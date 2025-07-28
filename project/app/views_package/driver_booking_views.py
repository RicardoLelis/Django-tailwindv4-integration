"""
Driver-side views for managing pre-booked rides.
Handles calendar, offers, and optimizations.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction, models
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse
from datetime import datetime, timedelta
import json
import logging

from ..models import (
    Driver, DriverCalendar, PreBookedRide,
    RideMatchOffer, WaitingTimeOptimization
)
from ..forms import DriverCalendarForm, RideOfferResponseForm
from ..services.calendar_service import CalendarService
from ..services.matching_service import MatchingService

logger = logging.getLogger(__name__)


def driver_required(view_func):
    """Decorator to ensure user is a driver"""
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            driver = request.user.driver
            if driver.application_status != 'approved':
                messages.warning(
                    request,
                    "Please complete your driver application to access this feature."
                )
                return redirect('driver_dashboard')
        except Driver.DoesNotExist:
            messages.error(request, "Driver profile not found.")
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


@login_required
@driver_required
def driver_calendar(request):
    """Main calendar view for drivers"""
    driver = request.user.driver
    
    # Get current month or requested month
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # Get calendar service
    calendar_service = CalendarService()
    
    # Get calendar entries for the month
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    schedule = calendar_service.get_driver_schedule(driver, start_date, end_date)
    
    # Get suggestions for optimization
    suggestions = calendar_service.suggest_schedule_improvements(driver, today)
    
    # Calculate month statistics
    month_stats = {
        'total_bookings': 0,
        'total_earnings': 0,
        'average_utilization': 0,
        'days_worked': 0,
    }
    
    for date_str, day_data in schedule.items():
        if day_data['calendar'] and day_data['calendar'].is_available:
            month_stats['days_worked'] += 1
            month_stats['total_bookings'] += len(day_data['bookings'])
            if day_data['calendar'].total_estimated_earnings:
                month_stats['total_earnings'] += float(
                    day_data['calendar'].total_estimated_earnings
                )
    
    context = {
        'driver': driver,
        'year': year,
        'month': month,
        'today': today,
        'schedule': schedule,
        'suggestions': suggestions,
        'month_stats': month_stats,
        'prev_month': (month - 1) if month > 1 else 12,
        'prev_year': year if month > 1 else year - 1,
        'next_month': (month + 1) if month < 12 else 1,
        'next_year': year if month < 12 else year + 1,
    }
    
    return render(request, 'driver/calendar/calendar.html', context)


@login_required
@driver_required
@require_http_methods(["GET", "POST"])
def update_calendar(request):
    """Update driver availability for a specific date"""
    driver = request.user.driver
    
    # Get date from query params or form
    date_str = request.GET.get('date') or request.POST.get('date')
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('driver_calendar')
    else:
        date = timezone.now().date()
    
    # Get existing calendar entry
    try:
        calendar_entry = DriverCalendar.objects.get(driver=driver, date=date)
    except DriverCalendar.DoesNotExist:
        calendar_entry = None
    
    if request.method == 'POST':
        form = DriverCalendarForm(request.POST, instance=calendar_entry)
        if form.is_valid():
            calendar_service = CalendarService()
            
            # Extract break slots from form
            break_slots = []
            if form.cleaned_data.get('break_start') and form.cleaned_data.get('break_duration'):
                break_start = form.cleaned_data['break_start']
                break_duration = form.cleaned_data['break_duration']
                break_end = (
                    datetime.combine(date, break_start) +
                    timedelta(minutes=break_duration)
                ).time()
                
                break_slots.append({
                    'start': break_start.isoformat(),
                    'end': break_end.isoformat(),
                    'reason': 'Scheduled break'
                })
            
            # Update calendar
            calendar_entry = calendar_service.update_driver_availability(
                driver=driver,
                date=form.cleaned_data['date'],
                start_time=form.cleaned_data['start_time'],
                end_time=form.cleaned_data['end_time'],
                is_available=form.cleaned_data['status'] == 'available',
                break_slots=break_slots,
                zones=[]  # TODO: Add zone selection
            )
            
            # Update preferences
            calendar_entry.max_bookings = form.cleaned_data.get('max_bookings')
            calendar_entry.accepts_wheelchair = form.cleaned_data.get('accepts_wheelchair', True)
            calendar_entry.accepts_long_distance = form.cleaned_data.get('accepts_long_distance', True)
            calendar_entry.save()
            
            messages.success(request, f"Availability updated for {date}")
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Availability updated successfully'
                })
            
            return redirect('driver_calendar')
    else:
        initial = {'date': date}
        if calendar_entry:
            initial.update({
                'start_time': calendar_entry.start_time,
                'end_time': calendar_entry.end_time,
                'status': 'available' if calendar_entry.is_available else 'busy',
                'max_bookings': calendar_entry.max_bookings,
                'accepts_wheelchair': calendar_entry.accepts_wheelchair,
                'accepts_long_distance': calendar_entry.accepts_long_distance,
            })
            
            # Extract break info
            if calendar_entry.break_slots:
                first_break = calendar_entry.break_slots[0]
                initial['break_start'] = first_break.get('start')
        
        form = DriverCalendarForm(initial=initial)
    
    context = {
        'form': form,
        'date': date,
        'calendar_entry': calendar_entry,
    }
    
    return render(request, 'driver/calendar/update_calendar.html', context)


@login_required
@driver_required
def driver_offers(request):
    """View and manage ride offers"""
    driver = request.user.driver
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'pending')
    
    # Base queryset
    offers = RideMatchOffer.objects.filter(
        driver=driver
    ).select_related(
        'pre_booked_ride',
        'pre_booked_ride__rider',
        'pre_booked_ride__rider__user'
    )
    
    # Apply status filter
    if status_filter == 'pending':
        offers = offers.filter(
            status='pending',
            expires_at__gt=timezone.now()
        )
    elif status_filter == 'expired':
        offers = offers.filter(
            models.Q(status='expired') | models.Q(expires_at__lte=timezone.now())
        )
    elif status_filter == 'accepted':
        offers = offers.filter(status='accepted')
    elif status_filter == 'declined':
        offers = offers.filter(status='declined')
    
    # Order by newest first for pending, by response date for others
    if status_filter == 'pending':
        offers = offers.order_by('-offered_at')
    else:
        offers = offers.order_by('-responded_at', '-offered_at')
    
    # Paginate
    paginator = Paginator(offers, 10)
    page = request.GET.get('page')
    offers_page = paginator.get_page(page)
    
    # Calculate statistics
    stats = {
        'pending_count': RideMatchOffer.objects.filter(
            driver=driver,
            status='pending',
            expires_at__gt=timezone.now()
        ).count(),
        'acceptance_rate': 0,
    }
    
    # Calculate acceptance rate
    total_responded = RideMatchOffer.objects.filter(
        driver=driver,
        status__in=['accepted', 'declined']
    ).count()
    
    if total_responded > 0:
        accepted = RideMatchOffer.objects.filter(
            driver=driver,
            status='accepted'
        ).count()
        stats['acceptance_rate'] = (accepted / total_responded) * 100
    
    context = {
        'offers': offers_page,
        'status_filter': status_filter,
        'stats': stats,
    }
    
    return render(request, 'driver/offers/offer_list.html', context)


@login_required
@driver_required
@require_http_methods(["GET", "POST"])
def accept_offer(request, offer_id):
    """Accept a ride offer"""
    driver = request.user.driver
    offer = get_object_or_404(
        RideMatchOffer,
        id=offer_id,
        driver=driver,
        status='pending'
    )
    
    # Check if offer is still valid
    if offer.expires_at <= timezone.now():
        messages.error(request, "This offer has expired.")
        return redirect('driver_offers')
    
    if request.method == 'POST':
        try:
            matching_service = MatchingService()
            success = matching_service.handle_offer_response(
                offer, accepted=True
            )
            
            if success:
                messages.success(
                    request,
                    f"You've accepted the ride to {offer.pre_booked_ride.dropoff_location}. "
                    "The rider has been notified."
                )
                # Return JSON response for AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'redirect_url': reverse('driver_booking_detail', kwargs={'booking_id': offer.pre_booked_ride.id})
                    })
                return redirect('driver_booking_detail', booking_id=offer.pre_booked_ride.id)
            else:
                messages.error(
                    request,
                    "This ride has already been assigned to another driver."
                )
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'This ride has already been assigned to another driver.'
                    })
        
        except Exception as e:
            logger.error(f"Error accepting offer {offer_id}: {e}")
            messages.error(request, "An error occurred. Please try again.")
        
        return redirect('driver_offers')
    
    # Calculate time until pickup
    time_until_pickup = offer.pre_booked_ride.scheduled_pickup_time - timezone.now()
    
    context = {
        'offer': offer,
        'booking': offer.pre_booked_ride,
        'time_until_pickup': time_until_pickup,
    }
    
    return render(request, 'driver/offers/accept_offer.html', context)


@login_required
@driver_required
@require_http_methods(["POST"])
def decline_offer(request, offer_id):
    """Decline a ride offer"""
    driver = request.user.driver
    offer = get_object_or_404(
        RideMatchOffer,
        id=offer_id,
        driver=driver,
        status='pending'
    )
    
    form = RideOfferResponseForm(request.POST)
    if form.is_valid() and form.cleaned_data['response'] == 'decline':
        try:
            matching_service = MatchingService()
            success = matching_service.handle_offer_response(
                offer,
                accepted=False,
                decline_reason=form.cleaned_data.get('decline_reason')
            )
            
            if success:
                messages.info(request, "Offer declined.")
            
        except Exception as e:
            logger.error(f"Error declining offer {offer_id}: {e}")
            messages.error(request, "An error occurred. Please try again.")
    
    return redirect('driver_offers')


@login_required
@driver_required
def driver_bookings(request):
    """View driver's accepted bookings"""
    driver = request.user.driver
    
    # Get filter
    time_filter = request.GET.get('time', 'upcoming')
    
    # Base queryset
    bookings = PreBookedRide.objects.filter(
        matched_driver=driver
    ).select_related(
        'rider', 'rider__user', 'matched_vehicle'
    )
    
    # Apply time filter
    now = timezone.now()
    if time_filter == 'upcoming':
        bookings = bookings.filter(
            scheduled_pickup_time__gte=now,
            status__in=['matched', 'confirmed', 'driver_assigned']
        ).order_by('scheduled_pickup_time')
    elif time_filter == 'today':
        today_start = now.replace(hour=0, minute=0, second=0)
        today_end = now.replace(hour=23, minute=59, second=59)
        bookings = bookings.filter(
            scheduled_pickup_time__range=(today_start, today_end)
        ).order_by('scheduled_pickup_time')
    elif time_filter == 'past':
        bookings = bookings.filter(
            models.Q(scheduled_pickup_time__lt=now) | models.Q(status='completed')
        ).order_by('-scheduled_pickup_time')
    
    # Paginate
    paginator = Paginator(bookings, 10)
    page = request.GET.get('page')
    bookings_page = paginator.get_page(page)
    
    # Get waiting optimizations
    optimizations = WaitingTimeOptimization.objects.filter(
        driver=driver,
        wait_start__gte=now,
        wait_end__gte=now
    ).select_related('original_ride').order_by('wait_start')[:5]
    
    context = {
        'bookings': bookings_page,
        'time_filter': time_filter,
        'optimizations': optimizations,
    }
    
    return render(request, 'driver/bookings/booking_list.html', context)


