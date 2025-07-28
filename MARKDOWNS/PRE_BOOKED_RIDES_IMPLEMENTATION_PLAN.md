# Pre-Booked Rides Implementation Plan

## Executive Summary

This document outlines a comprehensive plan for implementing a pre-booked rides feature in RideConnect, with a primary focus on medical appointments while supporting general advance bookings. The system will enable riders to schedule rides in advance, match them with suitable drivers, handle round-trip bookings, and optimize driver utilization during waiting periods.

## Business Requirements

### Core Features

1. **Advance Booking System**
   - Book rides up to 30 days in advance
   - Support for single and round-trip bookings
   - Flexible return times for medical appointments
   - Recurring ride scheduling (weekly therapy, dialysis, etc.)

2. **Intelligent Matching Algorithm**
   - Match riders with drivers based on:
     - Vehicle accessibility requirements
     - Driver availability and working hours
     - Geographic efficiency
     - Driver experience with medical rides
     - Cost optimization for both parties

3. **Driver Calendar Management**
   - Visual calendar interface
   - Automatic conflict detection
   - Buffer time management between rides
   - Integration with driver working hours

4. **Waiting Time Optimization**
   - Smart ride suggestions during wait periods
   - Geofenced notifications for nearby opportunities
   - Return trip flexibility

## Technical Architecture

### Data Models

```python
# New Models Required

class PreBookedRide(models.Model):
    """Main model for pre-booked rides"""
    BOOKING_TYPES = [
        ('single', 'One Way'),
        ('round_trip', 'Round Trip'),
        ('recurring', 'Recurring'),
    ]
    
    PURPOSES = [
        ('medical', 'Medical Appointment'),
        ('therapy', 'Therapy Session'),
        ('work', 'Work Commute'),
        ('education', 'School/University'),
        ('social', 'Social/Personal'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Match'),
        ('matched', 'Driver Matched'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic Information
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPES)
    purpose = models.CharField(max_length=20, choices=PURPOSES)
    
    # Locations
    pickup_location = models.CharField(max_length=255)
    pickup_lat = models.DecimalField(max_digits=10, decimal_places=7)
    pickup_lng = models.DecimalField(max_digits=10, decimal_places=7)
    dropoff_location = models.CharField(max_length=255)
    dropoff_lat = models.DecimalField(max_digits=10, decimal_places=7)
    dropoff_lng = models.DecimalField(max_digits=10, decimal_places=7)
    
    # Timing
    pickup_datetime = models.DateTimeField()
    estimated_duration_minutes = models.IntegerField(default=30)
    
    # Round Trip Specific
    return_pickup_datetime = models.DateTimeField(null=True, blank=True)
    flexible_return = models.BooleanField(default=False)
    earliest_return_time = models.TimeField(null=True, blank=True)
    latest_return_time = models.TimeField(null=True, blank=True)
    waiting_duration_minutes = models.IntegerField(null=True, blank=True)
    
    # Requirements
    special_requirements = models.TextField(blank=True)
    wheelchair_required = models.BooleanField(default=False)
    assistance_required = models.JSONField(default=list)
    
    # Matching
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    matched_driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL)
    matched_vehicle = models.ForeignKey(Vehicle, null=True, blank=True, on_delete=models.SET_NULL)
    match_confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Pricing
    estimated_fare = models.DecimalField(max_digits=8, decimal_places=2)
    final_fare = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    waiting_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=100, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['pickup_datetime', 'status']),
            models.Index(fields=['matched_driver', 'pickup_datetime']),
            models.Index(fields=['rider', '-created_at']),
        ]


class DriverCalendar(models.Model):
    """Driver availability and schedule management"""
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    date = models.DateField()
    
    # Working hours for this date
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Blocked time slots
    blocked_slots = models.JSONField(default=list)  # List of {start, end, reason}
    
    # Pre-booked rides for this date
    total_bookings = models.IntegerField(default=0)
    total_estimated_earnings = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['driver', 'date']
        indexes = [
            models.Index(fields=['driver', 'date']),
        ]


class RideMatchOffer(models.Model):
    """Offers sent to drivers for pre-booked rides"""
    pre_booked_ride = models.ForeignKey(PreBookedRide, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    
    # Offer details
    offered_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    fare_amount = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Driver response
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    responded_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.CharField(max_length=100, blank=True)
    
    # Ranking
    match_score = models.DecimalField(max_digits=5, decimal_places=2)  # 0-100
    distance_to_pickup_km = models.DecimalField(max_digits=6, decimal_places=2)
    
    class Meta:
        unique_together = ['pre_booked_ride', 'driver']
        indexes = [
            models.Index(fields=['status', 'expires_at']),
        ]


class WaitingTimeOptimization(models.Model):
    """Track and optimize driver waiting times"""
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    original_ride = models.ForeignKey(PreBookedRide, on_delete=models.CASCADE, related_name='waiting_optimizations')
    
    # Waiting period
    wait_start = models.DateTimeField()
    wait_end = models.DateTimeField()
    location_lat = models.DecimalField(max_digits=10, decimal_places=7)
    location_lng = models.DecimalField(max_digits=10, decimal_places=7)
    
    # Optimization settings
    max_distance_km = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    min_fare = models.DecimalField(max_digits=6, decimal_places=2, default=10.0)
    accepts_short_trips = models.BooleanField(default=True)
    
    # Results
    opportunities_found = models.IntegerField(default=0)
    rides_completed = models.IntegerField(default=0)
    earnings_during_wait = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)


class RecurringRideTemplate(models.Model):
    """Template for recurring rides (dialysis, therapy, etc.)"""
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    
    # Schedule
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ]
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    days_of_week = models.JSONField(default=list)  # [1,3,5] for Mon, Wed, Fri
    
    # Ride details (same as PreBookedRide)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    pickup_time = models.TimeField()
    duration_minutes = models.IntegerField()
    round_trip = models.BooleanField(default=True)
    
    # Preferences
    preferred_driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL)
    special_requirements = models.TextField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    # Auto-booking
    auto_book_days_ahead = models.IntegerField(default=7)
    last_generated_until = models.DateField(null=True, blank=True)
```

