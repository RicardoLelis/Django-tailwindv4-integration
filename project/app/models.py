from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta
from django.utils import timezone
import uuid
import os

class Rider(models.Model):
    DISABILITY_CHOICES = [
        ('wheelchair', 'Wheelchair User'),
        ('blind', 'Blind/Visually Impaired'),
        ('deaf', 'Deaf/Hard of Hearing'),
        ('mobility', 'Mobility Impairment'),
        ('cognitive', 'Cognitive Disability'),
        ('service_animal', 'Service Animal User'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    disabilities = models.JSONField(default=list, blank=True)
    other_disability = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Rider: {self.user.username}"

class Ride(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name='rides')
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    pickup_datetime = models.DateTimeField(validators=[MinValueValidator(timezone.now)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    special_requirements = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-pickup_datetime']
    
    def __str__(self):
        return f"Ride from {self.pickup_location} to {self.dropoff_location} on {self.pickup_datetime}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.pickup_datetime:
            # Ensure pickup is not more than 7 days in the future
            max_future_date = timezone.now() + timedelta(days=7)
            if self.pickup_datetime > max_future_date:
                raise ValidationError("Pickup date cannot be more than 7 days in the future.")


def driver_document_upload_path(instance, filename):
    """Generate upload path for driver documents"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('driver_documents', str(instance.driver.user.id), filename)


def vehicle_photo_upload_path(instance, filename):
    """Generate upload path for vehicle photos"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('vehicle_photos', str(instance.driver.user.id), filename)


class Driver(models.Model):
    STATUS_CHOICES = [
        ('started', 'Application Started'),
        ('email_verified', 'Email Verified'),
        ('documents_uploaded', 'Documents Uploaded'),
        ('background_check_pending', 'Background Check Pending'),
        ('training_in_progress', 'Training In Progress'),
        ('assessment_scheduled', 'Assessment Scheduled'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]
    
    EXPERIENCE_CHOICES = [
        ('none', 'No Experience'),
        ('some', 'Some Experience'),
        ('experienced', 'Very Experienced'),
    ]
    
    FLEET_SIZE_CHOICES = [
        ('1', '1 vehicle'),
        ('2-5', '2-5 vehicles'),
        ('6-10', '6-10 vehicles'),
        ('11-20', '11-20 vehicles'),
        ('20+', 'More than 20 vehicles'),
    ]
    
    BACKGROUND_CHECK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20)
    fleet_size = models.CharField(max_length=10, choices=FLEET_SIZE_CHOICES, default='1')
    
    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True)
    email_verification_sent = models.DateTimeField(null=True, blank=True)
    registration_token = models.CharField(max_length=100, blank=True)
    registration_token_created = models.DateTimeField(null=True, blank=True)
    license_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    license_expiry = models.DateField(null=True, blank=True)
    
    # Application status
    application_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='started')
    
    # Background check
    background_check_status = models.CharField(max_length=20, choices=BACKGROUND_CHECK_STATUS_CHOICES, default='pending')
    background_check_date = models.DateField(null=True, blank=True)
    background_check_consent = models.BooleanField(default=False)
    
    # Professional info
    years_driving = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(50)])
    previous_platforms = models.JSONField(default=list, blank=True)
    disability_experience = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default='none')
    languages = models.JSONField(default=list, blank=True)
    
    # Availability
    working_hours = models.JSONField(default=list, blank=True)
    working_days = models.JSONField(default=list, blank=True)
    expected_trips_per_week = models.IntegerField(default=20, validators=[MinValueValidator(1), MaxValueValidator(100)])
    
    # Driver status
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_rides = models.IntegerField(default=0)
    is_active = models.BooleanField(default=False)
    is_available = models.BooleanField(default=False)
    current_location = models.JSONField(null=True, blank=True)
    
    # Training
    accessibility_training = models.JSONField(default=list, blank=True)
    training_completed = models.BooleanField(default=False)
    assessment_passed = models.BooleanField(default=False)
    
    # Eligibility checks
    has_portuguese_license = models.BooleanField(default=False)
    has_accessible_vehicle = models.BooleanField(default=False)
    authorized_to_work = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Driver: {self.user.get_full_name() or self.user.username}"
    
    @property
    def can_drive(self):
        return (self.application_status == 'approved' and 
                self.is_active and 
                self.training_completed and 
                self.assessment_passed)


