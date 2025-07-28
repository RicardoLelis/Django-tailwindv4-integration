"""
Calendar service for managing driver availability and scheduling.
Handles calendar operations with conflict detection and optimization.
"""

from django.db import transaction, models
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import logging

from ..models import (
    Driver, DriverCalendar, PreBookedRide,
    WaitingTimeOptimization
)

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for driver calendar and availability management"""
    
    # Default working hours
    DEFAULT_START_TIME = time(7, 0)  # 7:00 AM
    DEFAULT_END_TIME = time(22, 0)   # 10:00 PM
    
    # Buffer times (in minutes)
    MINIMUM_BREAK_DURATION = 30
    BUFFER_BETWEEN_RIDES = 15
    
    @transaction.atomic
    def update_driver_availability(
        self,
        driver: Driver,
        date: datetime.date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        is_available: bool = True,
        break_slots: Optional[List[Dict]] = None,
        zones: Optional[List[str]] = None
    ) -> DriverCalendar:
        """
        Update or create driver availability for a specific date.
        
        Args:
            driver: The driver
            date: The date to update
            start_time: Work start time
            end_time: Work end time
            is_available: Whether driver is available
            break_slots: List of break periods
            zones: Preferred zones for the day
            
        Returns:
            Updated DriverCalendar entry
        """
        calendar, created = DriverCalendar.objects.get_or_create(
            driver=driver,
            date=date,
            defaults={
                'start_time': start_time or self.DEFAULT_START_TIME,
                'end_time': end_time or self.DEFAULT_END_TIME,
                'is_available': is_available,
            }
        )
        
        if not created:
            # Update existing entry
            if start_time:
                calendar.start_time = start_time
            if end_time:
                calendar.end_time = end_time
            calendar.is_available = is_available
        
        # Update break slots
        if break_slots:
            calendar.break_slots = break_slots
        
        # Update preferred zones
        if zones:
            calendar.preferred_zones = zones
        
        # Recalculate metrics
        self._update_calendar_metrics(calendar)
        
        calendar.save()
        
        logger.info(
            f"Updated availability for driver {driver.id} on {date}: "
            f"{calendar.start_time}-{calendar.end_time}"
        )
        
        return calendar
    
    def check_driver_availability(
        self,
        driver: Driver,
        pickup_datetime: datetime,
        duration_minutes: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if driver is available for a specific time slot.
        
        Args:
            driver: The driver to check
            pickup_datetime: Proposed pickup time
            duration_minutes: Expected ride duration
            
        Returns:
            Tuple of (is_available, reason_if_not)
        """
        date = pickup_datetime.date()
        
        # Get calendar entry
        try:
            calendar = DriverCalendar.objects.get(driver=driver, date=date)
        except DriverCalendar.DoesNotExist:
            return False, "Driver has not set availability for this date"
        
        if not calendar.is_available:
            return False, "Driver is not available on this date"
        
        # Check working hours
        start_time = pickup_datetime.time()
        end_time = (pickup_datetime + timedelta(minutes=duration_minutes)).time()
        
        if start_time < calendar.start_time:
            return False, f"Pickup time is before driver's start time ({calendar.start_time})"
        
        if end_time > calendar.end_time:
            return False, f"Ride would end after driver's end time ({calendar.end_time})"
        
        # Check for conflicts with existing bookings
        conflict = self._check_booking_conflicts(
            driver, pickup_datetime, duration_minutes
        )
        if conflict:
            return False, f"Conflicts with existing booking"
        
        # Check break times
        if self._conflicts_with_break(calendar, pickup_datetime, duration_minutes):
            return False, "Conflicts with driver's scheduled break"
        
        # Check if within booking limit
        if calendar.max_bookings and calendar.total_bookings >= calendar.max_bookings:
            return False, "Driver has reached booking limit for this date"
        
        return True, None
    
    def _check_booking_conflicts(
        self,
        driver: Driver,
        pickup_datetime: datetime,
        duration_minutes: int
    ) -> bool:
        """Check for conflicts with existing bookings"""
        start_window = pickup_datetime - timedelta(minutes=self.BUFFER_BETWEEN_RIDES)
        end_window = pickup_datetime + timedelta(
            minutes=duration_minutes + self.BUFFER_BETWEEN_RIDES
        )
        
        conflicts = PreBookedRide.objects.filter(
            assigned_driver=driver,
            status__in=['driver_assigned', 'confirmed'],
            scheduled_pickup_time__date=pickup_datetime.date()
        ).filter(
            models.Q(scheduled_pickup_time__range=(start_window, end_window)) |
            models.Q(
                scheduled_pickup_time__lte=start_window,
                scheduled_pickup_time__gt=start_window - timedelta(
                    minutes=models.F('estimated_duration_minutes') + self.BUFFER_BETWEEN_RIDES
                )
            )
        )
        
        return conflicts.exists()
    
    def _conflicts_with_break(
        self,
        calendar: DriverCalendar,
        pickup_datetime: datetime,
        duration_minutes: int
    ) -> bool:
        """Check if ride conflicts with scheduled breaks"""
        ride_start = pickup_datetime.time()
        ride_end = (pickup_datetime + timedelta(minutes=duration_minutes)).time()
        
        for break_slot in calendar.break_slots:
            break_start = time.fromisoformat(break_slot['start'])
            break_end = time.fromisoformat(break_slot['end'])
            
            # Check for any overlap
            if not (ride_end <= break_start or ride_start >= break_end):
                return True
        
        return False
    
    def _update_calendar_metrics(self, calendar: DriverCalendar):
        """Update calendar metrics (bookings, earnings, utilization)"""
        # Count bookings for the date
        bookings = PreBookedRide.objects.filter(
            matched_driver=calendar.driver,
            pickup_datetime__date=calendar.date,
            status__in=['matched', 'confirmed', 'completed']
        )
        
        calendar.total_bookings = bookings.count()
        calendar.total_estimated_earnings = bookings.aggregate(
            total=Sum('estimated_fare')
        )['total'] or Decimal('0')
        
        # Calculate utilization
        if calendar.is_available:
            total_minutes = self._calculate_working_minutes(calendar)
            booked_minutes = bookings.aggregate(
                total=Sum('estimated_duration_minutes')
            )['total'] or 0
            
            if total_minutes > 0:
                calendar.utilization_percent = min(
                    100,
                    (booked_minutes / total_minutes) * 100
                )
            else:
                calendar.utilization_percent = 0
    
    def _calculate_working_minutes(self, calendar: DriverCalendar) -> int:
        """Calculate total working minutes excluding breaks"""
        # Total time between start and end
        start_datetime = datetime.combine(calendar.date, calendar.start_time)
        end_datetime = datetime.combine(calendar.date, calendar.end_time)
        total_minutes = int((end_datetime - start_datetime).total_seconds() / 60)
        
        # Subtract break time
        break_minutes = 0
        for break_slot in calendar.break_slots:
            break_start = time.fromisoformat(break_slot['start'])
            break_end = time.fromisoformat(break_slot['end'])
            break_duration = (
                datetime.combine(calendar.date, break_end) -
                datetime.combine(calendar.date, break_start)
            ).total_seconds() / 60
            break_minutes += break_duration
        
        return max(0, total_minutes - break_minutes)
    
    def get_driver_schedule(
        self,
        driver: Driver,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> Dict[str, List]:
        """
        Get driver's schedule for a date range.
        
        Args:
            driver: The driver
            start_date: Start of range
            end_date: End of range
            
        Returns:
            Dict with calendar entries and bookings
        """
        # Get calendar entries
        calendars = DriverCalendar.objects.filter(
            driver=driver,
            date__range=(start_date, end_date)
        ).order_by('date')
        
        # Get bookings
        bookings = PreBookedRide.objects.filter(
            matched_driver=driver,
            pickup_datetime__date__range=(start_date, end_date),
            status__in=['matched', 'confirmed', 'completed']
        ).select_related('rider').order_by('pickup_datetime')
        
        # Organize by date
        schedule = {}
        for date in self._date_range(start_date, end_date):
            date_str = date.isoformat()
            schedule[date_str] = {
                'calendar': None,
                'bookings': [],
                'gaps': [],
            }
        
        # Add calendar entries
        for calendar in calendars:
            date_str = calendar.date.isoformat()
            schedule[date_str]['calendar'] = calendar
        
        # Add bookings
        for booking in bookings:
            date_str = booking.pickup_datetime.date().isoformat()
            schedule[date_str]['bookings'].append(booking)
        
        # Identify gaps for optimization
        for date_str, day_data in schedule.items():
            if day_data['calendar'] and day_data['bookings']:
                gaps = self._identify_schedule_gaps(
                    day_data['calendar'],
                    day_data['bookings']
                )
                day_data['gaps'] = gaps
        
        return schedule
    
    def _date_range(self, start_date: datetime.date, end_date: datetime.date):
        """Generate date range"""
        current = start_date
        while current <= end_date:
            yield current
            current += timedelta(days=1)
    
    def _identify_schedule_gaps(
        self,
        calendar: DriverCalendar,
        bookings: List[PreBookedRide]
    ) -> List[Dict]:
        """Identify gaps in schedule that could be filled"""
        gaps = []
        
        # Sort bookings by time
        sorted_bookings = sorted(bookings, key=lambda b: b.scheduled_pickup_time)
        
        # Check gap at start of day
        work_start = datetime.combine(calendar.date, calendar.start_time)
        if sorted_bookings:
            first_pickup = sorted_bookings[0].scheduled_pickup_time
            gap_minutes = (first_pickup - work_start).total_seconds() / 60
            
            if gap_minutes >= 45:  # Minimum useful gap
                gaps.append({
                    'start': work_start.time(),
                    'end': first_pickup.time(),
                    'duration_minutes': int(gap_minutes),
                    'type': 'start_of_day',
                })
        
        # Check gaps between bookings
        for i in range(len(sorted_bookings) - 1):
            current_end = (
                sorted_bookings[i].scheduled_pickup_time +
                timedelta(minutes=sorted_bookings[i].estimated_duration_minutes)
            )
            next_start = sorted_bookings[i + 1].scheduled_pickup_time
            
            gap_minutes = (next_start - current_end).total_seconds() / 60
            
            if gap_minutes >= 45:  # Minimum useful gap
                gaps.append({
                    'start': current_end.time(),
                    'end': next_start.time(),
                    'duration_minutes': int(gap_minutes),
                    'type': 'between_rides',
                    'after_booking_id': sorted_bookings[i].id,
                    'before_booking_id': sorted_bookings[i + 1].id,
                })
        
        # Check gap at end of day
        if sorted_bookings:
            last_booking = sorted_bookings[-1]
            last_end = (
                last_booking.scheduled_pickup_time +
                timedelta(minutes=last_booking.estimated_duration_minutes)
            )
            work_end = datetime.combine(calendar.date, calendar.end_time)
            
            gap_minutes = (work_end - last_end).total_seconds() / 60
            
            if gap_minutes >= 45:  # Minimum useful gap
                gaps.append({
                    'start': last_end.time(),
                    'end': work_end.time(),
                    'duration_minutes': int(gap_minutes),
                    'type': 'end_of_day',
                })
        
        return gaps
    
    @transaction.atomic
    def optimize_waiting_time(
        self,
        driver: Driver,
        original_booking: PreBookedRide,
        wait_location: Dict[str, float],
        wait_duration_minutes: int
    ) -> WaitingTimeOptimization:
        """
        Create optimization record for waiting time between rides.
        
        Args:
            driver: The driver
            original_booking: The booking causing the wait
            wait_location: Location during wait
            wait_duration_minutes: Duration of wait
            
        Returns:
            WaitingTimeOptimization record
        """
        wait_start = (
            original_booking.pickup_datetime +
            timedelta(minutes=original_booking.estimated_duration_minutes)
        )
        wait_end = wait_start + timedelta(minutes=wait_duration_minutes)
        
        optimization = WaitingTimeOptimization.objects.create(
            driver=driver,
            original_ride=original_booking,
            wait_start=wait_start,
            wait_end=wait_end,
            location_lat=Decimal(str(wait_location['lat'])),
            location_lng=Decimal(str(wait_location['lng'])),
            max_distance_km=Decimal('5.0'),  # Default 5km radius
            min_fare=Decimal('10.0'),  # Minimum €10 fare
        )
        
        # Schedule task to find opportunities
        # TODO: Implement with Celery
        # find_waiting_opportunities_task.delay(optimization.id)
        
        return optimization
    
    def suggest_schedule_improvements(
        self,
        driver: Driver,
        date: datetime.date
    ) -> List[Dict]:
        """
        Suggest improvements to driver's schedule.
        
        Args:
            driver: The driver
            date: The date to analyze
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        try:
            calendar = DriverCalendar.objects.get(driver=driver, date=date)
        except DriverCalendar.DoesNotExist:
            return [{
                'type': 'missing_availability',
                'message': 'Set your availability to receive bookings',
                'priority': 'high',
            }]
        
        # Check utilization
        if calendar.utilization_percent < 50:
            suggestions.append({
                'type': 'low_utilization',
                'message': f'Your schedule is only {calendar.utilization_percent:.0f}% full',
                'recommendation': 'Consider accepting more bookings or adjusting hours',
                'priority': 'medium',
            })
        
        # Check for long gaps
        schedule = self.get_driver_schedule(driver, date, date)
        gaps = schedule[date.isoformat()]['gaps']
        
        for gap in gaps:
            if gap['duration_minutes'] > 90:
                suggestions.append({
                    'type': 'long_gap',
                    'message': f"{gap['duration_minutes']} minute gap {gap['type'].replace('_', ' ')}",
                    'recommendation': 'This time could be used for additional rides',
                    'gap_info': gap,
                    'priority': 'low',
                })
        
        # Check working hours
        working_minutes = self._calculate_working_minutes(calendar)
        if working_minutes < 360:  # Less than 6 hours
            suggestions.append({
                'type': 'short_hours',
                'message': 'You\'re working less than 6 hours',
                'recommendation': 'Consider extending your availability for more earnings',
                'priority': 'low',
            })
        
        return suggestions
    
    def _update_calendar_metrics(self, calendar: DriverCalendar):
        """Update calendar metrics like booking counts and earnings"""
        date = calendar.date
        
        # Count bookings for this date
        bookings = PreBookedRide.objects.filter(
            assigned_driver=calendar.driver,
            scheduled_pickup_time__date=date,
            status__in=['driver_assigned', 'confirmed', 'completed']
        )
        
        calendar.current_bookings = bookings.count()
        
        # Calculate total estimated earnings
        total_earnings = Decimal('0.00')
        for booking in bookings:
            if booking.estimated_fare:
                total_earnings += booking.estimated_fare
        
        calendar.total_estimated_earnings = total_earnings
        
        # Calculate utilization
        if calendar.is_available and calendar.start_time and calendar.end_time:
            total_hours = (
                datetime.combine(date, calendar.end_time) -
                datetime.combine(date, calendar.start_time)
            ).total_seconds() / 3600
            
            busy_hours = 0
            for booking in bookings:
                busy_hours += (booking.estimated_duration_minutes + 30) / 60  # Include buffer
            
            if total_hours > 0:
                calendar.utilization_percent = min(100, (busy_hours / total_hours) * 100)
            else:
                calendar.utilization_percent = 0
    
    @transaction.atomic
    def add_booking_to_calendar(self, booking: PreBookedRide, driver: Driver):
        """Add an accepted booking to driver's calendar"""
        date = booking.scheduled_pickup_time.date()
        
        # Get or create calendar entry for the date
        calendar, created = DriverCalendar.objects.get_or_create(
            driver=driver,
            date=date,
            defaults={
                'start_time': self.DEFAULT_START_TIME,
                'end_time': self.DEFAULT_END_TIME,
                'is_available': True,
            }
        )
        
        # Update metrics
        self._update_calendar_metrics(calendar)
        calendar.save()
        
        logger.info(
            f"Added booking {booking.id} to driver {driver.id}'s calendar for {date}"
        )
    
    def _calculate_working_minutes(self, calendar: DriverCalendar) -> int:
        """Calculate total working minutes for a calendar entry"""
        if not calendar.start_time or not calendar.end_time:
            return 0
        
        start = datetime.combine(calendar.date, calendar.start_time)
        end = datetime.combine(calendar.date, calendar.end_time)
        
        return int((end - start).total_seconds() / 60)