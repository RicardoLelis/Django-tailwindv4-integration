from django.shortcuts import redirect
from django.urls import reverse
from .models import Driver

class UserRoleMiddleware:
    """Middleware to ensure users are accessing appropriate pages based on their role"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Define role-specific URLs
        driver_urls = [
            'driver_dashboard', 'driver_landing', 'driver_initial_registration',
            'driver_verify_email', 'driver_complete_registration', 'driver_register_basic',
            'driver_register_professional', 'driver_upload_documents', 'driver_background_consent',
            'driver_register_vehicle', 'driver_vehicle_accessibility', 'driver_vehicle_safety',
            'driver_vehicle_documents', 'driver_vehicle_photos', 'driver_training',
            'driver_training_module'
        ]
        
        rider_urls = ['home', 'book_ride']
        
        # Skip middleware for non-authenticated users and admin/auth URLs
        if not request.user.is_authenticated:
            return self.get_response(request)
            
        if request.path.startswith('/admin/') or request.path.startswith('/password-reset/'):
            return self.get_response(request)
        
        # Get current URL name
        current_url_name = request.resolver_match.url_name if request.resolver_match else None
        
        if current_url_name:
            # Check if user is a driver
            try:
                driver = request.user.driver
                # Driver trying to access rider-only pages
                if current_url_name in rider_urls:
                    return redirect('driver_dashboard')
            except Driver.DoesNotExist:
                # Regular user/rider trying to access driver-only pages
                if current_url_name in driver_urls:
                    return redirect('home')
        
        return self.get_response(request)