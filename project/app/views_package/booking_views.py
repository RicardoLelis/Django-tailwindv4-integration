"""
Views for pre-booked ride functionality.
Follows SoC by delegating business logic to services.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
import json
import logging

from ..models import (
    Rider, PreBookedRide, RecurringRideTemplate,
    RideMatchOffer, Driver
)
from ..forms import PreBookedRideForm, RecurringRideForm
from ..services.booking_service import BookingService
from ..services.matching_service import MatchingService
from ..services.pricing_service import PricingService
from ..services.geocoding_service import GeocodingService

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def pre_book_ride(request):
    """Create a new pre-booked ride"""
    try:
        rider = request.user.rider
    except Rider.DoesNotExist:
        messages.error(request, "Please complete your rider profile first.")
        return redirect('home')
    
    if request.method == 'POST':
        form = PreBookedRideForm(request.POST)
        if form.is_valid():
            try:
                # Get services
                booking_service = BookingService()
                
                # Create booking
                booking = booking_service.create_booking(
                    rider=rider,
                    pickup_location=form.cleaned_data['pickup_location'],
                    dropoff_location=form.cleaned_data['dropoff_location'],
                    pickup_datetime=form.cleaned_data['pickup_datetime'],
                    booking_type=form.cleaned_data.get('booking_type', 'single'),
                    purpose=form.cleaned_data.get('purpose', 'other'),
                    special_requirements=form.cleaned_data.get('special_requirements', ''),
                    wheelchair_required=form.cleaned_data.get('wheelchair_required', False),
                    assistance_required=form.cleaned_data.get('assistance_required', []),
                    priority=form.cleaned_data.get('priority', 'normal'),
                    pickup_window_minutes=form.cleaned_data.get('pickup_window_minutes', 15)
                )
                
                # Broadcast the pre-booked ride to available drivers
                try:
                    from ..services.matching_service import MatchingService
                    from ..services.notification_service import NotificationService
                    
                    matching_service = MatchingService()
                    notification_service = NotificationService()
                    
                    # Find best driver matches for this booking
                    matches = matching_service.find_best_matches(booking, max_offers=5)
                    
                    if matches:
                        # Create offers for top matches
                        offers = matching_service.create_match_offers(
                            booking,
                            matches,
                            offer_duration_hours=24  # Pre-booked offers last longer
                        )
                        
                        # Notify each matched driver
                        for offer in offers:
                            notification_service.notify_driver_new_offer(offer.driver, offer)
                        
                        logger.info(f"Created {len(offers)} offers for pre-booked ride {booking.id}")
                        
                        messages.success(
                            request,
                            f"Your ride has been scheduled for {booking.pickup_datetime.strftime('%B %d at %I:%M %p')}. "
                            f"We've notified {len(offers)} nearby drivers!"
                        )
                    else:
                        messages.success(
                            request,
                            f"Your ride has been scheduled for {booking.pickup_datetime.strftime('%B %d at %I:%M %p')}. "
                            "We'll match you with a driver soon."
                        )
                        
                except Exception as e:
                    logger.error(f"Error matching/broadcasting booking {booking.id}: {e}")
                    messages.success(
                        request,
                        f"Your ride has been scheduled for {booking.pickup_datetime.strftime('%B %d at %I:%M %p')}. "
                        "We'll match you with a driver soon."
                    )
                
                # Redirect to driver selection if immediate matching
                if form.cleaned_data.get('immediate_matching'):
                    return redirect('search_drivers', booking_id=booking.id)
                
                return redirect('booking_details', booking_id=booking.id)
                
            except Exception as e:
                logger.error(f"Error creating booking: {e}")
                messages.error(request, "An error occurred while creating your booking. Please try again.")
    else:
        # Pre-fill form with common medical locations if coming from medical context
        initial = {}
        if request.GET.get('medical'):
            initial['purpose'] = 'medical'
        
        form = PreBookedRideForm(initial=initial)
    
    # Get recent locations for quick selection
    recent_locations = PreBookedRide.objects.filter(
        rider=rider
    ).values_list('pickup_location', 'dropoff_location').distinct()[:5]
    
    # Get medical facilities
    geocoding_service = GeocodingService()
    medical_facilities = geocoding_service.get_nearby_medical_facilities(
        38.7223, -9.1393, radius_km=10  # Lisbon center
    )
    
    context = {
        'form': form,
        'recent_locations': recent_locations,
        'medical_facilities': medical_facilities,
    }
    
    return render(request, 'bookings/pre_book_ride.html', context)


@login_required
def search_drivers(request, booking_id):
    """Search and display available drivers for a booking"""
    booking = get_object_or_404(PreBookedRide, id=booking_id, rider__user=request.user)
    
    if booking.status != 'pending':
        messages.warning(request, "This booking has already been matched with a driver.")
        return redirect('booking_details', booking_id=booking.id)
    
    # Get matching service
    matching_service = MatchingService()
    
    # Find best matches
    matches = matching_service.find_best_matches(booking, max_offers=5)
    
    if not matches:
        messages.warning(
            request,
            "No drivers are currently available for your requested time. "
            "We'll notify you when drivers become available."
        )
        return redirect('booking_details', booking_id=booking.id)
    
    # Create offers for matched drivers
    if request.method == 'POST':
        selected_drivers = request.POST.getlist('selected_drivers')
        if selected_drivers:
            # Create offers for selected drivers
            selected_matches = [
                (driver, score) for driver, score in matches
                if str(driver.id) in selected_drivers
            ]
            
            offers = matching_service.create_match_offers(
                booking,
                selected_matches,
                offer_duration_hours=2
            )
            
            messages.success(
                request,
                f"Your ride request has been sent to {len(offers)} drivers. "
                "You'll be notified when a driver accepts."
            )
            
            return redirect('booking_details', booking_id=booking.id)
    
    # Prepare driver data for display
    driver_options = []
    for driver, scores in matches:
        # Get driver's vehicle info
        vehicle = driver.vehicles.filter(is_active=True).first()
        
        driver_info = {
            'driver': driver,
            'vehicle': vehicle,
            'scores': scores,
            'total_score': scores['total_score'],
            'estimated_arrival': booking.pickup_datetime,  # TODO: Calculate based on distance
            'fare_estimate': booking.estimated_fare,  # TODO: Driver-specific pricing
        }
        driver_options.append(driver_info)
    
    context = {
        'booking': booking,
        'driver_options': driver_options,
    }
    
    return render(request, 'bookings/search_drivers.html', context)


@login_required
def booking_details(request, booking_id):
    """View details of a pre-booked ride"""
    booking = get_object_or_404(
        PreBookedRide.objects.select_related(
            'rider', 'matched_driver', 'matched_vehicle'
        ),
        id=booking_id,
        rider__user=request.user
    )
    
    # Get match offers if pending
    offers = None
    if booking.status == 'pending':
        offers = RideMatchOffer.objects.filter(
            pre_booked_ride=booking
        ).select_related('driver', 'driver__user').order_by('-match_score')
    
    # Calculate time until pickup
    time_until_pickup = booking.pickup_datetime - timezone.now()
    hours_until_pickup = time_until_pickup.total_seconds() / 3600
    
    # Determine if cancellation is free
    cancellation_fee = Decimal('0')
    if hours_until_pickup < 24:
        pricing_service = PricingService()
        cancellation_fee = pricing_service.calculate_cancellation_fee(booking)
    
    context = {
        'booking': booking,
        'offers': offers,
        'hours_until_pickup': hours_until_pickup,
        'cancellation_fee': cancellation_fee,
        'can_modify': booking.status == 'pending' and hours_until_pickup > 2,
    }
    
    return render(request, 'bookings/booking_details.html', context)


@login_required
@require_http_methods(["POST"])
def cancel_booking(request, booking_id):
    """Cancel a pre-booked ride"""
    booking = get_object_or_404(
        PreBookedRide,
        id=booking_id,
        rider__user=request.user
    )
    
    if booking.status in ['completed', 'cancelled']:
        messages.error(request, "This booking cannot be cancelled.")
        return redirect('booking_details', booking_id=booking.id)
    
    reason = request.POST.get('reason', 'User requested cancellation')
    
    try:
        booking_service = BookingService()
        success, fee = booking_service.cancel_booking(booking, reason)
        
        if success:
            if fee > 0:
                messages.warning(
                    request,
                    f"Your booking has been cancelled. A cancellation fee of €{fee} applies."
                )
            else:
                messages.success(request, "Your booking has been cancelled successfully.")
        
    except Exception as e:
        logger.error(f"Error cancelling booking {booking_id}: {e}")
        messages.error(request, "An error occurred while cancelling your booking.")
    
    return redirect('my_bookings')


@login_required
def confirm_booking(request, booking_id):
    """Confirm a pre-booked ride after driver selection"""
    booking = get_object_or_404(PreBookedRide, id=booking_id, rider=request.user.rider)
    
    if request.method == 'POST':
        offer_id = request.POST.get('offer_id')
        if offer_id:
            offer = get_object_or_404(RideMatchOffer, id=offer_id, pre_booked_ride=booking)
            
            # Accept the offer
            booking.status = 'confirmed'
            booking.matched_driver = offer.driver
            booking.matched_vehicle = offer.vehicle
            booking.estimated_fare = offer.total_fare
            booking.save()
            
            # Update offer status
            offer.status = 'accepted'
            offer.save()
            
            # Decline other offers
            RideMatchOffer.objects.filter(
                pre_booked_ride=booking
            ).exclude(id=offer.id).update(status='declined')
            
            # Send notifications
            from ..services.notification_service import NotificationService
            notification_service = NotificationService()
            notification_service.notify_rider_offer_accepted(booking)
            
            messages.success(request, 'Your ride has been confirmed!')
            return redirect('booking_details', booking_id=booking.id)
    
    return redirect('booking_details', booking_id=booking.id)


@login_required
def my_bookings(request):
    """View all bookings for the current rider"""
    try:
        rider = request.user.rider
    except Rider.DoesNotExist:
        messages.error(request, "Please complete your rider profile first.")
        return redirect('home')
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'upcoming')
    
    # Base queryset
    bookings = PreBookedRide.objects.filter(
        rider=rider
    ).select_related(
        'matched_driver', 'matched_vehicle', 'recurring_template'
    ).order_by('-pickup_datetime')
    
    # Apply filters
    if status_filter == 'upcoming':
        bookings = bookings.filter(
            pickup_datetime__gte=timezone.now(),
            status__in=['pending', 'matched', 'confirmed']
        )
    elif status_filter == 'past':
        bookings = bookings.filter(
            Q(pickup_datetime__lt=timezone.now()) |
            Q(status__in=['completed', 'cancelled'])
        )
    elif status_filter == 'active':
        bookings = bookings.filter(status='in_progress')
    
    # Paginate
    paginator = Paginator(bookings, 10)
    page = request.GET.get('page')
    bookings_page = paginator.get_page(page)
    
    # Get recurring templates
    recurring_templates = RecurringRideTemplate.objects.filter(
        rider=rider,
        is_active=True
    ).select_related('preferred_driver')
    
    context = {
        'bookings': bookings_page,
        'recurring_templates': recurring_templates,
        'status_filter': status_filter,
    }
    
    return render(request, 'bookings/my_bookings.html', context)


@login_required
def recurring_rides(request):
    """Manage recurring ride templates"""
    try:
        rider = request.user.rider
    except Rider.DoesNotExist:
        messages.error(request, "Please complete your rider profile first.")
        return redirect('home')
    
    templates = RecurringRideTemplate.objects.filter(
        rider=rider
    ).select_related('preferred_driver').order_by('-created_at')
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'bookings/recurring_rides.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def create_recurring_ride(request):
    """Create a new recurring ride template"""
    try:
        rider = request.user.rider
    except Rider.DoesNotExist:
        messages.error(request, "Please complete your rider profile first.")
        return redirect('home')
    
    if request.method == 'POST':
        form = RecurringRideForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.rider = rider
            
            # Get geocoding for addresses
            geocoding_service = GeocodingService()
            pickup_coords = geocoding_service.geocode(template.pickup_location)
            dropoff_coords = geocoding_service.geocode(template.dropoff_location)
            
            if pickup_coords and dropoff_coords:
                template.pickup_lat = Decimal(str(pickup_coords['lat']))
                template.pickup_lng = Decimal(str(pickup_coords['lng']))
                template.dropoff_lat = Decimal(str(dropoff_coords['lat']))
                template.dropoff_lng = Decimal(str(dropoff_coords['lng']))
                
                # Calculate route info
                route_info = geocoding_service.get_route_info(
                    pickup_coords, dropoff_coords
                )
                template.duration_minutes = route_info['duration_minutes']
            
            template.save()
            
            # Generate initial bookings if requested
            if form.cleaned_data.get('generate_now'):
                booking_service = BookingService()
                generate_until = timezone.now() + timezone.timedelta(
                    days=template.auto_book_days_ahead
                )
                bookings = booking_service.create_recurring_bookings(
                    template, generate_until
                )
                
                messages.success(
                    request,
                    f"Recurring ride created! {len(bookings)} rides have been scheduled."
                )
            else:
                messages.success(request, "Recurring ride template created successfully!")
            
            return redirect('recurring_rides')
    else:
        form = RecurringRideForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'bookings/create_recurring_ride.html', context)


@login_required
@require_http_methods(["POST"])
def pause_recurring_ride(request, template_id):
    """Pause or resume a recurring ride template"""
    template = get_object_or_404(
        RecurringRideTemplate,
        id=template_id,
        rider__user=request.user
    )
    
    action = request.POST.get('action', 'pause')
    
    if action == 'pause':
        template.pause()
        messages.success(request, "Recurring ride has been paused.")
    elif action == 'resume':
        template.resume()
        messages.success(request, "Recurring ride has been resumed.")
    
    return redirect('recurring_rides')


# AJAX endpoints for pre-booking

@login_required
@require_http_methods(["POST"])
def ajax_calculate_fare(request):
    """Calculate fare estimate for pre-booked ride"""
    try:
        data = json.loads(request.body)
        
        # Get geocoding service
        geocoding_service = GeocodingService()
        pricing_service = PricingService()
        
        # Geocode addresses
        pickup_coords = geocoding_service.geocode(data['pickup_location'])
        dropoff_coords = geocoding_service.geocode(data['dropoff_location'])
        
        if not pickup_coords or not dropoff_coords:
            return JsonResponse({
                'success': False,
                'error': 'Unable to validate addresses'
            })
        
        # Get route info
        route_info = geocoding_service.get_route_info(
            pickup_coords, dropoff_coords
        )
        
        # Calculate fare
        fare_estimate = pricing_service.get_fare_estimate_range(
            distance_km=route_info['distance_km'],
            duration_minutes=route_info['duration_minutes'],
            booking_type=data.get('booking_type', 'single'),
            priority=data.get('priority', 'normal'),
            wheelchair_required=data.get('wheelchair_required', False)
        )
        
        return JsonResponse({
            'success': True,
            'distance_km': route_info['distance_km'],
            'duration_minutes': route_info['duration_minutes'],
            'min_fare': str(fare_estimate['min_fare']),
            'max_fare': str(fare_estimate['max_fare']),
            'estimated_fare': str(fare_estimate['estimated_fare']),
        })
        
    except Exception as e:
        logger.error(f"Fare calculation error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to calculate fare'
        })


@login_required
@require_http_methods(["GET"])
def ajax_check_availability(request):
    """Check driver availability for a specific time"""
    try:
        pickup_datetime = timezone.datetime.fromisoformat(
            request.GET.get('pickup_datetime')
        )
        duration_minutes = int(request.GET.get('duration_minutes', 30))
        
        # Get matching service
        matching_service = MatchingService()
        
        # Mock check for available drivers
        available_count = Driver.objects.filter(
            is_active=True,
            application_status='approved'
        ).count()
        
        # Estimate availability
        if pickup_datetime.hour < 6 or pickup_datetime.hour > 22:
            availability = 'low'
            message = 'Limited drivers available at this time'
        elif available_count < 5:
            availability = 'medium'
            message = 'Some drivers available'
        else:
            availability = 'high'
            message = 'Good driver availability'
        
        return JsonResponse({
            'success': True,
            'availability': availability,
            'message': message,
            'available_drivers': available_count,
        })
        
    except Exception as e:
        logger.error(f"Availability check error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to check availability'
        })