@login_required
@driver_required
def driver_booking_detail(request, booking_id):
    """View details of a specific booking"""
    driver = request.user.driver
    booking = get_object_or_404(
        PreBookedRide.objects.select_related(
            'rider', 'rider__user', 'matched_vehicle'
        ),
        id=booking_id,
        assigned_driver=driver
    )
    
    # Check for optimization opportunities
    optimization = None
    if booking.booking_type == 'round_trip' and booking.waiting_duration_minutes:
        try:
            optimization = WaitingTimeOptimization.objects.get(
                original_ride=booking,
                driver=driver
            )
        except WaitingTimeOptimization.DoesNotExist:
            # Create optimization record if it doesn't exist
            if booking.status in ['matched', 'confirmed']:
                calendar_service = CalendarService()
                optimization = calendar_service.optimize_waiting_time(
                    driver=driver,
                    original_booking=booking,
                    wait_location={
                        'lat': float(booking.dropoff_latitude),
                        'lng': float(booking.dropoff_longitude)
                    },
                    wait_duration_minutes=booking.waiting_duration_minutes
                )
    
    # Get navigation info
    nav_info = None
    if booking.scheduled_pickup_time - timezone.now() < timedelta(hours=1):
        # Show navigation info if pickup is within an hour
        nav_info = {
            'pickup_address': booking.pickup_location,
            'pickup_lat': float(booking.pickup_latitude),
            'pickup_lng': float(booking.pickup_longitude),
            'maps_url': (
                f"https://www.google.com/maps/dir/?api=1"
                f"&destination={booking.pickup_latitude},{booking.pickup_longitude}"
            )
        }
    
    context = {
        'booking': booking,
        'optimization': optimization,
        'nav_info': nav_info,
    }
    
    return render(request, 'driver/bookings/booking_detail.html', context)


