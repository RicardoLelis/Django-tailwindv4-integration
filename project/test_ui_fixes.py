#!/usr/bin/env python
"""
Test script to verify the UI fixes for pre-book functionality
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings_simple')
django.setup()

from app.forms import PreBookedRideForm


def test_pre_book_button_visibility():
    """Test that pre-book button exists in home template"""
    print("Testing Pre-Book Button Visibility...")
    
    try:
        template_path = '/Users/lelisra/Documents/code/tailwind4-django-how/project/app/templates/home.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
            
        # Check for pre-book button
        if 'Pre-Book Ride' in content:
            print("✅ Pre-Book button text found in home template")
        else:
            print("❌ Pre-Book button text missing from home template")
            
        if 'pre_book_ride' in content:
            print("✅ Pre-book URL reference found in home template")
        else:
            print("❌ Pre-book URL reference missing from home template")
            
        # Check if button is conditionally shown
        if 'booking-buttons' in content and 'hidden' in content:
            print("✅ Booking buttons have conditional visibility logic")
        else:
            print("❌ Booking buttons may not have proper visibility logic")
            
    except Exception as e:
        print(f"❌ Error testing pre-book button visibility: {e}")


def test_form_styling():
    """Test that form has proper styling for readability"""
    print("\nTesting Form Styling...")
    
    try:
        form = PreBookedRideForm()
        
        # Check that form fields have glass-input class
        field_tests = [
            ('pickup_location', 'pickup location'),
            ('dropoff_location', 'dropoff location'), 
            ('scheduled_pickup_date', 'pickup date'),
            ('scheduled_pickup_time', 'pickup time'),
            ('estimated_duration_minutes', 'duration'),
            ('special_requirements', 'special requirements')
        ]
        
        for field_name, display_name in field_tests:
            if field_name in form.fields:
                widget = form.fields[field_name].widget
                widget_class = widget.attrs.get('class', '')
                
                if 'glass-input' in widget_class:
                    print(f"✅ {display_name} field has glass-input styling")
                else:
                    print(f"❌ {display_name} field missing glass-input styling")
                    
                # Check for old white text classes that would make text invisible
                if 'text-white' in widget_class:
                    print(f"⚠️  {display_name} field may have invisible white text")
                else:
                    print(f"✅ {display_name} field has readable text styling")
            else:
                print(f"⚠️  {display_name} field not found in form")
                
    except Exception as e:
        print(f"❌ Error testing form styling: {e}")


def test_template_text_colors():
    """Test that template uses readable text colors"""
    print("\nTesting Template Text Colors...")
    
    try:
        template_path = '/Users/lelisra/Documents/code/tailwind4-django-how/project/app/templates/bookings/pre_book_ride.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
            
        # Check for improved styling classes
        if 'glass-card' in content:
            print("✅ Template uses glass-card for better contrast")
        else:
            print("❌ Template missing glass-card styling")
            
        if 'text-gray-700' in content:
            print("✅ Template uses readable dark text colors")
        else:
            print("⚠️  Template may not have optimal text colors")
            
        # Check for problematic white text
        white_text_count = content.count('text-white')
        if white_text_count == 0:
            print("✅ No problematic white text found")
        else:
            print(f"⚠️  Found {white_text_count} instances of white text - verify readability")
            
        # Check for gradient text on headers
        if 'gradient-text' in content:
            print("✅ Template uses gradient text for headers")
        else:
            print("❌ Template missing gradient text styling")
            
    except Exception as e:
        print(f"❌ Error testing template text colors: {e}")


def test_css_classes():
    """Test that CSS classes are properly defined"""
    print("\nTesting CSS Classes...")
    
    try:
        template_path = '/Users/lelisra/Documents/code/tailwind4-django-how/project/templates/base.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
            
        # Check for required CSS classes
        required_classes = ['glass-effect', 'glass-card', 'glass-input', 'gradient-text']
        
        for class_name in required_classes:
            if f'.{class_name}' in content:
                print(f"✅ {class_name} CSS class is defined")
            else:
                print(f"❌ {class_name} CSS class is missing")
                
        # Check glass-input properties for readability
        if 'rgba(255, 255, 255, 0.8)' in content:
            print("✅ Glass input has semi-transparent white background for readability")
        else:
            print("⚠️  Glass input background may not be optimal for readability")
            
        if 'color: #374151' in content:
            print("✅ Glass input has dark text color for readability")
        else:
            print("⚠️  Glass input text color may not be readable")
            
    except Exception as e:
        print(f"❌ Error testing CSS classes: {e}")


if __name__ == '__main__':
    print("🔍 Testing UI Fixes for Pre-Book Functionality")
    print("=" * 60)
    
    test_pre_book_button_visibility()
    test_form_styling() 
    test_template_text_colors()
    test_css_classes()
    
    print("\n" + "=" * 60)
    print("✨ UI testing complete!")