class DriverDocument(models.Model):
    DOCUMENT_TYPES = [
        ('driving_license_front', 'Driving License Front'),
        ('driving_license_back', 'Driving License Back'),
        ('citizen_card', 'Citizen Card'),
        ('passport', 'Passport'),
        ('proof_of_address', 'Proof of Address'),
    ]
    
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to=driver_document_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['driver', 'document_type']
    
    def __str__(self):
        return f"{self.driver.user.username} - {self.get_document_type_display()}"


class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('sedan_accessible', 'Accessible Sedan'),
        ('van_ramp', 'Van with Ramp'),
        ('van_lift', 'Van with Lift'),
        ('suv_accessible', 'Accessible SUV'),
        ('other', 'Other'),
    ]
    
    COLORS = [
        ('white', 'White'),
        ('black', 'Black'),
        ('silver', 'Silver'),
        ('gray', 'Gray'),
        ('blue', 'Blue'),
        ('red', 'Red'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('other', 'Other'),
    ]
    
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='vehicles')
    license_plate = models.CharField(max_length=20, unique=True)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField(validators=[MinValueValidator(1990), MaxValueValidator(2030)])
    color = models.CharField(max_length=20, choices=COLORS)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    
    # Accessibility features
    wheelchair_capacity = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])
    has_ramp = models.BooleanField(default=False)
    has_lift = models.BooleanField(default=False)
    has_lowered_floor = models.BooleanField(default=False)
    has_swivel_seats = models.BooleanField(default=False)
    has_hand_controls = models.BooleanField(default=False)
    door_width_cm = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(50), MaxValueValidator(200)])
    
    # Additional features
    extra_features = models.JSONField(default=list, blank=True)
    
    # Documentation dates
    insurance_expiry = models.DateField()
    inspection_expiry = models.DateField()
    
    # Safety equipment
    safety_equipment = models.JSONField(default=list, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    verification_status = models.CharField(max_length=20, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.make} {self.model} ({self.license_plate})"
    
    @property
    def is_accessible(self):
        return (self.has_ramp or self.has_lift or 
                self.has_lowered_floor or self.has_swivel_seats)


class VehicleDocument(models.Model):
    DOCUMENT_TYPES = [
        ('registration', 'Vehicle Registration (DUA)'),
        ('insurance', 'Insurance Certificate'),
        ('inspection', 'Inspection Certificate (IPO)'),
        ('accessibility_cert', 'Accessibility Certification'),
    ]
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to=driver_document_upload_path)
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['vehicle', 'document_type']
    
    def __str__(self):
        return f"{self.vehicle} - {self.get_document_type_display()}"


class VehiclePhoto(models.Model):
    PHOTO_TYPES = [
        ('exterior_front', 'Exterior Front'),
        ('exterior_back', 'Exterior Back'),
        ('exterior_left', 'Exterior Left'),
        ('exterior_right', 'Exterior Right'),
        ('interior_dashboard', 'Interior Dashboard'),
        ('interior_seats', 'Interior Seats'),
        ('accessibility_ramp', 'Ramp/Lift'),
        ('wheelchair_area', 'Wheelchair Area'),
        ('securing_points', 'Wheelchair Securing Points'),
    ]
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='photos')
    photo_type = models.CharField(max_length=30, choices=PHOTO_TYPES)
    image = models.ImageField(upload_to=vehicle_photo_upload_path)
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.vehicle} - {self.get_photo_type_display()}"