### Matching Algorithm

```python
class PreBookedRideMatchingService:
    """
    Intelligent matching service for pre-booked rides
    """
    
    def find_best_drivers(self, pre_booked_ride: PreBookedRide, max_offers: int = 5):
        """
        Find the best available drivers for a pre-booked ride
        """
        # Step 1: Get available drivers
        available_drivers = self._get_available_drivers(
            pre_booked_ride.pickup_datetime,
            pre_booked_ride.estimated_duration_minutes
        )
        
        # Step 2: Filter by accessibility requirements
        if pre_booked_ride.wheelchair_required:
            available_drivers = self._filter_by_accessibility(
                available_drivers,
                pre_booked_ride.assistance_required
            )
        
        # Step 3: Calculate match scores
        scored_drivers = []
        for driver in available_drivers:
            score = self._calculate_match_score(driver, pre_booked_ride)
            scored_drivers.append((driver, score))
        
        # Step 4: Sort by score and return top matches
        scored_drivers.sort(key=lambda x: x[1]['total_score'], reverse=True)
        return scored_drivers[:max_offers]
    
    def _calculate_match_score(self, driver, ride):
        """
        Calculate comprehensive match score (0-100)
        """
        scores = {
            'distance_score': self._distance_score(driver, ride),  # 0-30 points
            'experience_score': self._experience_score(driver, ride),  # 0-25 points
            'availability_score': self._availability_score(driver, ride),  # 0-20 points
            'efficiency_score': self._efficiency_score(driver, ride),  # 0-15 points
            'rating_score': self._rating_score(driver),  # 0-10 points
        }
        
        scores['total_score'] = sum(scores.values())
        return scores
    
    def _efficiency_score(self, driver, ride):
        """
        Calculate route efficiency considering:
        - Other bookings on the same day
        - Potential for combining trips
        - Dead mileage minimization
        """
        # Check for rides before and after
        buffer_minutes = 60
        nearby_rides = self._get_driver_rides_in_window(
            driver,
            ride.pickup_datetime - timedelta(minutes=buffer_minutes),
            ride.pickup_datetime + timedelta(minutes=buffer_minutes + ride.estimated_duration_minutes)
        )
        
        if nearby_rides:
            # Calculate if this ride fits well with existing schedule
            # Higher score for rides that create efficient routes
            pass
        
        return efficiency_score
```

## Implementation Phases

### Phase 1: Core Pre-Booking (Week 1-2)

1. **Database Models**
   - Create all new models
   - Add migrations
   - Create admin interfaces

2. **Basic Booking Flow**
   - Rider booking interface
   - Date/time selection with calendar
   - Location autocomplete
   - Round-trip options

3. **Fare Estimation**
   - Distance calculation
   - Time-based pricing
   - Waiting fees for round trips
   - Pre-booking premium (if any)

### Phase 2: Matching System (Week 3-4)

1. **Driver Availability Management**
   - Calendar interface for drivers
   - Working hours configuration
   - Time-off management
   - Booking capacity limits

2. **Matching Algorithm**
   - Implement scoring system
   - Create offer distribution logic
   - Handle acceptance/rejection flow
   - Automatic re-matching on rejection

3. **Driver Notification System**
   - Push notifications for new offers
   - In-app offer management
   - Expiration handling
   - Counter-offer capability

### Phase 3: Round-Trip Optimization (Week 5-6)

1. **Flexible Return Management**
   - Return time window selection
   - Driver notification system
   - Dynamic scheduling
   - Waiting fee calculation

2. **Waiting Time Optimization**
   - Nearby ride detection
   - Geofenced notifications
   - Quick acceptance flow
   - Earnings tracking

