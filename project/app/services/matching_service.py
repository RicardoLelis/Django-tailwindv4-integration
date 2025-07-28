"""
Driver matching service for pre-booked rides.
Implements intelligent matching algorithm with scoring system.
"""

from django.db import transaction
from django.db.models import Q, F, Count, Avg
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import math
import logging

from ..models import (
    PreBookedRide, Driver, Vehicle, RideMatchOffer,
    DriverCalendar, WaitingTimeOptimization
)

logger = logging.getLogger(__name__)


class MatchingService:
    """Service for matching drivers to pre-booked rides"""
    
    # Scoring weights (total = 100)
    DISTANCE_WEIGHT = 30
    EXPERIENCE_WEIGHT = 25
    AVAILABILITY_WEIGHT = 20
    EFFICIENCY_WEIGHT = 15
    RATING_WEIGHT = 10
    
    def find_best_matches(
        self,
        booking: PreBookedRide,
        max_offers: int = 5,
        search_radius_km: float = 10.0
    ) -> List[Tuple[Driver, Dict]]:
        """
        Find the best available drivers for a pre-booked ride.
        
        Args:
            booking: The pre-booked ride to match
            max_offers: Maximum number of offers to generate
            search_radius_km: Search radius for drivers
            
        Returns:
            List of (driver, score_dict) tuples
        """
        # Step 1: Get available drivers
        available_drivers = self._get_available_drivers(
            booking.scheduled_pickup_time,
            booking.estimated_duration_minutes,
            booking.pickup_latitude,
            booking.pickup_longitude,
            search_radius_km
        )
        
        # Step 2: Filter by requirements
        if booking.wheelchair_required:
            available_drivers = self._filter_by_accessibility(
                available_drivers,
                booking.assistance_required
            )
        
        # Step 3: Calculate scores for each driver
        scored_drivers = []
        for driver in available_drivers:
            score = self._calculate_match_score(driver, booking)
            if score['total_score'] > 50:  # Minimum threshold
                scored_drivers.append((driver, score))
        
        # Step 4: Sort by total score
        scored_drivers.sort(key=lambda x: x[1]['total_score'], reverse=True)
        
        # Step 5: Return top matches
        return scored_drivers[:max_offers]
    
    def _get_available_drivers(
        self,
        pickup_datetime: datetime,
        duration_minutes: int,
        pickup_lat: Decimal,
        pickup_lng: Decimal,
        radius_km: float
    ) -> List[Driver]:
        """Get drivers available at the specified time"""
        # Calculate time window
        start_time = pickup_datetime
        end_time = pickup_datetime + timedelta(minutes=duration_minutes + 30)  # Buffer
        
        # Get drivers who are:
        # 1. Active and approved
        # 2. Available during the time window
        # 3. Within the search radius (approximate)
        
        available_drivers = Driver.objects.filter(
            is_active=True,
            application_status='approved',
            training_completed=True,
            assessment_passed=True
        ).exclude(
            # Exclude drivers with conflicting pre-booked rides
            pre_booked_assignments__scheduled_pickup_time__range=(
                start_time - timedelta(hours=1),
                end_time + timedelta(hours=1)
            ),
            pre_booked_assignments__status__in=['confirmed', 'driver_assigned']
        )
        
        # Filter by calendar availability
        pickup_date = pickup_datetime.date()
        available_drivers = available_drivers.filter(
            calendar_entries__date=pickup_date,
            calendar_entries__is_available=True
        ).distinct()
        
        # Apply radius filter (rough filtering, exact distance calculated later)
        lat_range = radius_km / 111.0  # Rough conversion
        lng_range = radius_km / (111.0 * abs(math.cos(math.radians(float(pickup_lat)))))
        
        available_drivers = available_drivers.filter(
            current_location__isnull=False,
            current_location__lat__range=(
                float(pickup_lat) - lat_range,
                float(pickup_lat) + lat_range
            ),
            current_location__lng__range=(
                float(pickup_lng) - lng_range,
                float(pickup_lng) + lng_range
            )
        )
        
        return list(available_drivers)
    
    def _filter_by_accessibility(
        self,
        drivers: List[Driver],
        assistance_required: List[str]
    ) -> List[Driver]:
        """Filter drivers by accessibility requirements"""
        filtered_drivers = []
        
        for driver in drivers:
            # Check if driver has accessible vehicles
            accessible_vehicles = driver.vehicles.filter(
                is_active=True,
                is_accessible=True
            )
            
            if not accessible_vehicles.exists():
                continue
            
            # Check specific requirements
            if assistance_required:
                # Check if driver has training for required assistance
                driver_training = set(driver.accessibility_training)
                required_training = set(assistance_required)
                
                if not required_training.issubset(driver_training):
                    continue
            
            filtered_drivers.append(driver)
        
        return filtered_drivers
    
    def _calculate_match_score(
        self,
        driver: Driver,
        booking: PreBookedRide
    ) -> Dict[str, float]:
        """Calculate comprehensive match score for a driver"""
        scores = {
            'distance_score': self._calculate_distance_score(driver, booking),
            'experience_score': self._calculate_experience_score(driver, booking),
            'availability_score': self._calculate_availability_score(driver, booking),
            'efficiency_score': self._calculate_efficiency_score(driver, booking),
            'rating_score': self._calculate_rating_score(driver),
        }
        
        # Calculate weighted total
        scores['total_score'] = (
            scores['distance_score'] * self.DISTANCE_WEIGHT / 100 +
            scores['experience_score'] * self.EXPERIENCE_WEIGHT / 100 +
            scores['availability_score'] * self.AVAILABILITY_WEIGHT / 100 +
            scores['efficiency_score'] * self.EFFICIENCY_WEIGHT / 100 +
            scores['rating_score'] * self.RATING_WEIGHT / 100
        ) * 100
        
        return scores
    
    def _calculate_distance_score(
        self,
        driver: Driver,
        booking: PreBookedRide
    ) -> float:
        """Calculate score based on distance to pickup (0-100)"""
        if not driver.current_location:
            return 0
        
        # Calculate distance using Haversine formula
        distance_km = self._haversine_distance(
            float(driver.current_location.get('lat', 0)),
            float(driver.current_location.get('lng', 0)),
            float(booking.pickup_lat),
            float(booking.pickup_lng)
        )
        
        # Score calculation: closer = higher score
        if distance_km <= 1:
            return 100
        elif distance_km <= 3:
            return 90
        elif distance_km <= 5:
            return 75
        elif distance_km <= 10:
            return 50
        elif distance_km <= 15:
            return 25
        else:
            return 0
    
    def _calculate_experience_score(
        self,
        driver: Driver,
        booking: PreBookedRide
    ) -> float:
        """Calculate score based on driver experience (0-100)"""
        score = 50  # Base score
        
        # Total rides experience
        if driver.total_rides > 500:
            score += 20
        elif driver.total_rides > 200:
            score += 15
        elif driver.total_rides > 50:
            score += 10
        
        # Medical/accessibility experience if relevant
        if booking.purpose == 'medical' or booking.wheelchair_required:
            # Get medical ride count
            medical_rides = driver.driver_rides.filter(
                ride__rider__disabilities__contains=['wheelchair']
            ).count()
            
            if medical_rides > 100:
                score += 30
            elif medical_rides > 50:
                score += 20
            elif medical_rides > 20:
                score += 10
        
        return min(score, 100)
    
    def _calculate_availability_score(
        self,
        driver: Driver,
        booking: PreBookedRide
    ) -> float:
        """Calculate score based on driver availability (0-100)"""
        try:
            calendar = DriverCalendar.objects.get(
                driver=driver,
                date=booking.scheduled_pickup_time.date()
            )
            
            # Check if booking fits well within working hours
            booking_start = booking.scheduled_pickup_time.time()
            booking_end = (
                booking.scheduled_pickup_time + 
                timedelta(minutes=booking.estimated_duration_minutes + 30)
            ).time()
            
            if (calendar.start_time <= booking_start and 
                calendar.end_time >= booking_end):
                # Perfect fit
                score = 100
            else:
                # Partial fit
                score = 50
            
            # Reduce score based on existing bookings
            utilization = calendar.utilization_percent
            if utilization < 50:
                score *= 1.0  # No penalty
            elif utilization < 70:
                score *= 0.9  # Small penalty
            else:
                score *= 0.7  # Larger penalty
            
            return score
            
        except DriverCalendar.DoesNotExist:
            return 0
    
    def _calculate_efficiency_score(
        self,
        driver: Driver,
        booking: PreBookedRide
    ) -> float:
        """Calculate route efficiency score (0-100)"""
        # Check for nearby bookings
        time_window_start = booking.scheduled_pickup_time - timedelta(hours=2)
        time_window_end = booking.scheduled_pickup_time + timedelta(hours=2)
        
        nearby_bookings = PreBookedRide.objects.filter(
            assigned_driver=driver,
            scheduled_pickup_time__range=(time_window_start, time_window_end),
            status__in=['matched', 'confirmed', 'driver_assigned']
        ).exclude(id=booking.id)
        
        if not nearby_bookings.exists():
            # No nearby bookings, neutral score
            return 50
        
        # Calculate efficiency based on route optimization potential
        efficiency_score = 50
        
        for other_booking in nearby_bookings:
            # Check if this booking creates an efficient route
            distance_between = self._haversine_distance(
                float(other_booking.dropoff_latitude),
                float(other_booking.dropoff_longitude),
                float(booking.pickup_latitude),
                float(booking.pickup_longitude)
            )
            
            time_gap = abs(
                (booking.scheduled_pickup_time - other_booking.scheduled_pickup_time).total_seconds() / 60
            )
            
            # Good match: short distance and appropriate time gap
            if distance_between < 5 and 30 < time_gap < 90:
                efficiency_score += 25
            elif distance_between < 10 and 30 < time_gap < 120:
                efficiency_score += 15
            else:
                efficiency_score -= 10
        
        return max(0, min(efficiency_score, 100))
    
    def _calculate_rating_score(self, driver: Driver) -> float:
        """Calculate score based on driver rating (0-100)"""
        if driver.rating >= 4.8:
            return 100
        elif driver.rating >= 4.5:
            return 85
        elif driver.rating >= 4.0:
            return 70
        elif driver.rating >= 3.5:
            return 50
        else:
            return 30
    
    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (
            math.sin(delta_lat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) *
            math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @transaction.atomic
    def create_match_offers(
        self,
        booking: PreBookedRide,
        drivers_scores: List[Tuple[Driver, Dict]],
        offer_duration_hours: int = 2
    ) -> List[RideMatchOffer]:
        """
        Create match offers for selected drivers.
        
        Args:
            booking: The booking to match
            drivers_scores: List of (driver, scores) tuples
            offer_duration_hours: How long offers remain valid
            
        Returns:
            List of created offers
        """
        offers = []
        expires_at = timezone.now() + timedelta(hours=offer_duration_hours)
        
        for driver, scores in drivers_scores:
            # Calculate fare for this driver
            base_fare = booking.estimated_fare
            
            # Add incentive for high-priority rides
            if booking.priority == 'high':
                incentive = base_fare * Decimal('0.15')  # 15% bonus
            elif booking.priority == 'urgent':
                incentive = base_fare * Decimal('0.25')  # 25% bonus
            else:
                incentive = Decimal('0')
            
            offer = RideMatchOffer.objects.create(
                pre_booked_ride=booking,
                driver=driver,
                expires_at=expires_at,
                base_fare=base_fare,
                bonus_amount=incentive,
                total_earnings=base_fare + incentive,
                compatibility_score=Decimal(str(scores['total_score'])),
                distance_to_pickup_km=Decimal(str(
                    self._haversine_distance(
                        float(driver.current_location.get('lat', 0)),
                        float(driver.current_location.get('lng', 0)),
                        float(booking.pickup_latitude),
                        float(booking.pickup_longitude)
                    )
                ))
            )
            
            offers.append(offer)
            
            # Send notification to driver
            self._send_offer_notification(driver, offer)
        
        logger.info(
            f"Created {len(offers)} match offers for booking {booking.id}"
        )
        
        return offers
    
    def _send_offer_notification(self, driver: Driver, offer: RideMatchOffer):
        """Send push notification to driver about new offer"""
        # TODO: Implement push notification
        # notification_service.send_push(
        #     driver.user,
        #     title="New ride offer!",
        #     body=f"€{offer.total_fare} ride from {offer.pre_booked_ride.pickup_location}",
        #     data={'offer_id': offer.id}
        # )
        pass
    
    @transaction.atomic
    def handle_offer_response(
        self,
        offer: RideMatchOffer,
        accepted: bool,
        decline_reason: Optional[str] = None
    ) -> bool:
        """
        Handle driver's response to an offer.
        
        Args:
            offer: The offer being responded to
            accepted: Whether the offer was accepted
            decline_reason: Reason if declined
            
        Returns:
            Success status
        """
        # Check if offer is still valid
        if offer.status != 'pending' or offer.expires_at < timezone.now():
            return False
        
        booking = offer.pre_booked_ride
        
        if accepted:
            # Check if ride is still available
            if booking.status != 'pending':
                offer.status = 'expired'
                offer.save()
                return False
            
            # Accept the offer
            offer.accept()
            
            # Decline all other pending offers
            RideMatchOffer.objects.filter(
                pre_booked_ride=booking,
                status='pending'
            ).exclude(id=offer.id).update(
                status='expired'
            )
            
            logger.info(
                f"Driver {offer.driver.id} accepted offer for booking {booking.id}"
            )
            
            return True
        else:
            # Decline the offer
            offer.decline(decline_reason)
            
            # Check if we need to create new offers
            remaining_offers = RideMatchOffer.objects.filter(
                pre_booked_ride=booking,
                status='pending'
            ).count()
            
            if remaining_offers == 0:
                # No more pending offers, create new batch
                self._create_next_batch_offers(booking)
            
            return True
    
    def _create_next_batch_offers(self, booking: PreBookedRide):
        """Create next batch of offers if all previous ones were declined"""
        # Get drivers who haven't been offered yet
        offered_drivers = RideMatchOffer.objects.filter(
            pre_booked_ride=booking
        ).values_list('driver_id', flat=True)
        
        # Find new matches excluding already offered drivers
        new_matches = self.find_best_matches(
            booking,
            max_offers=3,
            search_radius_km=15.0  # Expand search radius
        )
        
        # Filter out already offered drivers
        new_matches = [
            (driver, score) for driver, score in new_matches
            if driver.id not in offered_drivers
        ]
        
        if new_matches:
            self.create_match_offers(booking, new_matches)
        else:
            # No more drivers available, mark booking as unmatched
            booking.status = 'unmatched'
            booking.save()
            
            # Notify rider
            # notification_service.send_email(
            #     booking.rider.user.email,
            #     "Unable to find driver",
            #     "We're having trouble finding a driver for your booking..."
            # )