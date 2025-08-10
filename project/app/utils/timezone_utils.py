"""
Timezone utilities for multi-geography support.
Handles timezone conversion and localization for different service areas.
"""

import pytz
from django.utils import timezone
from django.conf import settings
from datetime import datetime


# Timezone mappings for different service areas
SERVICE_AREA_TIMEZONES = {
    'lisbon': 'Europe/Lisbon',
    'porto': 'Europe/Lisbon', 
    'madrid': 'Europe/Madrid',
    'barcelona': 'Europe/Madrid',
    'london': 'Europe/London',
    'paris': 'Europe/Paris',
    'berlin': 'Europe/Berlin',
    'rome': 'Europe/Rome',
    'amsterdam': 'Europe/Amsterdam',
    # Add more cities as service expands
}


def get_service_area_timezone(service_area_code: str = None) -> str:
    """
    Get the timezone for a specific service area.
    
    Args:
        service_area_code: Code for the service area (e.g., 'lisbon', 'madrid')
        
    Returns:
        Timezone string (e.g., 'Europe/Lisbon')
    """
    if not service_area_code:
        # Default to Django's configured timezone
        return getattr(settings, 'TIME_ZONE', 'UTC')
    
    return SERVICE_AREA_TIMEZONES.get(
        service_area_code.lower(), 
        getattr(settings, 'TIME_ZONE', 'UTC')
    )


def localize_datetime(dt: datetime, service_area_code: str = None) -> datetime:
    """
    Convert a datetime to the appropriate timezone for a service area.
    
    Args:
        dt: Datetime to convert (can be naive or timezone-aware)
        service_area_code: Service area code for timezone lookup
        
    Returns:
        Timezone-aware datetime in the appropriate timezone
    """
    target_tz_str = get_service_area_timezone(service_area_code)
    target_tz = pytz.timezone(target_tz_str)
    
    # If datetime is naive, assume it's in UTC
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, pytz.UTC)
    
    # Convert to target timezone
    return dt.astimezone(target_tz)


def format_local_time(dt: datetime, service_area_code: str = None, format_str: str = '%H:%M') -> str:
    """
    Format a datetime in the local timezone for display.
    
    Args:
        dt: Datetime to format
        service_area_code: Service area for timezone
        format_str: strftime format string
        
    Returns:
        Formatted time string in local timezone
    """
    local_dt = localize_datetime(dt, service_area_code)
    return local_dt.strftime(format_str)


def get_current_local_time(service_area_code: str = None) -> datetime:
    """
    Get the current time in a specific service area's timezone.
    
    Args:
        service_area_code: Service area code
        
    Returns:
        Current datetime in the service area's timezone
    """
    utc_now = timezone.now()
    return localize_datetime(utc_now, service_area_code)


def detect_service_area_from_coordinates(lat: float, lng: float) -> str:
    """
    Detect service area from coordinates (for future expansion).
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        Service area code
    """
    # Simple coordinate-based detection
    # This could be expanded with proper geofencing
    
    # Portugal bounds (approximate)
    if 36.0 <= lat <= 42.5 and -9.5 <= lng <= -6.0:
        # More precise detection could distinguish between Lisbon/Porto
        if lat > 40.0:  # Northern Portugal (Porto area)
            return 'porto'
        else:  # Central/Southern Portugal (Lisbon area)
            return 'lisbon'
    
    # Spain bounds (approximate) 
    elif 35.0 <= lat <= 44.0 and -10.0 <= lng <= 4.0:
        if lat > 40.0:  # Northern Spain
            return 'madrid'
        else:  # Southern Spain, but could be Barcelona too
            return 'madrid'
    
    # Default fallback
    return 'lisbon'


# Convenience functions for common operations
def now_local(service_area_code: str = None) -> datetime:
    """Get current time in service area timezone."""
    return get_current_local_time(service_area_code)


def format_ride_time(pickup_datetime: datetime, service_area_code: str = None) -> str:
    """Format a ride pickup time for display."""
    return format_local_time(pickup_datetime, service_area_code, '%b %d, %I:%M %p')


def format_offer_time(created_at: datetime, service_area_code: str = None) -> str:
    """Format offer creation time for driver dashboard."""
    return format_local_time(created_at, service_area_code, '%H:%M')