@login_required
@driver_required
def calendar_week_view(request):
    """Weekly calendar view for drivers"""
    driver = request.user.driver
    
    # Get week start date
    week_start_str = request.GET.get('week_start')
    if week_start_str:
        try:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        except ValueError:
            week_start = timezone.now().date()
    else:
        # Default to current week
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
    
    week_end = week_start + timedelta(days=6)
    
    # Get calendar service
    calendar_service = CalendarService()
    schedule = calendar_service.get_driver_schedule(driver, week_start, week_end)
    
    # Organize by time slots for grid display
    time_slots = []
    for hour in range(6, 23):  # 6 AM to 10 PM
        time_slots.append({
            'hour': hour,
            'display': f"{hour:02d}:00",
            'days': {}
        })
        
        for day_offset in range(7):
            date = week_start + timedelta(days=day_offset)
            date_str = date.isoformat()
            
            # Find bookings in this hour
            hour_bookings = []
            if date_str in schedule:
                for booking in schedule[date_str]['bookings']:
                    booking_hour = booking.scheduled_pickup_time.hour
                    if booking_hour == hour:
                        hour_bookings.append(booking)
            
            time_slots[-1]['days'][date_str] = hour_bookings
    
    # Navigation
    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)
    
    context = {
        'driver': driver,
        'week_start': week_start,
        'week_end': week_end,
        'schedule': schedule,
        'time_slots': time_slots,
        'prev_week': prev_week,
        'next_week': next_week,
    }
    
    return render(request, 'driver/calendar/week_view.html', context)


@login_required
@driver_required
def waiting_opportunities(request, optimization_id):
    """View opportunities during waiting time"""
    driver = request.user.driver
    optimization = get_object_or_404(
        WaitingTimeOptimization,
        id=optimization_id,
        driver=driver
    )
    
    # Find potential rides during wait time
    potential_rides = PreBookedRide.objects.filter(
        status='pending',
        scheduled_pickup_time__gte=optimization.wait_start,
        scheduled_pickup_time__lte=optimization.wait_end
    ).exclude(
        # Exclude rides that would conflict with return trip
        scheduled_pickup_time__gte=optimization.wait_end - timedelta(minutes=30)
    )
    
    # Filter by distance
    nearby_rides = []
    for ride in potential_rides:
        # Calculate distance from wait location
        # TODO: Implement actual distance calculation
        distance_km = 3.0  # Mock distance
        
        if distance_km <= float(optimization.max_distance_km):
            ride.distance_from_wait = distance_km
            nearby_rides.append(ride)
    
    context = {
        'optimization': optimization,
        'original_booking': optimization.original_ride,
        'nearby_rides': nearby_rides,
    }
    
    return render(request, 'driver/bookings/waiting_opportunities.html', context)