3. **Medical Appointment Features**
   - Common medical locations database
   - Typical appointment durations
   - Assistance requirements
   - Emergency contact integration

### Phase 4: Advanced Features (Week 7-8)

1. **Recurring Rides**
   - Template creation
   - Automatic scheduling
   - Preferred driver assignment
   - Modification handling

2. **Analytics Dashboard**
   - Pre-booking metrics
   - Driver utilization reports
   - Popular routes/times
   - Cancellation analysis

3. **Integration & Testing**
   - Payment system integration
   - Notification testing
   - Load testing
   - User acceptance testing

## User Interface Designs

### Rider Booking Flow

```
1. Home Screen Enhancement
   [Book Now] [Pre-Book Ride] <- New button

2. Pre-Booking Screen
   - Purpose selector (Medical/Work/Other)
   - Date picker (calendar view)
   - Time picker with common slots
   - Round-trip toggle
   
3. Location Selection
   - Saved medical locations
   - Recent destinations
   - Map-based selection
   
4. Requirements Screen
   - Accessibility needs
   - Special instructions
   - Preferred driver (if any)
   
5. Matching Screen
   - Show 3-5 driver options
   - Driver ratings & experience
   - Estimated fare
   - Vehicle details
   
6. Confirmation
   - Booking summary
   - Add to calendar option
   - SMS/Email confirmation
```

### Driver Calendar Interface

```
1. Monthly View
   - Color-coded bookings
   - Earnings preview
   - Quick stats
   
2. Daily View
   - Timeline with bookings
   - Gap identification
   - Optimization suggestions
   
3. Booking Details
   - Rider information
   - Special requirements
   - Navigation prep
   - Contact options
```

## Pricing Strategy

### Base Fare Calculation
```
Pre-booked Fare = Base Fare + Distance Rate + Time Rate + Pre-booking Fee

Where:
- Base Fare: €5 (higher than instant rides)
- Distance Rate: €1.50/km
- Time Rate: €0.30/min
- Pre-booking Fee: €2 (for guaranteed availability)
```

### Round-Trip Pricing
```
Round-Trip Fare = (Outbound Fare + Return Fare) * 0.9 (10% discount)
+ Waiting Fee (if applicable)

Waiting Fee:
- First 15 minutes: Free
- 15-60 minutes: €10/hour
- 60+ minutes: €15/hour
```

### Cancellation Policy
- Rider cancellation:
  - 24+ hours before: Free
  - 2-24 hours: €5 fee
  - <2 hours: 50% of fare
  
- Driver cancellation:
  - Automatic re-matching
  - Penalty for driver
  - Compensation for rider

## Success Metrics

### Key Performance Indicators

1. **Adoption Metrics**
   - % of rides pre-booked vs instant
   - Pre-booking growth rate
   - Repeat pre-booking users

2. **Operational Metrics**
   - Match success rate (>95%)
   - Average match time (<5 minutes)
   - Driver acceptance rate (>80%)
   - On-time arrival rate (>90%)

3. **Financial Metrics**
   - Average pre-booked fare
   - Driver utilization improvement
   - Waiting time monetization rate
   - Cancellation rate (<5%)

4. **Medical Segment Metrics**
   - Medical ride percentage
   - Round-trip completion rate
   - Partner facility satisfaction
   - Patient testimonials

## Risk Mitigation

### Potential Risks & Solutions

1. **No-show Risk**
   - Solution: Deposit system, rating impact

2. **Driver Reliability**
   - Solution: Backup driver system, penalties

3. **Demand-Supply Mismatch**
   - Solution: Dynamic pricing, driver incentives

4. **Technical Failures**
   - Solution: Manual backup, phone support

5. **Regulatory Compliance**
   - Solution: Medical transport licenses, insurance

## Technical Requirements

### Backend Infrastructure
- Django Celery for scheduled tasks
- Redis for caching and task queue
- PostGIS for geographic queries
- Push notification service (FCM/APNs)

### Frontend Updates
- Calendar component integration
- Real-time updates via WebSocket
- Offline capability for bookings
- Progressive Web App features

### Third-party Integrations
- Google Calendar API
- SMS gateway for reminders
- Payment hold/authorization
- Traffic prediction API

## Conclusion

The pre-booked rides feature represents a significant advancement for RideConnect, particularly in serving the medical transportation market. By focusing on reliability, efficiency, and accessibility, this system will create value for both riders requiring planned transportation and drivers seeking predictable income.

The phased implementation approach ensures that core functionality is delivered quickly while allowing for iterative improvements based on user feedback. The emphasis on round-trip optimization and waiting time utilization addresses the unique challenges of medical transportation while maximizing driver earnings potential.

Success will be measured not just in adoption rates but in the reliability and satisfaction metrics that are crucial for medical appointments and other time-sensitive transportation needs.