class TrainingModule(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration_minutes = models.IntegerField()
    is_mandatory = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    content_url = models.URLField(blank=True)
    quiz_questions = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.title


class DriverTraining(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='training_progress')
    module = models.ForeignKey(TrainingModule, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    quiz_score = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    attempts = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['driver', 'module']
    
    def __str__(self):
        return f"{self.driver} - {self.module.title}"
    
    @property
    def is_completed(self):
        return self.completed_at is not None and self.quiz_score >= 80


class DriverRide(models.Model):
    """Extended ride model for driver-specific data and analytics"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('mbway', 'MB Way'),
        ('voucher', 'Voucher'),
    ]
    
    CANCELLATION_REASONS = [
        ('rider_no_show', 'Rider No Show'),
        ('rider_cancelled', 'Rider Cancelled'),
        ('driver_cancelled', 'Driver Cancelled'),
        ('vehicle_issue', 'Vehicle Issue'),
        ('weather', 'Weather Conditions'),
        ('other', 'Other'),
    ]
    
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name='driver_ride')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='driver_rides')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='rides')
    
    # Timing data
    accepted_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Distance and route data
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    route_polyline = models.TextField(blank=True)  # Encoded polyline for route visualization
    
    # Financial data
    base_fare = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    distance_fare = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    time_fare = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    accessibility_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_fare = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    driver_earnings = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    
    # Ratings and feedback
    driver_rating = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    rider_rating = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    driver_comment = models.TextField(blank=True)
    rider_comment = models.TextField(blank=True)
    
    # Cancellation data
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=20, choices=CANCELLATION_REASONS, blank=True)
    cancellation_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Accessibility data
    wheelchair_used = models.BooleanField(default=False)
    assistance_provided = models.JSONField(default=list, blank=True)  # List of assistance types
    equipment_used = models.JSONField(default=list, blank=True)  # List of equipment used
    
    # Performance metrics
    pickup_delay_minutes = models.IntegerField(default=0)  # Negative means early
    route_efficiency = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Percentage
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['driver', '-created_at']),
            models.Index(fields=['vehicle', '-created_at']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['completed_at']),
        ]
    
    def __str__(self):
        return f"DriverRide {self.id} - {self.driver.user.username}"
    
    @property
    def response_time_seconds(self):
        if self.accepted_at and self.ride.created_at:
            return (self.accepted_at - self.ride.created_at).total_seconds()
        return None
    
    @property
    def total_duration_minutes(self):
        if self.completed_at and self.accepted_at:
            return int((self.completed_at - self.accepted_at).total_seconds() / 60)
        return None


class RideAnalytics(models.Model):
    """Aggregated analytics for rides - updated periodically"""
    driver_ride = models.OneToOneField(DriverRide, on_delete=models.CASCADE, related_name='analytics')
    
    # Location analytics
    pickup_zone = models.CharField(max_length=50, blank=True)  # City zone/district
    dropoff_zone = models.CharField(max_length=50, blank=True)
    pickup_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    pickup_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    dropoff_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    dropoff_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Time analytics
    day_of_week = models.IntegerField()  # 0=Monday, 6=Sunday
    hour_of_day = models.IntegerField()  # 0-23
    is_peak_hour = models.BooleanField(default=False)
    is_weekend = models.BooleanField(default=False)
    is_holiday = models.BooleanField(default=False)
    
    # Weather data (to be populated from external API)
    weather_condition = models.CharField(max_length=50, blank=True)
    temperature_celsius = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    
    # Efficiency metrics
    idle_time_minutes = models.IntegerField(default=0)  # Time between rides
    fuel_efficiency_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Revenue metrics
    revenue_per_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    revenue_per_minute = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['day_of_week', 'hour_of_day']),
            models.Index(fields=['pickup_zone']),
            models.Index(fields=['is_peak_hour']),
        ]


class DriverPerformance(models.Model):
    """Daily/Weekly/Monthly driver performance metrics"""
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='performance_metrics')
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Activity metrics
    total_rides = models.IntegerField(default=0)
    total_hours_online = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_distance_km = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    acceptance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    cancellation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    
    # Financial metrics
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_fare = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_tips = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fuel_costs = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Quality metrics
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_5_star_rides = models.IntegerField(default=0)
    total_complaints = models.IntegerField(default=0)
    on_time_arrival_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    
    # Accessibility metrics
    total_wheelchair_rides = models.IntegerField(default=0)
    accessibility_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    assistance_provided_count = models.IntegerField(default=0)
    
    # Efficiency metrics
    average_pickup_time = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Minutes
    utilization_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    peak_hours_coverage = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['driver', 'period_type', 'period_start']
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['driver', 'period_type', '-period_start']),
        ]
    
    def __str__(self):
        return f"{self.driver.user.username} - {self.period_type} - {self.period_start}"


class DriverSession(models.Model):
    """Track driver online/offline sessions for analytics"""
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='sessions')
    
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # Location tracking
    start_location = models.JSONField(null=True, blank=True)  # {lat, lng, address}
    end_location = models.JSONField(null=True, blank=True)
    
    # Session metrics
    total_rides = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_distance_km = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Break tracking
    break_time_minutes = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['driver', '-started_at']),
        ]
    
    @property
    def duration_hours(self):
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds() / 3600
        return None
    
    @property
    def active_time_hours(self):
        if self.duration_hours:
            return self.duration_hours - (self.break_time_minutes / 60)
        return None


class PreBookedRide(models.Model):
    """
    Model for rides scheduled in advance (beyond immediate booking window).
    Supports both one-time and recurring pre-booked rides.
    """
    BOOKING_STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('driver_assigned', 'Driver Assigned'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Core booking information
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name='pre_booked_rides')
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    dropoff_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    dropoff_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Scheduling information
    scheduled_pickup_time = models.DateTimeField(db_index=True)
    estimated_duration_minutes = models.IntegerField(validators=[MinValueValidator(5), MaxValueValidator(300)])
    
    # Booking window and flexibility
    pickup_window_minutes = models.IntegerField(
        default=15,
        validators=[MinValueValidator(5), MaxValueValidator(60)],
        help_text="Acceptable pickup time window in minutes"
    )
    is_flexible = models.BooleanField(
        default=False,
        help_text="Whether rider is flexible with pickup time for optimization"
    )
    
    # Status and assignment
    status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='pending', db_index=True)
    assigned_driver = models.ForeignKey(
        Driver, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='pre_booked_assignments'
    )
    assigned_vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pre_booked_rides'
    )
    assignment_confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Special requirements and notes
    special_requirements = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True, help_text="Internal notes not visible to rider")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Accessibility requirements
    wheelchair_required = models.BooleanField(default=False)
    assistance_required = models.JSONField(default=list, blank=True)
    
    # Round trip configuration
    booking_type = models.CharField(max_length=20, choices=[('one_way', 'One Way'), ('round_trip', 'Round Trip')], default='one_way')
    waiting_duration_minutes = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(15), MaxValueValidator(240)])
    
    # Recurring ride reference
    recurring_template = models.ForeignKey(
        'RecurringRideTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_rides'
    )
    
    # Pricing information
    estimated_fare = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    surge_multiplier = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=1.0,
        validators=[MinValueValidator(0.5), MaxValueValidator(5.0)]
    )
    
    # Notification tracking
    rider_notified_at = models.DateTimeField(null=True, blank=True)
    driver_notified_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Cancellation information
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_pre_bookings')
    cancellation_reason = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['scheduled_pickup_time']
        indexes = [
            models.Index(fields=['rider', 'scheduled_pickup_time']),
            models.Index(fields=['assigned_driver', 'scheduled_pickup_time']),
            models.Index(fields=['status', 'scheduled_pickup_time']),
            models.Index(fields=['scheduled_pickup_time', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(scheduled_pickup_time__gte=timezone.now() + timedelta(hours=2)),
                name='pre_booking_min_advance_time'
            )
        ]
    
    def __str__(self):
        return f"Pre-booked ride for {self.rider.user.username} on {self.scheduled_pickup_time}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Ensure scheduled pickup is at least 2 hours in advance
        if self.scheduled_pickup_time:
            min_booking_time = timezone.now() + timedelta(hours=2)
            if self.scheduled_pickup_time < min_booking_time:
                raise ValidationError("Pre-booked rides must be scheduled at least 2 hours in advance.")
        
        # Ensure pickup window is reasonable
        if self.pickup_window_minutes < 5 or self.pickup_window_minutes > 60:
            raise ValidationError("Pickup window must be between 5 and 60 minutes.")
    
    @property
    def pickup_window_start(self):
        """Calculate the start of the acceptable pickup window"""
        return self.scheduled_pickup_time - timedelta(minutes=self.pickup_window_minutes // 2)
    
    @property
    def pickup_window_end(self):
        """Calculate the end of the acceptable pickup window"""
        return self.scheduled_pickup_time + timedelta(minutes=self.pickup_window_minutes // 2)
    
    @property
    def is_within_assignment_window(self):
        """Check if ride is within the 24-hour driver assignment window"""
        return self.scheduled_pickup_time <= timezone.now() + timedelta(hours=24)
    
    @property
    def can_be_cancelled(self):
        """Check if ride can still be cancelled (2 hours before pickup)"""
        return timezone.now() < self.scheduled_pickup_time - timedelta(hours=2)
    
    def assign_driver(self, driver, vehicle=None):
        """Assign a driver to this pre-booked ride"""
        from .services.calendar_service import CalendarService
        
        self.assigned_driver = driver
        self.assigned_vehicle = vehicle or driver.vehicles.filter(is_active=True).first()
        self.assignment_confirmed_at = timezone.now()
        self.status = 'driver_assigned'
        self.save()
        
        # Add to driver's calendar
        calendar_service = CalendarService()
        calendar_service.add_booking_to_calendar(self, driver)
    
    def cancel(self, user, reason=''):
        """Cancel this pre-booked ride"""
        if not self.can_be_cancelled:
            raise ValueError("Cannot cancel ride less than 2 hours before pickup")
        
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = user
        self.cancellation_reason = reason
        self.save()
    
    def create_regular_ride(self):
        """Convert pre-booked ride to regular ride when pickup time approaches"""
        if self.status != 'driver_assigned':
            raise ValueError("Cannot create regular ride without assigned driver")
        
        ride = Ride.objects.create(
            rider=self.rider,
            pickup_location=self.pickup_location,
            dropoff_location=self.dropoff_location,
            pickup_datetime=self.scheduled_pickup_time,
            special_requirements=self.special_requirements,
            status='confirmed'
        )
        
        # Create driver ride assignment
        DriverRide.objects.create(
            ride=ride,
            driver=self.assigned_driver,
            vehicle=self.assigned_vehicle,
            accepted_at=timezone.now()
        )
        
        self.status = 'completed'
        self.save()
        
        return ride


class DriverCalendar(models.Model):
    """
    Manages driver availability and commitments for pre-booked rides.
    Helps optimize driver assignments and prevent conflicts.
    """
    AVAILABILITY_STATUS_CHOICES = [
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('break', 'On Break'),
        ('offline', 'Offline'),
    ]
    
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='calendar_entries')
    date = models.DateField(db_index=True)
    
    # Availability windows
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=AVAILABILITY_STATUS_CHOICES, default='available')
    is_available = models.BooleanField(default=True)
    
    # Capacity management
    max_rides = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="Maximum number of pre-booked rides for this time slot"
    )
    current_bookings = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Location preferences
    preferred_zones = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of preferred pickup zones"
    )
    avoided_zones = models.JSONField(
        default=list,
        blank=True,
        help_text="List of zones to avoid"
    )
    
    # Break management
    break_start = models.TimeField(null=True, blank=True)
    break_duration_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(15), MaxValueValidator(120)]
    )
    
    # Notes and preferences
    notes = models.TextField(blank=True)
    accepts_wheelchair = models.BooleanField(default=True)
    accepts_long_distance = models.BooleanField(default=True)
    
    # Metrics
    total_estimated_earnings = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    utilization_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    break_slots = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ['driver', 'date', 'start_time', 'end_time']
        indexes = [
            models.Index(fields=['driver', 'date']),
            models.Index(fields=['date', 'status']),
            models.Index(fields=['date', 'current_bookings']),
        ]
    
    def __str__(self):
        return f"{self.driver.user.username} - {self.date} {self.start_time}-{self.end_time}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Ensure end time is after start time
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")
        
        # Ensure break is within working hours
        if self.break_start:
            if self.break_start < self.start_time or self.break_start > self.end_time:
                raise ValidationError("Break must be within working hours.")
    
    @property
    def available_slots(self):
        """Calculate remaining available slots"""
        return max(0, self.max_rides - self.current_bookings)
    
    @property
    def is_fully_booked(self):
        """Check if this calendar entry is fully booked"""
        return self.current_bookings >= self.max_rides
    
    @property
    def utilization_percentage(self):
        """Calculate utilization percentage"""
        if self.max_rides == 0:
            return 0
        return (self.current_bookings / self.max_rides) * 100
    
    def can_accept_ride(self, pickup_time, pickup_location=None):
        """Check if driver can accept a ride at given time and location"""
        if self.status != 'available' or self.is_fully_booked:
            return False
        
        # Check if pickup time is within working hours
        pickup_time_only = pickup_time.time()
        if pickup_time_only < self.start_time or pickup_time_only > self.end_time:
            return False
        
        # Check if pickup time conflicts with break
        if self.break_start and self.break_duration_minutes:
            break_end = (datetime.combine(datetime.today(), self.break_start) + 
                        timedelta(minutes=self.break_duration_minutes)).time()
            if self.break_start <= pickup_time_only <= break_end:
                return False
        
        # Check zone preferences if location provided
        if pickup_location and self.avoided_zones:
            # This would need geocoding logic to determine zone
            pass
        
        return True
    
    def book_slot(self):
        """Book a slot in this calendar entry"""
        if self.is_fully_booked:
            raise ValueError("Calendar entry is fully booked")
        
        self.current_bookings += 1
        self.save()
    
    def release_slot(self):
        """Release a slot in this calendar entry"""
        if self.current_bookings > 0:
            self.current_bookings -= 1
            self.save()


class RideMatchOffer(models.Model):
    """
    Represents an offer to match a driver with a pre-booked ride.
    Tracks driver responses and helps optimize assignments.
    """
    OFFER_STATUS_CHOICES = [
        ('pending', 'Pending Response'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    DECLINE_REASON_CHOICES = [
        ('distance', 'Too Far'),
        ('timing', 'Bad Timing'),
        ('vehicle', 'Vehicle Unavailable'),
        ('personal', 'Personal Reason'),
        ('other', 'Other'),
    ]
    
    pre_booked_ride = models.ForeignKey(
        PreBookedRide,
        on_delete=models.CASCADE,
        related_name='match_offers'
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='ride_offers')
    
    # Offer details
    status = models.CharField(max_length=20, choices=OFFER_STATUS_CHOICES, default='pending', db_index=True)
    offered_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Financial incentives
    base_fare = models.DecimalField(max_digits=8, decimal_places=2)
    bonus_amount = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Additional bonus for accepting this ride"
    )
    total_earnings = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Match quality metrics
    distance_to_pickup_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)
    compatibility_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score indicating how well this match fits driver preferences"
    )
    
    # Response tracking
    decline_reason = models.CharField(max_length=20, choices=DECLINE_REASON_CHOICES, blank=True)
    decline_notes = models.TextField(blank=True)
    
    # Notification tracking
    push_notification_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    
    # Priority and ordering
    priority_rank = models.IntegerField(
        default=0,
        help_text="Lower number = higher priority"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['priority_rank', '-offered_at']
        unique_together = ['pre_booked_ride', 'driver']
        indexes = [
            models.Index(fields=['driver', 'status', '-offered_at']),
            models.Index(fields=['pre_booked_ride', 'status']),
            models.Index(fields=['expires_at', 'status']),
        ]
    
    def __str__(self):
        return f"Offer for {self.driver.user.username} - Ride {self.pre_booked_ride.id}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Ensure expiry is after offer time
        if self.expires_at and self.offered_at and self.expires_at <= self.offered_at:
            raise ValidationError("Expiry time must be after offer time.")
    
    @property
    def is_expired(self):
        """Check if offer has expired"""
        return timezone.now() > self.expires_at
    
    @property
    def time_to_respond(self):
        """Calculate remaining time to respond"""
        if self.status != 'pending':
            return None
        remaining = self.expires_at - timezone.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    @property
    def response_time_seconds(self):
        """Calculate how long driver took to respond"""
        if self.responded_at and self.offered_at:
            return (self.responded_at - self.offered_at).total_seconds()
        return None
    
    def accept(self):
        """Accept the ride offer"""
        if self.status != 'pending':
            raise ValueError("Can only accept pending offers")
        
        if self.is_expired:
            raise ValueError("Cannot accept expired offer")
        
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save()
        
        # Assign driver to the pre-booked ride
        self.pre_booked_ride.assign_driver(self.driver)
        
        # Decline all other pending offers for this ride
        RideMatchOffer.objects.filter(
            pre_booked_ride=self.pre_booked_ride,
            status='pending'
        ).exclude(id=self.id).update(
            status='withdrawn',
            updated_at=timezone.now()
        )
    
    def decline(self, reason='', notes=''):
        """Decline the ride offer"""
        if self.status != 'pending':
            raise ValueError("Can only decline pending offers")
        
        self.status = 'declined'
        self.responded_at = timezone.now()
        self.decline_reason = reason
        self.decline_notes = notes
        self.save()
    
    def calculate_compatibility_score(self):
        """Calculate compatibility score based on various factors"""
        score = 100.0
        
        # Distance factor (closer is better)
        if self.distance_to_pickup_km:
            if self.distance_to_pickup_km > 10:
                score -= 20
            elif self.distance_to_pickup_km > 5:
                score -= 10
        
        # Time factor (driver availability)
        # This would need more complex logic based on driver calendar
        
        # Driver rating factor
        if self.driver.rating < 4.5:
            score -= 10
        
        # Special requirements matching
        # This would need logic to match ride requirements with driver capabilities
        
        self.compatibility_score = max(0, min(100, score))
        return self.compatibility_score


class WaitingTimeOptimization(models.Model):
    """
    Tracks and optimizes waiting times between consecutive pre-booked rides.
    Helps in efficient route planning and driver utilization.
    """
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='waiting_optimizations')
    date = models.DateField(db_index=True)
    
    # Ride sequence
    first_ride = models.ForeignKey(
        PreBookedRide,
        on_delete=models.CASCADE,
        related_name='as_first_ride'
    )
    second_ride = models.ForeignKey(
        PreBookedRide,
        on_delete=models.CASCADE,
        related_name='as_second_ride'
    )
    
    # Time calculations
    first_ride_end_time = models.DateTimeField()
    second_ride_start_time = models.DateTimeField()
    buffer_time_minutes = models.IntegerField(validators=[MinValueValidator(0)])
    travel_time_minutes = models.IntegerField(validators=[MinValueValidator(0)])
    waiting_time_minutes = models.IntegerField(validators=[MinValueValidator(0)])
    
    # Distance and route
    distance_between_km = models.DecimalField(max_digits=6, decimal_places=2)
    route_polyline = models.TextField(blank=True)
    
    # Optimization metrics
    efficiency_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    fuel_cost_estimate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Suggestions
    suggested_departure_time = models.DateTimeField(null=True, blank=True)
    suggested_route = models.TextField(blank=True)
    optimization_notes = models.TextField(blank=True)
    
    # Status
    is_optimal = models.BooleanField(default=False)
    needs_reoptimization = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'first_ride_end_time']
        unique_together = ['driver', 'first_ride', 'second_ride']
        indexes = [
            models.Index(fields=['driver', 'date']),
            models.Index(fields=['waiting_time_minutes']),
            models.Index(fields=['efficiency_score']),
        ]
    
    def __str__(self):
        return f"Optimization for {self.driver.user.username} on {self.date}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Ensure rides are in correct order
        if self.first_ride_end_time >= self.second_ride_start_time:
            raise ValidationError("First ride must end before second ride starts.")
        
        # Ensure both rides are assigned to the same driver
        if (self.first_ride.assigned_driver != self.driver or 
            self.second_ride.assigned_driver != self.driver):
            raise ValidationError("Both rides must be assigned to the specified driver.")
    
    @property
    def total_gap_minutes(self):
        """Calculate total time gap between rides"""
        gap = self.second_ride_start_time - self.first_ride_end_time
        return int(gap.total_seconds() / 60)
    
    @property
    def is_efficient(self):
        """Check if the waiting time is within acceptable limits"""
        # Less than 30 minutes waiting is considered efficient
        return self.waiting_time_minutes < 30
    
    def calculate_efficiency_score(self):
        """Calculate efficiency score based on various factors"""
        score = 100.0
        
        # Waiting time penalty
        if self.waiting_time_minutes > 60:
            score -= 40
        elif self.waiting_time_minutes > 30:
            score -= 20
        elif self.waiting_time_minutes > 15:
            score -= 10
        
        # Distance penalty
        if self.distance_between_km > 20:
            score -= 30
        elif self.distance_between_km > 10:
            score -= 15
        
        # Buffer time bonus
        if self.buffer_time_minutes >= 10:
            score += 10
        
        self.efficiency_score = max(0, min(100, score))
        return self.efficiency_score
    
    def suggest_optimization(self):
        """Generate optimization suggestions"""
        suggestions = []
        
        if self.waiting_time_minutes > 30:
            suggestions.append("Consider finding intermediate rides to fill the gap")
        
        if self.distance_between_km > 15:
            suggestions.append("Long distance between rides - consider zone-based assignment")
        
        if self.buffer_time_minutes < 10:
            suggestions.append("Low buffer time - risk of delays affecting second ride")
        
        self.optimization_notes = "\n".join(suggestions)
        self.needs_reoptimization = len(suggestions) > 0
        return suggestions


class RecurringRideTemplate(models.Model):
    """
    Template for recurring pre-booked rides (e.g., daily commute, weekly appointments).
    Automatically generates individual pre-booked rides based on the recurrence pattern.
    """
    RECURRENCE_PATTERN_CHOICES = [
        ('daily', 'Daily'),
        ('weekdays', 'Weekdays Only'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom Pattern'),
    ]
    
    DAY_OF_WEEK_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    # Rider information
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name='recurring_templates')
    template_name = models.CharField(max_length=100, help_text="e.g., 'Daily work commute'")
    
    # Route information
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    dropoff_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    dropoff_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Timing information
    pickup_time = models.TimeField()
    estimated_duration_minutes = models.IntegerField(validators=[MinValueValidator(5), MaxValueValidator(300)])
    pickup_window_minutes = models.IntegerField(
        default=15,
        validators=[MinValueValidator(5), MaxValueValidator(60)]
    )
    
    # Recurrence pattern
    recurrence_pattern = models.CharField(max_length=20, choices=RECURRENCE_PATTERN_CHOICES)
    custom_days = models.JSONField(
        default=list,
        blank=True,
        help_text="List of day numbers (0-6) for custom pattern"
    )
    
    # Validity period
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Preferences
    preferred_driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_recurring_rides'
    )
    special_requirements = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PreBookedRide.PRIORITY_CHOICES, default='normal')
    
    # Generation tracking
    last_generated_date = models.DateField(null=True, blank=True)
    generation_horizon_days = models.IntegerField(
        default=30,
        validators=[MinValueValidator(7), MaxValueValidator(90)],
        help_text="How many days ahead to generate rides"
    )
    
    # Exclusions
    excluded_dates = models.JSONField(
        default=list,
        blank=True,
        help_text="List of dates to skip (holidays, vacations, etc.)"
    )
    
    # Statistics
    total_rides_generated = models.IntegerField(default=0)
    total_rides_completed = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rider', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['last_generated_date']),
        ]
    
    def __str__(self):
        return f"{self.template_name} - {self.rider.user.username}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Ensure end date is after start date
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date.")
        
        # Validate custom days
        if self.recurrence_pattern == 'custom' and not self.custom_days:
            raise ValidationError("Custom pattern requires specifying days.")
        
        if self.custom_days:
            for day in self.custom_days:
                if not isinstance(day, int) or day < 0 or day > 6:
                    raise ValidationError("Custom days must be integers between 0 and 6.")
    
    @property
    def is_valid(self):
        """Check if template is currently valid"""
        today = timezone.now().date()
        if not self.is_active:
            return False
        if self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True
    
    def get_occurrence_dates(self, start_date, end_date):
        """Generate list of dates when rides should occur"""
        dates = []
        current_date = max(start_date, self.start_date)
        end_date = min(end_date, self.end_date) if self.end_date else end_date
        
        while current_date <= end_date:
            should_include = False
            
            if self.recurrence_pattern == 'daily':
                should_include = True
            elif self.recurrence_pattern == 'weekdays':
                should_include = current_date.weekday() < 5
            elif self.recurrence_pattern == 'weekly':
                should_include = current_date.weekday() == self.start_date.weekday()
            elif self.recurrence_pattern == 'biweekly':
                weeks_diff = (current_date - self.start_date).days // 7
                should_include = weeks_diff % 2 == 0 and current_date.weekday() == self.start_date.weekday()
            elif self.recurrence_pattern == 'monthly':
                should_include = current_date.day == self.start_date.day
            elif self.recurrence_pattern == 'custom':
                should_include = current_date.weekday() in self.custom_days
            
            # Check exclusions
            if should_include and str(current_date) not in self.excluded_dates:
                dates.append(current_date)
            
            current_date += timedelta(days=1)
        
        return dates
    
    def generate_rides(self, days_ahead=None):
        """Generate pre-booked rides based on the template"""
        if not self.is_valid:
            return []
        
        days_ahead = days_ahead or self.generation_horizon_days
        start_date = timezone.now().date()
        if self.last_generated_date:
            start_date = max(start_date, self.last_generated_date + timedelta(days=1))
        
        end_date = start_date + timedelta(days=days_ahead)
        occurrence_dates = self.get_occurrence_dates(start_date, end_date)
        
        created_rides = []
        for date in occurrence_dates:
            pickup_datetime = timezone.make_aware(
                datetime.combine(date, self.pickup_time)
            )
            
            # Skip if too close to current time
            if pickup_datetime < timezone.now() + timedelta(hours=2):
                continue
            
            # Check if ride already exists
            existing = PreBookedRide.objects.filter(
                rider=self.rider,
                recurring_template=self,
                scheduled_pickup_time=pickup_datetime
            ).exists()
            
            if not existing:
                ride = PreBookedRide.objects.create(
                    rider=self.rider,
                    pickup_location=self.pickup_location,
                    dropoff_location=self.dropoff_location,
                    pickup_latitude=self.pickup_latitude,
                    pickup_longitude=self.pickup_longitude,
                    dropoff_latitude=self.dropoff_latitude,
                    dropoff_longitude=self.dropoff_longitude,
                    scheduled_pickup_time=pickup_datetime,
                    estimated_duration_minutes=self.estimated_duration_minutes,
                    pickup_window_minutes=self.pickup_window_minutes,
                    special_requirements=self.special_requirements,
                    priority=self.priority,
                    recurring_template=self
                )
                created_rides.append(ride)
        
        if created_rides:
            self.last_generated_date = end_date
            self.total_rides_generated += len(created_rides)
            self.save()
        
        return created_rides
    
    def pause(self):
        """Pause the recurring template"""
        self.is_active = False
        self.save()
        
        # Cancel future rides
        PreBookedRide.objects.filter(
            recurring_template=self,
            status='pending',
            scheduled_pickup_time__gt=timezone.now()
        ).update(
            status='cancelled',
            cancellation_reason='Recurring template paused'
        )
    
    def resume(self):
        """Resume the recurring template"""
        self.is_active = True
        self.save()
        
        # Generate rides for the next period
        self.generate_rides()
