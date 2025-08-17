#!/usr/bin/env python
"""
Test script to verify the Book Ride button is properly structured
"""

def test_book_button_visibility():
    """Test that Book Ride button has proper layout structure"""
    print("Testing Book Ride Button Structure...")
    
    try:
        template_path = '/Users/lelisra/Documents/code/tailwind4-django-how/project/app/templates/bookings/pre_book_ride.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
            
        # Check for responsive layout fixes
        if 'flex flex-col sm:flex-row justify-center gap-4' in content:
            print("✅ Button layout uses responsive flex design")
        else:
            print("❌ Button layout may not be responsive")
            
        # Check for Book Ride button text
        if 'Pre-Book Ride' in content:
            print("✅ Pre-Book Ride button text found")
        else:
            print("❌ Pre-Book Ride button text missing")
            
        # Check for proper button styling
        if 'type="submit"' in content:
            print("✅ Submit button type is properly set")
        else:
            print("❌ Submit button may not be properly configured")
            
        # Check for separated checkbox and buttons
        if 'mb-4' in content and 'Action Buttons' in content:
            print("✅ Checkbox and buttons are properly separated")
        else:
            print("⚠️  Layout separation may need improvement")
            
        # Check for centered button layout
        if 'justify-center' in content:
            print("✅ Buttons are centered for better visibility")
        else:
            print("❌ Buttons may not be properly centered")
            
        # Check for proper button padding
        if 'px-8 py-3' in content:
            print("✅ Buttons have adequate padding for mobile")
        else:
            print("⚠️  Button padding may be insufficient")
            
        # Check for button styling
        if 'bg-gradient-to-r from-purple-600 to-pink-600' in content:
            print("✅ Book button has proper gradient styling")
        else:
            print("❌ Book button missing gradient styling")
            
    except Exception as e:
        print(f"❌ Error testing book button structure: {e}")


if __name__ == '__main__':
    print("🔍 Testing Book Ride Button Visibility")
    print("=" * 50)
    
    test_book_button_visibility()
    
    print("\n" + "=" * 50)
    print("✨ Button testing complete!")