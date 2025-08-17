#!/usr/bin/env python
"""
Test script to verify booking integration works correctly
"""

import os
import sys
import django

# Setup Django environment  
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings_simple')
django.setup()

def test_booking_view_field_access():
    """Test that booking view accesses the correct form fields"""
    print("Testing Booking View Field Access...")
    
    try:
        # Read the booking view file
        booking_view_path = '/Users/lelisra/Documents/code/tailwind4-django-how/project/app/views_package/booking_views.py'
        
        with open(booking_view_path, 'r') as f:
            content = f.read()
            
        # Check that it's using the correct field name
        if "form.cleaned_data['scheduled_pickup_time']" in content:
            print("✅ Booking view uses correct 'scheduled_pickup_time' field")
        else:
            print("❌ Booking view may be using incorrect field name")
            
        # Check that it's not using the old incorrect field name
        if "form.cleaned_data['pickup_datetime']" not in content:
            print("✅ Old 'pickup_datetime' field reference removed")
        else:
            print("❌ Still references old 'pickup_datetime' field")
            
        # Check for required form fields
        required_accesses = [
            "form.cleaned_data['pickup_location']",
            "form.cleaned_data['dropoff_location']", 
            "form.cleaned_data['scheduled_pickup_time']"
        ]
        
        for access in required_accesses:
            if access in content:
                print(f"✅ Found access to {access}")
            else:
                print(f"❌ Missing access to {access}")
                
        # Check for optional field handling
        optional_patterns = [
            "form.cleaned_data.get('purpose'", 
            "form.cleaned_data.get('priority'",
            "form.cleaned_data.get('special_requirements'"
        ]
        
        for pattern in optional_patterns:
            if pattern in content:
                print(f"✅ Safe optional access: {pattern}")
            else:
                print(f"⚠️  May be missing optional access: {pattern}")
                
    except Exception as e:
        print(f"❌ Error testing booking view: {e}")


def test_form_field_names():
    """Test that form field names match what's expected"""
    print("\nTesting Form Field Names...")
    
    try:
        from app.forms import PreBookedRideForm
        
        form = PreBookedRideForm()
        field_names = list(form.fields.keys())
        
        print(f"✅ Available form fields: {field_names}")
        
        # Check for critical fields
        critical_fields = ['pickup_location', 'dropoff_location', 'scheduled_pickup_date', 'scheduled_pickup_time']
        
        for field in critical_fields:
            if field in field_names:
                print(f"✅ Critical field '{field}' present")
            else:
                print(f"❌ Critical field '{field}' missing")
                
    except Exception as e:
        print(f"❌ Error testing form fields: {e}")


if __name__ == '__main__':
    print("🔍 Testing Booking Integration")
    print("=" * 50)
    
    test_booking_view_field_access()
    test_form_field_names()
    
    print("\n" + "=" * 50)
    print("✨ Integration testing complete!")