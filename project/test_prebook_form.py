#!/usr/bin/env python
"""
Test script to verify pre-book form processing
"""

import os
import sys
import django
from datetime import datetime, time, date, timedelta

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings_simple')
django.setup()

from django.utils import timezone
from app.forms import PreBookedRideForm


def test_form_data_processing():
    """Test that form correctly processes date and time fields"""
    print("Testing Pre-Book Form Data Processing...")
    
    try:
        # Create form data similar to what would be submitted
        tomorrow = date.today() + timedelta(days=1)
        pickup_time = time(14, 30)  # 2:30 PM
        
        form_data = {
            'pickup_location': 'Rua Engenheiro Francisco Lencastre Garrett 5',
            'dropoff_location': 'R. Mário Botas S/N, 1998-018 Lisboa',
            'scheduled_pickup_date': tomorrow,
            'scheduled_pickup_time': pickup_time,
            'estimated_duration_minutes': 60,
            'pickup_window_minutes': 15,
            'purpose': 'general',
            'priority': 'normal',
            'special_requirements': '',
        }
        
        # Create and validate form
        form = PreBookedRideForm(form_data)
        
        if form.is_valid():
            print("✅ Form validation passed")
            
            # Check that cleaned_data contains the combined datetime
            if 'scheduled_pickup_time' in form.cleaned_data:
                combined_datetime = form.cleaned_data['scheduled_pickup_time']
                print(f"✅ Combined datetime created: {combined_datetime}")
                
                # Check that it's timezone-aware
                if timezone.is_aware(combined_datetime):
                    print("✅ Datetime is timezone-aware")
                else:
                    print("❌ Datetime is not timezone-aware")
                    
                # Check that it combines date and time correctly
                expected_datetime = timezone.make_aware(datetime.combine(tomorrow, pickup_time))
                if combined_datetime == expected_datetime:
                    print("✅ Date and time combined correctly")
                else:
                    print(f"❌ Date/time combination incorrect. Expected: {expected_datetime}, Got: {combined_datetime}")
                    
            else:
                print("❌ Form missing scheduled_pickup_time in cleaned_data")
                print(f"Available fields: {list(form.cleaned_data.keys())}")
                
            # Test that the field names match what the booking view expects
            required_fields = [
                'pickup_location', 'dropoff_location', 'scheduled_pickup_time',
                'purpose', 'special_requirements', 'priority', 'pickup_window_minutes'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in form.cleaned_data:
                    missing_fields.append(field)
                    
            if not missing_fields:
                print("✅ All required fields present in cleaned_data")
            else:
                print(f"❌ Missing fields: {missing_fields}")
                
        else:
            print("❌ Form validation failed")
            print("Form errors:", form.errors)
            
    except Exception as e:
        print(f"❌ Error testing form processing: {e}")
        import traceback
        traceback.print_exc()


def test_form_field_consistency():
    """Test that form fields match template expectations"""
    print("\nTesting Form Field Consistency...")
    
    try:
        form = PreBookedRideForm()
        
        # Check that the form has the fields referenced in the template
        template_fields = [
            'pickup_location', 'dropoff_location', 'scheduled_pickup_date', 
            'scheduled_pickup_time', 'estimated_duration_minutes', 'special_requirements'
        ]
        
        for field_name in template_fields:
            if field_name in form.fields:
                print(f"✅ Form field '{field_name}' exists")
            else:
                print(f"❌ Form field '{field_name}' missing")
                
        # Check that the clean method exists
        if hasattr(form, 'clean'):
            print("✅ Form has clean method for date/time processing")
        else:
            print("❌ Form missing clean method")
            
    except Exception as e:
        print(f"❌ Error testing form consistency: {e}")


if __name__ == '__main__':
    print("🧪 Testing Pre-Book Form Processing")
    print("=" * 60)
    
    test_form_data_processing()
    test_form_field_consistency()
    
    print("\n" + "=" * 60)
    print("✨ Form testing complete!")