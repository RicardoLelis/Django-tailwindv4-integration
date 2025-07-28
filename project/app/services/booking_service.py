"""
Pre-booked ride booking service following SoC and DRY principles.
Handles all business logic for creating and managing pre-booked rides.
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from ..models import (
    PreBookedRide, Driver, Vehicle, Rider,
    RecurringRideTemplate, DriverCalendar
)
from .pricing_service import PricingService
from .geocoding_service import GeocodingService

logger = logging.getLogger(__name__)


class BookingService:
    """Service for handling pre-booked ride operations"""
    
    def __init__(self):
        self.pricing_service = PricingService()
        self.geocoding_service = GeocodingService()
    
    @transaction.atomic
    def create_booking(
        self,
        rider: Rider,
        pickup_location: str,
        dropoff_location: str,
        pickup_datetime: datetime,
        booking_type: str = 'single',
        purpose: str = 'other',
        special_requirements: str = '',
        wheelchair_required: bool = False,
        assistance_required: List[str] = None,
        return_pickup_datetime: Optional[datetime] = None,
        flexible_return: bool = False,
        earliest_return_time: Optional[datetime] = None,
        latest_return_time: Optional[datetime] = None,
        waiting_duration_minutes: Optional[int] = None,
        priority: str = 'normal'
    ) -> PreBookedRide:
        """
        Create a new pre-booked ride with validation and pricing.
        
        Args:
            rider: The rider making the booking
            pickup_location: Pickup address
            dropoff_location: Dropoff address
            pickup_datetime: When to pick up the rider
            booking_type: 'single', 'round_trip', or 'recurring'
            purpose: Ride purpose (medical, work, etc.)
            special_requirements: Any special notes
            wheelchair_required: Whether wheelchair access is needed
            assistance_required: List of assistance types needed
            return_pickup_datetime: For round trips
            flexible_return: Whether return time is flexible
            earliest_return_time: Earliest possible return
            latest_return_time: Latest possible return
            waiting_duration_minutes: Expected wait time
            priority: Booking priority level
            
        Returns:
            PreBookedRide: The created booking
            
        Raises:
            ValidationError: If booking parameters are invalid
        """
        # Validate booking time (must be at least 2 hours in advance)
        min_booking_time = timezone.now() + timedelta(hours=2)
        if pickup_datetime < min_booking_time:
            raise ValidationError(
                "Rides must be booked at least 2 hours in advance."
            )
        
        # Validate booking window (max 30 days)
        max_booking_time = timezone.now() + timedelta(days=30)
        if pickup_datetime > max_booking_time:
            raise ValidationError(
                "Rides cannot be booked more than 30 days in advance."
            )
        
        # Get geocoding data
        pickup_coords = self.geocoding_service.geocode(pickup_location)
        dropoff_coords = self.geocoding_service.geocode(dropoff_location)
        
        if not pickup_coords or not dropoff_coords:
            raise ValidationError("Unable to validate addresses. Please check and try again.")
        
        # Calculate distance and duration
        route_info = self.geocoding_service.get_route_info(
            pickup_coords, dropoff_coords
        )
        
        # Calculate estimated fare
        estimated_fare = self.pricing_service.calculate_pre_booked_fare(
            distance_km=route_info['distance_km'],
            duration_minutes=route_info['duration_minutes'],
            booking_type=booking_type,
            priority=priority,
            wheelchair_required=wheelchair_required
        )
        
        # Handle round trip validation
        if booking_type == 'round_trip':
            if not any([return_pickup_datetime, flexible_return]):
                raise ValidationError(
                    "Round trip bookings require either a fixed return time or flexible return option."
                )
            
            if return_pickup_datetime and return_pickup_datetime <= pickup_datetime:
                raise ValidationError(
                    "Return pickup time must be after the initial pickup time."
                )
        
        # Create the booking
        booking = PreBookedRide.objects.create(
            rider=rider,
            booking_type=booking_type,
            purpose=purpose,
            pickup_location=pickup_location,
            pickup_lat=Decimal(str(pickup_coords['lat'])),
            pickup_lng=Decimal(str(pickup_coords['lng'])),
            dropoff_location=dropoff_location,
            dropoff_lat=Decimal(str(dropoff_coords['lat'])),
            dropoff_lng=Decimal(str(dropoff_coords['lng'])),
            pickup_datetime=pickup_datetime,
            estimated_duration_minutes=route_info['duration_minutes'],
            estimated_distance_km=Decimal(str(route_info['distance_km'])),
            special_requirements=special_requirements,
            wheelchair_required=wheelchair_required,
            assistance_required=assistance_required or [],
            return_pickup_datetime=return_pickup_datetime,
            flexible_return=flexible_return,
            earliest_return_time=earliest_return_time,
            latest_return_time=latest_return_time,
            waiting_duration_minutes=waiting_duration_minutes,
            estimated_fare=estimated_fare,
            priority=priority
        )
        
        logger.info(f"Created pre-booked ride {booking.id} for rider {rider.id}")
        
        # Schedule matching task (will be implemented with Celery)
        self._schedule_matching_task(booking)
        
        return booking
    
    @transaction.atomic
    def create_recurring_bookings(
        self,
        template: RecurringRideTemplate,
        generate_until: datetime
    ) -> List[PreBookedRide]:
        """
        Generate individual bookings from a recurring template.
        
        Args:
            template: The recurring ride template
            generate_until: Generate bookings up to this date
            
        Returns:
            List of created bookings
        """
        bookings = []
        current_date = max(template.start_date, timezone.now().date())
        
        while current_date <= generate_until.date():
            # Skip if this date is excluded
            if current_date in template.exclusion_dates:
                current_date += timedelta(days=1)
                continue
            
            # Check if this day matches the recurrence pattern
            if self._matches_recurrence_pattern(template, current_date):
                # Create booking for this date
                pickup_datetime = timezone.make_aware(
                    datetime.combine(current_date, template.pickup_time)
                )
                
                # Skip if in the past
                if pickup_datetime < timezone.now():
                    current_date += timedelta(days=1)
                    continue
                
                booking = self.create_booking(
                    rider=template.rider,
                    pickup_location=template.pickup_location,
                    dropoff_location=template.dropoff_location,
                    pickup_datetime=pickup_datetime,
                    booking_type='round_trip' if template.round_trip else 'single',
                    purpose=template.purpose,
                    special_requirements=template.special_requirements,
                    wheelchair_required=template.wheelchair_required,
                    assistance_required=template.assistance_required,
                    waiting_duration_minutes=template.waiting_duration_minutes,
                    priority=template.priority
                )
                
                bookings.append(booking)
            
            current_date += timedelta(days=1)
        
        # Update template tracking
        template.last_generated_until = generate_until.date()
        template.save()
        
        logger.info(
            f"Generated {len(bookings)} bookings from template {template.id}"
        )
        
        return bookings
    
    def _matches_recurrence_pattern(
        self,
        template: RecurringRideTemplate,
        date: datetime.date
    ) -> bool:
        """Check if a date matches the template's recurrence pattern"""
        if template.recurrence_type == 'daily':
            return True
        elif template.recurrence_type == 'weekly':
            return date.weekday() in template.custom_days
        elif template.recurrence_type == 'biweekly':
            # Check if it's the right week and day
            weeks_diff = (date - template.start_date).days // 7
            return weeks_diff % 2 == 0 and date.weekday() in template.custom_days
        elif template.recurrence_type == 'monthly':
            # Check if it's the right day of month
            return date.day in template.custom_days
        elif template.recurrence_type == 'custom':
            # Custom pattern - check against custom_days
            return date.weekday() in template.custom_days
        
        return False
    
    def _schedule_matching_task(self, booking: PreBookedRide):
        """Schedule matching task and immediately match with online drivers"""
        # Immediate matching for online drivers
        from .matching_service import MatchingService
        from ..models import Driver, DriverSession
        
        matching_service = MatchingService()
        
        # Find online drivers
        online_sessions = DriverSession.objects.filter(
            end_time__isnull=True,
            driver__status='approved'
        ).select_related('driver')
        
        # Create offers for suitable online drivers
        for session in online_sessions:
            # Check if driver is suitable for this ride
            matches = matching_service.find_best_matches(
                booking, 
                specific_drivers=[session.driver],
                max_offers=1
            )
            
            if matches:
                # Notify driver about new ride
                from ..services.notification_service import NotificationService
                notification_service = NotificationService()
                for offer in matches:
                    notification_service.notify_driver_new_offer(
                        offer.driver,
                        offer
                    )
                    logger.info(f"Notified driver {offer.driver.id} about ride {booking.id}")
        
        # TODO: Schedule future matching with Celery for rides > 24h away
        # if booking.pickup_datetime > timezone.now() + timedelta(hours=24):
        #     match_drivers_task.apply_async(
        #         args=[booking.id],
        #         eta=booking.pickup_datetime - timedelta(hours=24)
        #     )
    
    @transaction.atomic
    def cancel_booking(
        self,
        booking: PreBookedRide,
        reason: str,
        cancelled_by: str = 'rider'
    ) -> Tuple[bool, Optional[Decimal]]:
        """
        Cancel a pre-booked ride and calculate any fees.
        
        Args:
            booking: The booking to cancel
            reason: Cancellation reason
            cancelled_by: Who is cancelling ('rider' or 'driver')
            
        Returns:
            Tuple of (success, cancellation_fee)
        """
        if booking.status in ['completed', 'cancelled']:
            raise ValidationError("Cannot cancel a completed or already cancelled ride.")
        
        # Calculate cancellation fee
        cancellation_fee = self.pricing_service.calculate_cancellation_fee(
            booking, cancelled_by
        )
        
        # Update booking status
        booking.status = 'cancelled'
        booking.cancelled_at = timezone.now()
        booking.cancellation_reason = reason
        booking.cancellation_fee = cancellation_fee
        booking.save()
        
        # If driver cancelled, trigger re-matching
        if cancelled_by == 'driver' and booking.matched_driver:
            # Release the driver
            booking.matched_driver = None
            booking.matched_vehicle = None
            booking.save()
            
            # Schedule immediate re-matching
            self._schedule_matching_task(booking)
        
        logger.info(
            f"Cancelled booking {booking.id} by {cancelled_by} "
            f"with fee {cancellation_fee}"
        )
        
        return True, cancellation_fee
    
    def update_booking(
        self,
        booking: PreBookedRide,
        **kwargs
    ) -> PreBookedRide:
        """
        Update a pre-booked ride with validation.
        
        Args:
            booking: The booking to update
            **kwargs: Fields to update
            
        Returns:
            Updated booking
        """
        # Validate that booking can be modified
        if booking.status in ['in_progress', 'completed', 'cancelled']:
            raise ValidationError(
                "Cannot modify a ride that is in progress, completed, or cancelled."
            )
        
        # Check if critical fields are being changed
        critical_fields = ['pickup_datetime', 'pickup_location', 'dropoff_location']
        critical_changes = any(field in kwargs for field in critical_fields)
        
        if critical_changes and booking.matched_driver:
            # Need to re-match if critical fields change
            booking.matched_driver = None
            booking.matched_vehicle = None
            booking.status = 'pending'
        
        # Update fields
        for field, value in kwargs.items():
            if hasattr(booking, field):
                setattr(booking, field, value)
        
        booking.save()
        
        # Re-calculate fare if locations changed
        if 'pickup_location' in kwargs or 'dropoff_location' in kwargs:
            route_info = self.geocoding_service.get_route_info(
                {'lat': booking.pickup_lat, 'lng': booking.pickup_lng},
                {'lat': booking.dropoff_lat, 'lng': booking.dropoff_lng}
            )
            
            booking.estimated_distance_km = Decimal(str(route_info['distance_km']))
            booking.estimated_duration_minutes = route_info['duration_minutes']
            booking.estimated_fare = self.pricing_service.calculate_pre_booked_fare(
                distance_km=route_info['distance_km'],
                duration_minutes=route_info['duration_minutes'],
                booking_type=booking.booking_type,
                priority=booking.priority,
                wheelchair_required=booking.wheelchair_required
            )
            booking.save()
        
        # Schedule re-matching if needed
        if critical_changes and not booking.matched_driver:
            self._schedule_matching_task(booking)
        
        return booking