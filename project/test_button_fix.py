#!/usr/bin/env python
"""
Test script to verify the Pre-Book Ride button text and styling fixes
"""

def test_button_styling_fix():
    """Test that Pre-Book Ride button has proper text and styling"""
    print("Testing Pre-Book Ride Button Styling Fix...")
    
    try:
        # Check template button
        template_path = '/Users/lelisra/Documents/code/tailwind4-django-how/project/app/templates/bookings/pre_book_ride.html'
        
        with open(template_path, 'r') as f:
            template_content = f.read()
            
        # Check for button text
        if 'Pre-Book Ride' in template_content:
            print("✅ 'Pre-Book Ride' text found in button")
        else:
            print("❌ Button text missing")
            
        # Check for custom submit-button class
        if 'submit-button' in template_content:
            print("✅ Custom submit-button class applied")
        else:
            print("❌ Custom button class missing")
            
        # Check for proper button structure
        if 'type="submit"' in template_content:
            print("✅ Button has correct submit type")
        else:
            print("❌ Button type incorrect")
            
        # Check for minimum width
        if 'min-w-[200px]' in template_content:
            print("✅ Button has minimum width for visibility")
        else:
            print("⚠️  Button width may be insufficient")
            
        # Check CSS styles
        base_template_path = '/Users/lelisra/Documents/code/tailwind4-django-how/project/templates/base.html'
        
        with open(base_template_path, 'r') as f:
            css_content = f.read()
            
        # Check for submit-button CSS class
        if '.submit-button' in css_content:
            print("✅ Custom submit-button CSS class defined")
        else:
            print("❌ Custom button CSS missing")
            
        # Check for forced white text color
        if 'color: white !important' in css_content:
            print("✅ Button text color forced to white")
        else:
            print("❌ Button text color not enforced")
            
        # Check for gradient background
        if 'background: linear-gradient' in css_content and 'submit-button' in css_content:
            print("✅ Button has gradient background")
        else:
            print("❌ Button gradient background missing")
            
        # Check for hover effects
        if '.submit-button:hover' in css_content:
            print("✅ Button hover effects defined")
        else:
            print("❌ Button hover effects missing")
            
    except Exception as e:
        print(f"❌ Error testing button styling: {e}")


if __name__ == '__main__':
    print("🔍 Testing Pre-Book Ride Button Fix")
    print("=" * 50)
    
    test_button_styling_fix()
    
    print("\n" + "=" * 50)
    print("✨ Button fix testing complete!")