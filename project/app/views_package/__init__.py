"""
Views package - organizing views by functionality.
"""

# Import all views to maintain backward compatibility
from ..views import *

# Import new booking views
from .booking_views import (
    pre_book_ride,
    search_drivers,
    confirm_booking,
    booking_details,
    cancel_booking,
    my_bookings,
    recurring_rides,
    create_recurring_ride,
    pause_recurring_ride,
    ajax_calculate_fare,
    ajax_check_availability,
)

# Import driver booking views
from .driver_booking_views import (
    driver_calendar,
    update_calendar,
    driver_offers,
    accept_offer,
    decline_offer,
    driver_bookings,
    driver_booking_detail,
    calendar_week_view,
    waiting_opportunities,
)

# Import driver status views
from .driver_status_views import (
    toggle_driver_status,
    update_driver_location,
    driver_live_offers,
)

__all__ = [
    # Original views (imported from views.py)
    'landing_page',
    'rider_registration',
    'login_view',
    'logout_view',
    'home',
    'book_ride',
    'driver_landing',
    'driver_initial_registration',
    'driver_verify_email',
    'driver_complete_registration',
    'driver_register_basic',
    'driver_register_professional',
    'driver_upload_documents',
    'driver_background_consent',
    'driver_register_vehicle',
    'driver_vehicle_accessibility',
    'driver_vehicle_safety',
    'driver_vehicle_documents',
    'driver_vehicle_photos',
    'driver_training',
    'driver_training_module',
    'driver_dashboard',
    'driver_documents',
    'ajax_upload_document',
    'ajax_upload_vehicle_photo',
    
    # Booking views
    'pre_book_ride',
    'search_drivers',
    'confirm_booking',
    'booking_details',
    'cancel_booking',
    'my_bookings',
    'recurring_rides',
    'create_recurring_ride',
    'pause_recurring_ride',
    'ajax_calculate_fare',
    'ajax_check_availability',
    'ajax_geocode',
    
    # Driver booking views
    'driver_calendar',
    'update_calendar',
    'driver_offers',
    'accept_offer',
    'decline_offer',
    'driver_bookings',
    'driver_booking_detail',
    'calendar_week_view',
    'waiting_opportunities',
    
    # Driver status views
    'toggle_driver_status',
    'update_driver_location',
    'driver_live_offers',
]