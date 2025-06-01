from django.db import models
from django.contrib.auth.models import User

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
