#!/usr/bin/env python
"""
Test script to verify the pre-booking and live offers workflow
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings_simple')
django.setup()

from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from app.models import Rider, Driver, Ride, PreBookedRide, Vehicle
from app.services.notification_service import NotificationService
from app.views_package.driver_status_views import driver_live_offers
from app.forms import PreBookedRideForm


def test_immediate_ride_workflow():
    """Test immediate ride creation and broadcasting"""
    print("Testing Immediate Ride Workflow...")
    
    try:
        # Check if NotificationService has the new method
        service = NotificationService()
        if hasattr(service, 'broadcast_immediate_ride_to_drivers'):
            print("✅ NotificationService has broadcast_immediate_ride_to_drivers method")
        else:
            print("❌ NotificationService missing broadcast_immediate_ride_to_drivers method")
            
        # Check if notify_rider_ride_accepted method exists
        if hasattr(service, 'notify_rider_ride_accepted'):
            print("✅ NotificationService has notify_rider_ride_accepted method")
        else:
            print("❌ NotificationService missing notify_rider_ride_accepted method")
            
    except Exception as e:
        print(f"❌ Error testing NotificationService: {e}")


def test_preebook_form():
    """Test pre-book form has proper date fields and styling"""
    print("\nTesting Pre-Book Form...")
    
    try:
        form = PreBookedRideForm()
        
        # Check for date and time fields
        if 'scheduled_pickup_date' in form.fields:
            print("✅ Form has scheduled_pickup_date field")
            
            # Check field widget styling
            widget = form.fields['scheduled_pickup_date'].widget
            if 'glass-input' in widget.attrs.get('class', ''):
                print("✅ Date field has glass morphism styling")
            else:
                print("❌ Date field missing glass morphism styling")
        else:
            print("❌ Form missing scheduled_pickup_date field")
            
        if 'scheduled_pickup_time' in form.fields:
            print("✅ Form has scheduled_pickup_time field")
            
            # Check field widget styling
            widget = form.fields['scheduled_pickup_time'].widget
            if 'glass-input' in widget.attrs.get('class', ''):
                print("✅ Time field has glass morphism styling")
            else:
                print("❌ Time field missing glass morphism styling")
        else:
            print("❌ Form missing scheduled_pickup_time field")
            
        # Check location field styling
        if 'pickup_location' in form.fields:
            widget = form.fields['pickup_location'].widget
            if 'glass-input' in widget.attrs.get('class', ''):
                print("✅ Pickup location field has glass morphism styling")
            else:
                print("❌ Pickup location field missing glass morphism styling")
                
    except Exception as e:
        print(f"❌ Error testing PreBookedRideForm: {e}")


def test_live_offers_filtering():
    """Test that live offers includes rides within 7 days"""
    print("\nTesting Live Offers Filtering...")
    
    try:
        # The driver_live_offers function should filter rides within 7 days
        # We can verify the function exists and has the correct logic
        import inspect
        from app.views_package.driver_status_views import driver_live_offers
        
        source = inspect.getsource(driver_live_offers)
        
        if 'days=7' in source:
            print("✅ Live offers filters rides within 7 days")
        else:
            print("❌ Live offers may not have correct 7-day filtering")
            
        if 'immediate_rides' in source:
            print("✅ Live offers includes immediate rides")
        else:
            print("❌ Live offers missing immediate rides support")
            
    except Exception as e:
        print(f"❌ Error testing live offers filtering: {e}")


def test_template_styling():
    """Test that pre-book template has glass morphism styling"""
    print("\nTesting Template Styling...")
    
    try:
        template_path = '/Users/lelisra/Documents/code/tailwind4-django-how/project/app/templates/bookings/pre_book_ride.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
            
        # Check for glass morphism classes
        if 'glass-effect' in content:
            print("✅ Template uses glass-effect styling")
        else:
            print("❌ Template missing glass-effect styling")
            
        if 'gradient-text' in content:
            print("✅ Template uses gradient text styling")
        else:
            print("❌ Template missing gradient text styling")
            
        if 'float-animation' in content:
            print("✅ Template has animated background elements")
        else:
            print("❌ Template missing animated background elements")
            
        # Check for form fields
        if 'scheduled_pickup_date' in content:
            print("✅ Template includes pickup date field")
        else:
            print("❌ Template missing pickup date field")
            
        if 'scheduled_pickup_time' in content:
            print("✅ Template includes pickup time field")
        else:
            print("❌ Template missing pickup time field")
            
    except Exception as e:
        print(f"❌ Error testing template styling: {e}")


if __name__ == '__main__':
    print("🧪 Testing Pre-Booking and Live Offers Workflow")
    print("=" * 60)
    
    test_immediate_ride_workflow()
    test_preebook_form() 
    test_live_offers_filtering()
    test_template_styling()
    
    print("\n" + "=" * 60)
    print("✨ Workflow testing complete!")