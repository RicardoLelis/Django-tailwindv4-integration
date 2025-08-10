"""
Pricing service for calculating fares and fees.
Centralized pricing logic following DRY principles.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Optional
from django.utils import timezone
from django.conf import settings

from ..models import PreBookedRide


class PricingService:
    """Service for all pricing calculations"""
    
    # Base rates (configurable via settings)
    BASE_FARE = Decimal(getattr(settings, 'RIDE_BASE_FARE', '5.00'))
    DISTANCE_RATE_PER_KM = Decimal(getattr(settings, 'RIDE_DISTANCE_RATE', '1.50'))
    TIME_RATE_PER_MIN = Decimal(getattr(settings, 'RIDE_TIME_RATE', '0.30'))
    PRE_BOOKING_FEE = Decimal(getattr(settings, 'PRE_BOOKING_FEE', '2.00'))
    
    # Accessibility surcharges
    WHEELCHAIR_SURCHARGE = Decimal(getattr(settings, 'WHEELCHAIR_SURCHARGE', '3.00'))
    
    # Round trip discount
    ROUND_TRIP_DISCOUNT = Decimal(getattr(settings, 'ROUND_TRIP_DISCOUNT', '0.10'))
    
    # Waiting fees
    FREE_WAITING_MINUTES = 15
    WAITING_RATE_PER_HOUR = Decimal(getattr(settings, 'WAITING_RATE_PER_HOUR', '10.00'))
    EXTENDED_WAITING_RATE = Decimal(getattr(settings, 'EXTENDED_WAITING_RATE', '15.00'))
    
    # Priority multipliers
    PRIORITY_MULTIPLIERS = {
        'normal': Decimal('1.0'),
        'high': Decimal('1.15'),
        'urgent': Decimal('1.30'),
    }
    
    # Cancellation policies
    CANCELLATION_POLICIES = {
        'rider': {
            24: Decimal('0'),      # 24+ hours: no fee
            2: Decimal('5.00'),    # 2-24 hours: €5
            0: Decimal('0.50'),    # <2 hours: 50% of fare
        },
        'driver': {
            'penalty': Decimal('10.00'),  # Driver penalty
            'rider_compensation': Decimal('5.00'),  # Rider compensation
        }
    }
    
    def calculate_pre_booked_fare(
        self,
        distance_km: float,
        duration_minutes: int,
        booking_type: str = 'single',
        priority: str = 'normal',
        wheelchair_required: bool = False,
        waiting_duration_minutes: Optional[int] = None
    ) -> Decimal:
        """
        Calculate fare for a pre-booked ride.
        
        Args:
            distance_km: Distance in kilometers
            duration_minutes: Estimated duration in minutes
            booking_type: 'single', 'round_trip', or 'recurring'
            priority: 'normal', 'high', or 'urgent'
            wheelchair_required: Whether wheelchair access is needed
            waiting_duration_minutes: Waiting time for round trips
            
        Returns:
            Total estimated fare
        """
        # Base calculation
        distance_fare = Decimal(str(distance_km)) * self.DISTANCE_RATE_PER_KM
        time_fare = Decimal(str(duration_minutes)) * self.TIME_RATE_PER_MIN
        
        subtotal = self.BASE_FARE + distance_fare + time_fare + self.PRE_BOOKING_FEE
        
        # Add accessibility surcharge if needed
        if wheelchair_required:
            subtotal += self.WHEELCHAIR_SURCHARGE
        
        # Apply priority multiplier
        priority_multiplier = self.PRIORITY_MULTIPLIERS.get(priority, Decimal('1.0'))
        subtotal *= priority_multiplier
        
        # Handle round trip pricing
        if booking_type == 'round_trip':
            # Double the fare for round trip
            subtotal *= 2
            
            # Apply round trip discount
            subtotal *= (1 - self.ROUND_TRIP_DISCOUNT)
            
            # Add waiting fee if applicable
            if waiting_duration_minutes:
                waiting_fee = self.calculate_waiting_fee(waiting_duration_minutes)
                subtotal += waiting_fee
        
        return self._round_fare(subtotal)
    
    def calculate_waiting_fee(self, waiting_minutes: int) -> Decimal:
        """
        Calculate waiting fee for round trips.
        
        Args:
            waiting_minutes: Total waiting time in minutes
            
        Returns:
            Waiting fee amount
        """
        if waiting_minutes <= self.FREE_WAITING_MINUTES:
            return Decimal('0')
        
        billable_minutes = waiting_minutes - self.FREE_WAITING_MINUTES
        billable_hours = Decimal(str(billable_minutes)) / 60
        
        if waiting_minutes <= 60:
            # Standard rate for first hour
            fee = billable_hours * self.WAITING_RATE_PER_HOUR
        else:
            # First 45 minutes at standard rate (60 - 15 free)
            first_period = Decimal('0.75') * self.WAITING_RATE_PER_HOUR
            
            # Remaining time at extended rate
            remaining_hours = (Decimal(str(waiting_minutes - 60)) / 60)
            extended_fee = remaining_hours * self.EXTENDED_WAITING_RATE
            
            fee = first_period + extended_fee
        
        return self._round_fare(fee)
    
    def calculate_cancellation_fee(
        self,
        booking: PreBookedRide,
        cancelled_by: str = 'rider'
    ) -> Decimal:
        """
        Calculate cancellation fee based on policy.
        
        Args:
            booking: The booking being cancelled
            cancelled_by: Who is cancelling ('rider' or 'driver')
            
        Returns:
            Cancellation fee amount
        """
        if cancelled_by == 'driver':
            # Driver pays penalty
            return self.CANCELLATION_POLICIES['driver']['penalty']
        
        # Calculate hours until pickup
        hours_until_pickup = (
            booking.pickup_datetime - timezone.now()
        ).total_seconds() / 3600
        
        # Apply rider cancellation policy
        if hours_until_pickup >= 24:
            return Decimal('0')
        elif hours_until_pickup >= 2:
            return self.CANCELLATION_POLICIES['rider'][2]
        else:
            # Less than 2 hours: 50% of fare
            return booking.estimated_fare * self.CANCELLATION_POLICIES['rider'][0]
    
    def calculate_driver_earnings(
        self,
        gross_fare: Decimal,
        platform_commission: Optional[Decimal] = None
    ) -> Dict[str, Decimal]:
        """
        Calculate driver earnings and platform fee.
        
        Args:
            gross_fare: Total fare paid by rider
            platform_commission: Platform commission rate (default from settings)
            
        Returns:
            Dict with driver_earnings and platform_fee
        """
        if platform_commission is None:
            platform_commission = Decimal(
                getattr(settings, 'PLATFORM_COMMISSION', '0.20')
            )
        
        platform_fee = gross_fare * platform_commission
        driver_earnings = gross_fare - platform_fee
        
        return {
            'driver_earnings': self._round_fare(driver_earnings),
            'platform_fee': self._round_fare(platform_fee),
        }
    
    def calculate_surge_pricing(
        self,
        base_fare: Decimal,
        demand_level: str = 'normal'
    ) -> Decimal:
        """
        Calculate surge pricing based on demand.
        
        Args:
            base_fare: Base fare amount
            demand_level: 'low', 'normal', 'high', 'very_high'
            
        Returns:
            Fare with surge pricing applied
        """
        surge_multipliers = {
            'low': Decimal('0.9'),      # 10% discount during low demand
            'normal': Decimal('1.0'),   # No change
            'high': Decimal('1.3'),     # 30% surge
            'very_high': Decimal('1.5'), # 50% surge
        }
        
        multiplier = surge_multipliers.get(demand_level, Decimal('1.0'))
        return self._round_fare(base_fare * multiplier)
    
    def estimate_total_cost(
        self,
        booking: PreBookedRide,
        include_tip: bool = False,
        tip_percentage: Optional[Decimal] = None
    ) -> Dict[str, Decimal]:
        """
        Estimate total cost including all fees and optional tip.
        
        Args:
            booking: The pre-booked ride
            include_tip: Whether to include tip in calculation
            tip_percentage: Tip percentage (default 15%)
            
        Returns:
            Dict with cost breakdown
        """
        breakdown = {
            'base_fare': booking.estimated_fare,
            'waiting_fee': booking.waiting_fee or Decimal('0'),
            'subtotal': booking.estimated_fare + (booking.waiting_fee or Decimal('0')),
        }
        
        if include_tip:
            if tip_percentage is None:
                tip_percentage = Decimal('0.15')
            
            tip_amount = breakdown['subtotal'] * tip_percentage
            breakdown['tip'] = self._round_fare(tip_amount)
            breakdown['total'] = breakdown['subtotal'] + breakdown['tip']
        else:
            breakdown['total'] = breakdown['subtotal']
        
        return breakdown
    
    def _round_fare(self, amount: Decimal) -> Decimal:
        """Round fare to 2 decimal places"""
        return amount.quantize(Decimal('0.01'))
    
    def get_fare_estimate_range(
        self,
        distance_km: float,
        duration_minutes: int,
        **kwargs
    ) -> Dict[str, Decimal]:
        """
        Get fare estimate range (min/max) for display.
        
        Args:
            distance_km: Distance in kilometers
            duration_minutes: Duration in minutes
            **kwargs: Additional parameters for fare calculation
            
        Returns:
            Dict with min_fare and max_fare
        """
        base_fare = self.calculate_pre_booked_fare(
            distance_km,
            duration_minutes,
            **kwargs
        )
        
        # Calculate range based on potential surge pricing
        min_fare = self.calculate_surge_pricing(base_fare, 'low')
        max_fare = self.calculate_surge_pricing(base_fare, 'high')
        
        return {
            'min_fare': min_fare,
            'max_fare': max_fare,
            'estimated_fare': base_fare,
        }
    
    def calculate_immediate_fare(
        self,
        distance_km: float,
        duration_minutes: int = None,
        wheelchair_required: bool = False,
        priority: str = 'urgent'  # Immediate rides are typically urgent
    ) -> Decimal:
        """
        Calculate fare for immediate rides (no pre-booking fee).
        
        Args:
            distance_km: Distance in kilometers
            duration_minutes: Estimated duration in minutes (estimated if None)
            wheelchair_required: Whether wheelchair access is needed
            priority: Priority level ('normal', 'high', 'urgent')
            
        Returns:
            Total estimated fare
        """
        # Estimate duration if not provided (average speed ~30 km/h in city)
        if duration_minutes is None:
            duration_minutes = max(5, int(distance_km * 2.5))  # Minimum 5 minutes
        
        # Base calculation (no pre-booking fee for immediate rides)
        distance_fare = Decimal(str(distance_km)) * self.DISTANCE_RATE_PER_KM
        time_fare = Decimal(str(duration_minutes)) * self.TIME_RATE_PER_MIN
        
        subtotal = self.BASE_FARE + distance_fare + time_fare
        
        # Add accessibility surcharge if needed
        if wheelchair_required:
            subtotal += self.WHEELCHAIR_SURCHARGE
        
        # Apply priority multiplier (immediate rides often have higher priority)
        priority_multiplier = self.PRIORITY_MULTIPLIERS.get(priority, Decimal('1.3'))
        subtotal *= priority_multiplier
        
        return self._round_fare(subtotal)