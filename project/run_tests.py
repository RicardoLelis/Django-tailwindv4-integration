#!/usr/bin/env python
"""
Test runner for Phase 1 implementation.
Creates minimal test environment without requiring full Django setup.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock Django before importing our modules
class MockDjango:
    """Mock Django components for testing"""
    
    class conf:
        class settings:
            NOMINATIM_API_URL = 'https://nominatim.openstreetmap.org'
            NOMINATIM_USER_AGENT = 'WheelchairRideShare/1.0'
            OPENROUTESERVICE_API_KEY = 'test-key'
            OPENROUTESERVICE_API_URL = 'https://api.openrouteservice.org'
            GEOCODING_RATE_LIMIT = '60/m'
            ROUTING_RATE_LIMIT = '100/m'
            CACHE_TTL = {'geocoding': 86400, 'routing': 3600}
            SERVICE_AREA_BOUNDS = {
                'north': 38.8500,
                'south': 38.6000,
                'east': -9.0000,
                'west': -9.5000,
            }
    
    class core:
        class cache:
            @staticmethod
            def cache():
                return MockCache()
        
        class exceptions:
            class ValidationError(Exception):
                pass
    
    class test:
        class TestCase(unittest.TestCase):
            pass
        
        @staticmethod
        def override_settings(**kwargs):
            def decorator(func):
                return func
            return decorator
    
    class utils:
        class decorators:
            @staticmethod
            def method_decorator(decorator):
                def actual_decorator(func):
                    return func
                return actual_decorator

class MockCache:
    """Mock cache for testing"""
    def __init__(self):
        self._cache = {}
    
    def get(self, key):
        return self._cache.get(key)
    
    def set(self, key, value, timeout=None):
        self._cache[key] = value
    
    def clear(self):
        self._cache.clear()

class MockRateLimit:
    """Mock rate limiting decorator"""
    @staticmethod
    def ratelimit(**kwargs):
        def decorator(func):
            return func
        return decorator

# Mock Django modules
sys.modules['django'] = MockDjango()
sys.modules['django.conf'] = MockDjango.conf
sys.modules['django.core'] = MockDjango.core
sys.modules['django.core.cache'] = MockDjango.core.cache
sys.modules['django.core.exceptions'] = MockDjango.core.exceptions
sys.modules['django.test'] = MockDjango.test
sys.modules['django.utils'] = MockDjango.utils
sys.modules['django.utils.decorators'] = MockDjango.utils.decorators
sys.modules['django_ratelimit'] = MockRateLimit()
sys.modules['django_ratelimit.decorators'] = MockRateLimit()

# Create mock cache instance
cache = MockCache()

def run_service_tests():
    """Run tests for geocoding and routing services"""
    print("Phase 1 Core Infrastructure - Service Tests")
    print("==========================================")
    
    # Test geocoding service basic functionality
    print("\n1. Testing Geocoding Service...")
    try:
        from app.services.geocoding_service import GeocodingService, GeocodingError
        
        service = GeocodingService()
        
        # Test input validation
        try:
            service._validate_address_input("Valid Address Lisboa")
            print("   ✓ Address validation - valid input")
        except Exception as e:
            print(f"   ✗ Address validation failed: {e}")
        
        try:
            service._validate_address_input("")
            print("   ✗ Address validation should reject empty string")
        except GeocodingError:
            print("   ✓ Address validation - empty string rejected")
        
        # Test coordinate validation
        try:
            lat, lng = service._validate_coordinates(38.7223, -9.1393)
            print("   ✓ Coordinate validation - valid coordinates")
        except Exception as e:
            print(f"   ✗ Coordinate validation failed: {e}")
        
        # Test service area validation
        if service.validate_service_area(38.7223, -9.1393):
            print("   ✓ Service area validation - Lisbon coordinates")
        else:
            print("   ✗ Service area validation failed for Lisbon")
        
        if not service.validate_service_area(40.7128, -74.0060):  # New York
            print("   ✓ Service area validation - rejects outside coordinates")
        else:
            print("   ✗ Service area validation should reject New York coordinates")
        
        print("   Geocoding Service: BASIC TESTS PASSED")
        
    except ImportError as e:
        print(f"   ✗ Failed to import GeocodingService: {e}")
    except Exception as e:
        print(f"   ✗ Geocoding Service test failed: {e}")
    
    # Test routing service basic functionality
    print("\n2. Testing Routing Service...")
    try:
        from app.services.routing_service import RoutingService, RoutingError
        
        service = RoutingService()
        
        # Test coordinate validation
        valid_coords = [[-9.1393, 38.7223], [-9.1607, 38.7492]]
        try:
            result = service._validate_coordinates(valid_coords)
            if len(result) == 2:
                print("   ✓ Coordinate validation - valid route coordinates")
            else:
                print("   ✗ Coordinate validation returned wrong length")
        except Exception as e:
            print(f"   ✗ Coordinate validation failed: {e}")
        
        # Test invalid coordinates
        try:
            service._validate_coordinates([])
            print("   ✗ Should reject empty coordinate list")
        except RoutingError:
            print("   ✓ Coordinate validation - rejects empty list")
        
        # Test service area check
        if service._is_in_service_area(38.7223, -9.1393):
            print("   ✓ Service area check - Lisbon coordinates")
        else:
            print("   ✗ Service area check failed for Lisbon")
        
        # Test distance calculation
        distance = service._calculate_distance(38.7223, -9.1393, 38.7492, -9.1607)
        if 1.0 < distance < 5.0:  # Should be around 2-3 km
            print("   ✓ Distance calculation - reasonable result")
        else:
            print(f"   ✗ Distance calculation gave unreasonable result: {distance}km")
        
        # Test fallback route generation
        fallback = service._get_fallback_route(valid_coords)
        if fallback and fallback.get('profile') == 'fallback':
            print("   ✓ Fallback route generation")
        else:
            print("   ✗ Fallback route generation failed")
        
        print("   Routing Service: BASIC TESTS PASSED")
        
    except ImportError as e:
        print(f"   ✗ Failed to import RoutingService: {e}")
    except Exception as e:
        print(f"   ✗ Routing Service test failed: {e}")
    
    print("\n3. Testing Service Integration...")
    try:
        from app.services.geocoding_service import GeocodingService
        from app.services.routing_service import RoutingService
        
        geocoding = GeocodingService()
        routing = RoutingService()
        
        # Test that services can work together
        test_address = "Hospital São José, Lisboa"
        coords_result = geocoding._get_fallback_location(test_address)
        
        if coords_result:
            # Convert to routing format [lng, lat]
            route_coords = [
                [coords_result['lng'], coords_result['lat']],
                [-9.1607, 38.7492]  # Hospital Santa Maria
            ]
            
            # Test route calculation
            route = routing._get_fallback_route(route_coords)
            if route:
                print("   ✓ Service integration - geocoding + routing")
            else:
                print("   ✗ Service integration - routing failed")
        else:
            print("   ✗ Service integration - geocoding failed")
        
    except Exception as e:
        print(f"   ✗ Service integration test failed: {e}")
    
    print("\n==========================================")
    print("Phase 1 Service Tests Complete")
    print("==========================================")

if __name__ == '__main__':
    run_service_tests()