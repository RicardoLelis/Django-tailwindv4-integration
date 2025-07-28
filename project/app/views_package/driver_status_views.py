"""
Driver status management views.
Handles online/offline status and real-time ride notifications.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
import json
import logging

from ..models import Driver, DriverSession, PreBookedRide, RideMatchOffer
from ..services.matching_service import MatchingService
from ..services.notification_service import NotificationService

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def toggle_driver_status(request):
    """Toggle driver online/offline status"""
    try:
        driver = request.user.driver
        
        if driver.application_status != 'approved':
            return JsonResponse({
                'success': False,
                'error': 'Your application must be approved to go online'
            })
        
        # Toggle status
        if driver.is_available:
            # Going offline
            driver.is_available = False
            driver.save()
            
            # End current session if exists
            current_session = DriverSession.objects.filter(
                driver=driver,
                ended_at__isnull=True
            ).first()
            
            if current_session:
                current_session.ended_at = timezone.now()
                current_session.save()
            
            message = "You are now offline"
            
        else:
            # Going online
            driver.is_available = True
            
            # Update current location if provided
            if request.POST.get('latitude') and request.POST.get('longitude'):
                driver.current_location = {
                    'lat': float(request.POST.get('latitude')),
                    'lng': float(request.POST.get('longitude'))
                }
            
            driver.save()
            
            # Create new session
            DriverSession.objects.create(
                driver=driver,
                started_at=timezone.now(),
                start_location=driver.current_location
            )
            
            # Check for pending rides and create offers
            check_and_notify_pending_rides(driver)
            
            message = "You are now online and ready to receive rides"
        
        return JsonResponse({
            'success': True,
            'is_available': driver.is_available,
            'message': message
        })
        
    except Driver.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Driver profile not found'
        })
    except Exception as e:
        logger.error(f"Error toggling driver status: {e}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred'
        })


@login_required
@require_http_methods(["POST"])
def update_driver_location(request):
    """Update driver's current location"""
    try:
        driver = request.user.driver
        
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        if not latitude or not longitude:
            return JsonResponse({
                'success': False,
                'error': 'Location coordinates required'
            })
        
        driver.current_location = {
            'lat': float(latitude),
            'lng': float(longitude)
        }
        driver.save()
        
        # If driver is online, check for nearby pending rides
        if driver.is_available:
            check_and_notify_pending_rides(driver)
        
        return JsonResponse({
            'success': True,
            'message': 'Location updated'
        })
        
    except Exception as e:
        logger.error(f"Error updating driver location: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to update location'
        })


def check_and_notify_pending_rides(driver):
    """Check for pending rides and create offers for online driver"""
    try:
        # Get pending pre-booked rides
        pending_rides = PreBookedRide.objects.filter(
            status='pending',
            pickup_datetime__gte=timezone.now(),
            pickup_datetime__lte=timezone.now() + timezone.timedelta(days=7)
        )
        
        # Filter rides that don't already have an offer for this driver
        existing_offers = RideMatchOffer.objects.filter(
            driver=driver,
            pre_booked_ride__in=pending_rides
        ).values_list('pre_booked_ride_id', flat=True)
        
        pending_rides = pending_rides.exclude(id__in=existing_offers)
        
        if not pending_rides:
            return
        
        # Use matching service to evaluate rides
        matching_service = MatchingService()
        notification_service = NotificationService()
        
        offers_created = []
        
        for ride in pending_rides:
            # Check if driver matches requirements
            if ride.wheelchair_required and not driver.vehicles.filter(is_accessible=True).exists():
                continue
            
            # Calculate match score
            matches = matching_service.find_best_matches(ride, max_offers=10)
            
            # Check if this driver is in the top matches
            driver_match = None
            for match_driver, score in matches:
                if match_driver.id == driver.id:
                    driver_match = (match_driver, score)
                    break
            
            if driver_match and driver_match[1]['total_score'] > 60:  # Minimum score threshold
                # Create offer for this driver
                offers = matching_service.create_match_offers(
                    ride,
                    [driver_match],
                    offer_duration_hours=2
                )
                
                if offers:
                    offers_created.extend(offers)
                    
                    # Send notification
                    notification_service.notify_driver_new_offer(driver, offers[0])
        
        if offers_created:
            logger.info(f"Created {len(offers_created)} new offers for driver {driver.id}")
            
    except Exception as e:
        logger.error(f"Error checking pending rides: {e}")


@login_required
def driver_live_offers(request):
    """Get live offers for driver (AJAX endpoint)"""
    try:
        driver = request.user.driver
        
        # Get pending offers
        offers = RideMatchOffer.objects.filter(
            driver=driver,
            status='pending',
            expires_at__gt=timezone.now()
        ).select_related(
            'pre_booked_ride',
            'pre_booked_ride__rider',
            'pre_booked_ride__rider__user'
        ).order_by('-compatibility_score', 'pre_booked_ride__scheduled_pickup_time')
        
        # Format offers for JSON response
        offers_data = []
        for offer in offers:
            ride = offer.pre_booked_ride
            time_until_pickup = (ride.scheduled_pickup_time - timezone.now()).total_seconds() / 3600
            
            offers_data.append({
                'id': offer.id,
                'pickup_location': ride.pickup_location,
                'dropoff_location': ride.dropoff_location,
                'pickup_time': ride.scheduled_pickup_time.strftime('%I:%M %p'),
                'pickup_date': ride.scheduled_pickup_time.strftime('%b %d'),
                'hours_until_pickup': round(time_until_pickup, 1),
                'fare': str(offer.total_earnings),
                'distance_km': float(offer.distance_to_pickup_km),
                'match_score': float(offer.compatibility_score),
                'wheelchair_required': ride.wheelchair_required,
                'special_requirements': ride.special_requirements,
                'expires_in_minutes': int((offer.expires_at - timezone.now()).total_seconds() / 60)
            })
        
        return JsonResponse({
            'success': True,
            'offers': offers_data,
            'count': len(offers_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting live offers: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to get offers'
        })