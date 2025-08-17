#!/usr/bin/env python
"""
Test script to verify Pre-Book button visibility on home page
"""

def test_prebook_button_always_visible():
    """Test that Pre-Book button is always visible on home page"""
    print("Testing Pre-Book Button Always Visible...")
    
    try:
        template_path = '/Users/lelisra/Documents/code/tailwind4-django-how/project/app/templates/home.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
            
        # Check for always-visible Pre-Book button
        if 'Pre-Book Button (Always Visible)' in content:
            print("✅ Always-visible Pre-Book button comment found")
        else:
            print("❌ Always-visible Pre-Book button comment missing")
            
        # Check that there's a Pre-Book link outside the conditional booking-buttons div
        prebook_links = content.count('pre_book_ride')
        if prebook_links >= 2:
            print(f"✅ Multiple Pre-Book links found ({prebook_links}) - indicates both conditional and always-visible versions")
        elif prebook_links == 1:
            print("⚠️  Only one Pre-Book link found - may still be conditional only")
        else:
            print("❌ No Pre-Book links found")
            
        # Check for the new button outside booking-buttons div
        lines = content.split('\n')
        found_always_visible = False
        inside_booking_buttons = False
        
        for line in lines:
            if 'id="booking-buttons"' in line:
                inside_booking_buttons = True
                continue
            if inside_booking_buttons and '</div>' in line and 'booking-buttons' not in line:
                inside_booking_buttons = False
                continue
                
            # Look for Pre-Book button outside the booking-buttons div
            if not inside_booking_buttons and 'pre_book_ride' in line and '<a href=' in line:
                found_always_visible = True
                break
                
        if found_always_visible:
            print("✅ Pre-Book button found outside conditional booking-buttons section")
        else:
            print("❌ Pre-Book button only in conditional section")
            
        # Check for proper styling
        if 'bg-gradient-to-r from-purple-600 to-violet-600' in content:
            print("✅ Pre-Book button has proper gradient styling")
        else:
            print("⚠️  Pre-Book button styling may be missing")
            
        # Check for calendar icon
        if 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' in content:
            print("✅ Calendar icon found in Pre-Book button")
        else:
            print("⚠️  Calendar icon may be missing from Pre-Book button")
            
        # Check for updated description text
        if 'Pre-Book Ride button above' in content:
            print("✅ Description text updated to reference always-visible button")
        else:
            print("❌ Description text not updated")
            
    except Exception as e:
        print(f"❌ Error testing Pre-Book button visibility: {e}")


def test_button_positioning():
    """Test that the button is positioned correctly in the header area"""
    print("\nTesting Pre-Book Button Positioning...")
    
    try:
        template_path = '/Users/lelisra/Documents/code/tailwind4-django-how/project/app/templates/home.html'
        
        with open(template_path, 'r') as f:
            content = f.read()
            
        # Check that button is near the "Book Your Ride" header
        if 'Book Your Ride' in content and 'Pre-Book Ride' in content:
            # Find positions
            book_ride_pos = content.find('Book Your Ride')
            prebook_pos = content.find('Pre-Book Ride')
            
            if book_ride_pos > 0 and prebook_pos > book_ride_pos:
                distance = prebook_pos - book_ride_pos
                if distance < 2000:  # Within reasonable distance
                    print("✅ Pre-Book button positioned near Book Your Ride header")
                else:
                    print("⚠️  Pre-Book button may be too far from header")
            else:
                print("❌ Pre-Book button positioning unclear")
        
        # Check for flex layout
        if 'flex items-center space-x-3' in content:
            print("✅ Buttons use proper flex layout for alignment")
        else:
            print("⚠️  Button layout may not be optimal")
            
    except Exception as e:
        print(f"❌ Error testing button positioning: {e}")


if __name__ == '__main__':
    print("🔍 Testing Pre-Book Button Visibility on Home Page")
    print("=" * 60)
    
    test_prebook_button_always_visible()
    test_button_positioning()
    
    print("\n" + "=" * 60)
    print("✨ Visibility testing complete!")