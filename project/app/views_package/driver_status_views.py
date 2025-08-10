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
from datetime import timedelta
import json
import logging
import pytz

from ..models import Driver, DriverSession, PreBookedRide, RideMatchOffer, Ride
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
    """Get live offers for driver (AJAX endpoint) - includes both immediate and pre-booked rides"""
    try:
        driver = request.user.driver
        
        # Check if driver is eligible to receive offers
        if not driver.can_drive or not driver.is_available or not driver.is_active:
            return JsonResponse({'offers': [], 'message': 'Not available to receive offers'})
        
        offers_data = []
        
        # 1. Get pending pre-booked ride offers (existing system)
        prebooked_offers = RideMatchOffer.objects.filter(
            driver=driver,
            status='pending',
            expires_at__gt=timezone.now()
        ).select_related(
            'pre_booked_ride',
            'pre_booked_ride__rider',
            'pre_booked_ride__rider__user'
        ).order_by('-compatibility_score', 'pre_booked_ride__scheduled_pickup_time')
        
        for offer in prebooked_offers:
            ride = offer.pre_booked_ride
            time_until_pickup = (ride.scheduled_pickup_time - timezone.now()).total_seconds() / 3600
            
            offers_data.append({
                'id': f'prebooked_{offer.id}',
                'type': 'prebooked',
                'offer_id': offer.id,
                'ride_id': ride.id,
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
        
        # 2. Get immediate pending rides (new functionality)
        from ..models import Ride
        from ..services.geocoding_service import GeocodingService
        from ..services.pricing_service import PricingService
        
        immediate_rides = Ride.objects.filter(
            status='pending',
            pickup_datetime__gte=timezone.now(),
            pickup_datetime__lte=timezone.now() + timedelta(days=7)  # Show rides within 7 days
        ).select_related('rider', 'rider__user').order_by('pickup_datetime')
        
        # Initialize services for distance and pricing calculations
        geocoding_service = GeocodingService()
        pricing_service = PricingService()
        
        for ride in immediate_rides:
            time_until_pickup = (ride.pickup_datetime - timezone.now()).total_seconds() / 3600
            
            # Skip if too far in the future (more than 7 days)
            if time_until_pickup > 168:  # 7 days * 24 hours
                continue
            
            # Calculate distance and fare
            distance_km = 0.0
            estimated_fare = 'TBD'
            
            try:
                # Geocode pickup and dropoff locations
                pickup_coords = geocoding_service.geocode(ride.pickup_location)
                dropoff_coords = geocoding_service.geocode(ride.dropoff_location)
                
                if pickup_coords and dropoff_coords:
                    # Calculate distance using Haversine formula
                    distance_km = geocoding_service._calculate_distance(
                        pickup_coords['lat'], pickup_coords['lng'],
                        dropoff_coords['lat'], dropoff_coords['lng']
                    )
                    
                    # Check if wheelchair is required
                    wheelchair_required = any('wheelchair' in disability.lower() 
                                            for disability in ride.rider.disabilities) if ride.rider.disabilities else False
                    
                    # Calculate fare for immediate ride
                    estimated_fare = pricing_service.calculate_immediate_fare(
                        distance_km=distance_km,
                        wheelchair_required=wheelchair_required
                    )
                    
            except Exception as e:
                logger.warning(f"Error calculating distance/fare for ride {ride.id}: {e}")
                # Use fallback values
                distance_km = 5.0  # Fallback distance
                estimated_fare = pricing_service.calculate_immediate_fare(distance_km=5.0)
            
            offers_data.append({
                'id': f'immediate_{ride.id}',
                'type': 'immediate',
                'ride_id': ride.id,
                'pickup_location': ride.pickup_location,
                'dropoff_location': ride.dropoff_location,
                'pickup_time': ride.pickup_datetime.strftime('%I:%M %p'),
                'pickup_date': ride.pickup_datetime.strftime('%b %d'),
                'hours_until_pickup': round(time_until_pickup, 1),
                'rider_name': ride.rider.user.get_full_name() or ride.rider.user.username,
                'special_requirements': ride.special_requirements or 'None',
                'distance_km': round(distance_km, 1),
                'fare': str(estimated_fare),
                'estimated_fare': str(estimated_fare),  # For compatibility
                'created_at': timezone.localtime(ride.created_at).strftime('%H:%M'),
                'is_immediate': True,
                'wheelchair_required': any('wheelchair' in disability.lower() 
                                         for disability in ride.rider.disabilities) if ride.rider.disabilities else False
            })
        
        # Sort all offers by urgency (immediate rides first, then by pickup time)
        offers_data.sort(key=lambda x: (
            0 if x.get('is_immediate') else 1,  # Immediate rides first
            x.get('hours_until_pickup', 999)     # Then by pickup time
        ))
        
        return JsonResponse({
            'success': True,
            'offers': offers_data,
            'count': len(offers_data),
            'immediate_count': len([o for o in offers_data if o.get('is_immediate')]),
            'prebooked_count': len([o for o in offers_data if not o.get('is_immediate')])
        })
        
    except Exception as e:
        logger.error(f"Error getting live offers: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to get offers'
        })


@login_required  
@require_http_methods(["POST"])
def accept_immediate_ride(request, ride_id):
    """Accept an immediate ride request"""
    try:
        driver = request.user.driver
        
        # Check if driver is eligible
        if not driver.can_drive or not driver.is_available or not driver.is_active:
            return JsonResponse({
                'success': False,
                'error': 'Driver not available to accept rides'
            })
        
        # Get the ride
        ride = Ride.objects.select_related('rider', 'rider__user').get(
            id=ride_id,
            status='pending'
        )
        
        # Create a DriverRide assignment (if the model exists)
        # For now, just update the ride status and assign the driver
        from django.db import transaction
        
        with transaction.atomic():
            # Update ride status
            ride.status = 'confirmed'
            ride.save()
            
            # Create or update driver ride assignment
            try:
                from ..models import DriverRide
                driver_ride = DriverRide.objects.create(
                    driver=driver,
                    ride=ride,
                    status='assigned',
                    assigned_at=timezone.now()
                )
            except Exception as e:
                logger.warning(f"Could not create DriverRide: {e}")
                # Continue without DriverRide if model doesn't exist
            
            # Set driver as busy 
            driver.is_available = False
            driver.save()
            
            # Send notification to rider (optional)
            try:
                notification_service = NotificationService()
                notification_service.notify_rider_ride_accepted(ride, driver)
            except Exception as e:
                logger.warning(f"Could not send notification: {e}")
        
        return JsonResponse({
            'success': True,
            'message': f'Ride accepted! Pickup at {ride.pickup_location}',
            'ride': {
                'id': ride.id,
                'pickup_location': ride.pickup_location,
                'dropoff_location': ride.dropoff_location,
                'pickup_time': ride.pickup_datetime.strftime('%I:%M %p'),
                'rider_name': ride.rider.user.get_full_name() or ride.rider.user.username
            }
        })
        
    except Ride.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Ride not found or already taken'
        })
    except Exception as e:
        logger.error(f"Error accepting immediate ride: {e}")
        return JsonResponse({
            'success': False, 
            'error': 'Failed to accept ride'
        })