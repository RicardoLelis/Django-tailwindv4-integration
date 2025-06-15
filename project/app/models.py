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
