"""
URL configuration for Phase 1 Core Infrastructure API endpoints.
Includes geocoding and routing services with security middleware.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PreBookedRideViewSet, 
    DriverCalendarViewSet, 
    RideMatchOfferViewSet
)
from .geocoding_views import (
    geocode_address,
    reverse_geocode,
    get_address_suggestions,
    validate_service_area,
    get_service_area_bounds,
    geocode_legacy,
    geocoding_health_check
)
from .routing_views import (
    get_wheelchair_route,
    get_driving_route,
    get_multiple_routes,
    calculate_route_accessibility,
    get_routing_capabilities,
    routing_health_check
)
from .geocoding_public_views import (
    public_geocoding_suggestions,
    public_reverse_geocode,
    public_service_area
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'bookings', PreBookedRideViewSet, basename='prebookedride')
router.register(r'calendar', DriverCalendarViewSet, basename='drivercalendar')
router.register(r'offers', RideMatchOfferViewSet, basename='ridematchoffer')

# Define URL patterns
urlpatterns = [
    # ViewSet endpoints
    path('', include(router.urls)),
    
    # Geocoding endpoints
    path('geocoding/', geocode_address, name='geocode_address'),
    path('geocoding/reverse/', reverse_geocode, name='reverse_geocode'),
    path('geocoding/suggestions/', get_address_suggestions, name='address_suggestions'),
    path('geocoding/validate-area/', validate_service_area, name='validate_service_area'),
    path('geocoding/service-area/', get_service_area_bounds, name='service_area_bounds'),
    path('geocoding/health/', geocoding_health_check, name='geocoding_health'),
    
    # Legacy geocoding endpoint (for backward compatibility)
    path('geocode/', geocode_legacy, name='geocode_legacy'),
    
    # Routing endpoints
    path('routing/wheelchair/', get_wheelchair_route, name='wheelchair_route'),
    path('routing/driving/', get_driving_route, name='driving_route'),
    path('routing/alternatives/', get_multiple_routes, name='multiple_routes'),
    path('routing/accessibility/', calculate_route_accessibility, name='route_accessibility'),
    path('routing/capabilities/', get_routing_capabilities, name='routing_capabilities'),
    path('routing/health/', routing_health_check, name='routing_health'),
    
    # Development-only public endpoints
    path('geocoding/public/suggestions/', public_geocoding_suggestions, name='public_geocoding_suggestions'),
    path('geocoding/public/reverse/', public_reverse_geocode, name='public_reverse_geocode'),
    path('geocoding/public/service-area/', public_service_area, name='public_service_area'),
]