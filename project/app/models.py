from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from datetime import datetime, timedelta
from django.utils import timezone

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
