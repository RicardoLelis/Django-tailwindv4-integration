"""
Unit tests for the enhanced routing service.
Tests wheelchair accessibility routing, API integration, caching, and error handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.core.cache import cache
import requests

from app.services.routing_service import RoutingService, RoutingError


class RoutingServiceTestCase(TestCase):
    """Test cases for RoutingService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.service = RoutingService()
        cache.clear()  # Clear cache between tests
        
        # Common test coordinates (Lisbon area)
        self.lisbon_center = [-9.1393, 38.7223]
        self.hospital_santa_maria = [-9.1607, 38.7492]
        self.belém = [-9.2034, 38.6968]
        
        self.valid_coordinates = [self.lisbon_center, self.hospital_santa_maria]
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_init_with_settings(self):
        """Test service initialization with settings"""
        self.assertIsNotNone(self.service.api_url)
        self.assertIsNotNone(self.service.session)
        self.assertEqual(self.service.wheelchair_profile, 'wheelchair')
        self.assertEqual(self.service.driving_profile, 'driving-car')
    
    def test_validate_coordinates_valid(self):
        """Test coordinate validation with valid inputs"""
        valid_cases = [
            [[-9.1393, 38.7223], [-9.1607, 38.7492]],  # Two points in Lisbon
            [[-9.1393, 38.7223], [-9.1607, 38.7492], [-9.2034, 38.6968]],  # Three points
        ]
        
        for coordinates in valid_cases:
            with self.subTest(coordinates=coordinates):
                result = self.service._validate_coordinates(coordinates)
                self.assertEqual(len(result), len(coordinates))
                self.assertIsInstance(result, list)
                
                # Check each coordinate is properly formatted
                for coord in result:
                    self.assertIsInstance(coord, list)
                    self.assertEqual(len(coord), 2)
                    self.assertIsInstance(coord[0], float)  # longitude
                    self.assertIsInstance(coord[1], float)  # latitude
    
    def test_validate_coordinates_invalid(self):
        """Test coordinate validation with invalid inputs"""
        invalid_cases = [
            [],  # Empty list
            [[-9.1393, 38.7223]],  # Only one coordinate
            [[-9.1393]],  # Missing latitude
            [[-9.1393, 38.7223, 100]],  # Too many values
            [["invalid", 38.7223]],  # Non-numeric longitude
            [[-9.1393, "invalid"]],  # Non-numeric latitude
            [[-200, 38.7223]],  # Longitude out of range
            [[-9.1393, 100]],  # Latitude out of range
            [[0, 0], [0, 0]],  # Outside service area
        ]
        
        for coordinates in invalid_cases:
            with self.subTest(coordinates=coordinates):
                with self.assertRaises(RoutingError):
                    self.service._validate_coordinates(coordinates)
    
    def test_is_in_service_area(self):
        """Test service area validation"""
        # Coordinates within Lisbon area should be valid
        valid_coords = [
            (38.7223, -9.1393),  # Lisbon center
            (38.7492, -9.1607),  # Hospital Santa Maria
            (38.6968, -9.2034),  # Belém
        ]
        
        for lat, lng in valid_coords:
            with self.subTest(lat=lat, lng=lng):
                self.assertTrue(self.service._is_in_service_area(lat, lng))
        
        # Coordinates outside service area should be invalid
        invalid_coords = [
            (40.7128, -74.0060),  # New York
            (51.5074, -0.1278),   # London
            (0, 0),               # Null Island
        ]
        
        for lat, lng in invalid_coords:
            with self.subTest(lat=lat, lng=lng):
                self.assertFalse(self.service._is_in_service_area(lat, lng))
    
    @patch('app.services.routing_service.requests.Session.post')
    def test_get_wheelchair_route_success(self, mock_post):
        """Test wheelchair routing with successful API response"""
        # Mock successful OpenRouteService response
        mock_response = Mock()
        mock_response.json.return_value = {
            'features': [{
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[-9.1393, 38.7223], [-9.1607, 38.7492]]
                },
                'properties': {
                    'summary': {
                        'distance': 5000,  # 5km in meters
                        'duration': 1200   # 20 minutes in seconds
                    },
                    'segments': [{
                        'steps': [{
                            'instruction': 'Head north',
                            'distance': 5000,
                            'duration': 1200,
                            'type': 0,
                            'name': 'Test Route'
                        }]
                    }]
                }
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.service.get_wheelchair_route(self.valid_coordinates)
        
        self.assertIsNotNone(result)
        self.assertIn('geometry', result)
        self.assertIn('summary', result)
        self.assertIn('instructions', result)
        self.assertIn('accessibility', result)
        
        # Check summary data
        self.assertEqual(result['summary']['distance'], 5.0)  # Converted to km
        self.assertEqual(result['summary']['duration'], 20.0)  # Converted to minutes
        
        # Check accessibility info
        self.assertIn('score', result['accessibility'])
        self.assertIn('max_incline', result['accessibility'])
    
    def test_get_wheelchair_route_api_key_missing(self):
        """Test wheelchair routing without API key falls back to mock data"""
        # Create service without API key
        with override_settings(OPENROUTESERVICE_API_KEY=None):
            service = RoutingService()
            
            result = service.get_wheelchair_route(self.valid_coordinates)
            
            self.assertIsNotNone(result)
            self.assertEqual(result['profile'], 'fallback')
            self.assertIn('warnings', result)
            self.assertIn('fallback method', result['warnings'][0])
    
    @patch('app.services.routing_service.requests.Session.post')
    def test_get_wheelchair_route_api_error_fallback(self, mock_post):
        """Test wheelchair routing with API error falls back to mock data"""
        # Mock API error
        mock_post.side_effect = requests.RequestException("API Error")
        
        result = self.service.get_wheelchair_route(self.valid_coordinates)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['profile'], 'fallback')
        self.assertIn('warnings', result)
    
    def test_wheelchair_route_caching(self):
        """Test that wheelchair routes are cached"""
        coordinates = self.valid_coordinates
        
        # Mock the API request method to track calls
        with patch.object(self.service, '_make_ors_request') as mock_api:
            mock_api.return_value = {
                'features': [{
                    'geometry': {'type': 'LineString', 'coordinates': coordinates},
                    'properties': {
                        'summary': {'distance': 5000, 'duration': 1200},
                        'segments': [{'steps': []}]
                    }
                }]
            }
            
            # First call should hit the API
            result1 = self.service.get_wheelchair_route(coordinates)
            self.assertEqual(mock_api.call_count, 1)
            
            # Second call should use cache
            result2 = self.service.get_wheelchair_route(coordinates)
            self.assertEqual(mock_api.call_count, 1)  # No additional API call
            
            # Results should be identical
            self.assertEqual(result1['summary'], result2['summary'])
    
    @patch('app.services.routing_service.requests.Session.post')
    def test_get_driving_route_success(self, mock_post):
        """Test driving routing with successful API response"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'features': [{
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[-9.1393, 38.7223], [-9.1607, 38.7492]]
                },
                'properties': {
                    'summary': {
                        'distance': 4500,  # 4.5km in meters
                        'duration': 900    # 15 minutes in seconds
                    },
                    'segments': [{
                        'steps': [{
                            'instruction': 'Head north on main road',
                            'distance': 4500,
                            'duration': 900,
                            'type': 0,
                            'name': 'Main Road'
                        }]
                    }]
                }
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.service.get_driving_route(self.valid_coordinates)
        
        self.assertIsNotNone(result)
        self.assertIn('geometry', result)
        self.assertIn('summary', result)
        self.assertEqual(result['profile'], 'driving')
        self.assertEqual(result['summary']['distance'], 4.5)
        self.assertEqual(result['summary']['duration'], 15.0)
    
    def test_get_driving_route_with_avoidance(self):
        """Test driving route with toll and highway avoidance"""
        with patch.object(self.service, '_make_ors_driving_request') as mock_api:
            mock_api.return_value = {
                'features': [{
                    'geometry': {'type': 'LineString', 'coordinates': self.valid_coordinates},
                    'properties': {
                        'summary': {'distance': 5000, 'duration': 1200},
                        'segments': [{'steps': []}]
                    }
                }]
            }
            
            # Test with both avoidance options
            result = self.service.get_driving_route(
                self.valid_coordinates,
                avoid_tolls=True,
                avoid_highways=True
            )
            
            self.assertIsNotNone(result)
            # Verify the mock was called with correct parameters
            mock_api.assert_called_once_with(self.valid_coordinates, True, True)
    
    def test_get_avoid_features_for_wheelchair(self):
        """Test avoid features selection for wheelchair accessibility"""
        # With obstacles avoidance
        features_with_avoidance = self.service._get_avoid_features(True)
        self.assertIn('ferries', features_with_avoidance)
        self.assertIn('highways', features_with_avoidance)
        self.assertIn('steps', features_with_avoidance)
        
        # Without obstacles avoidance
        features_without_avoidance = self.service._get_avoid_features(False)
        self.assertIn('ferries', features_without_avoidance)
        self.assertNotIn('highways', features_without_avoidance)
        self.assertNotIn('steps', features_without_avoidance)
    
    def test_process_route_response_complete(self):
        """Test processing of complete route response"""
        mock_response = {
            'features': [{
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[-9.1393, 38.7223], [-9.1607, 38.7492], [-9.2034, 38.6968]]
                },
                'properties': {
                    'summary': {
                        'distance': 8000,  # 8km
                        'duration': 1800   # 30 minutes
                    },
                    'segments': [{
                        'steps': [
                            {
                                'instruction': 'Head north',
                                'distance': 4000,
                                'duration': 900,
                                'type': 0,
                                'name': 'Rua Augusta'
                            },
                            {
                                'instruction': 'Turn left',
                                'distance': 4000,
                                'duration': 900,
                                'type': 1,
                                'name': 'Avenida da Liberdade'
                            }
                        ]
                    }]
                }
            }]
        }
        
        result = self.service._process_route_response(mock_response, 'wheelchair')
        
        # Check geometry
        self.assertEqual(result['geometry']['type'], 'LineString')
        self.assertEqual(len(result['geometry']['coordinates']), 3)
        
        # Check summary
        self.assertEqual(result['summary']['distance'], 8.0)
        self.assertEqual(result['summary']['duration'], 30.0)
        
        # Check instructions
        self.assertEqual(len(result['instructions']), 2)
        self.assertEqual(result['instructions'][0]['instruction'], 'Head north')
        self.assertEqual(result['instructions'][0]['name'], 'Rua Augusta')
        
        # Check accessibility info for wheelchair profile
        self.assertIn('accessibility', result)
        self.assertIn('score', result['accessibility'])
        
        # Check profile and warnings
        self.assertEqual(result['profile'], 'wheelchair')
        self.assertIn('warnings', result)
    
    def test_process_route_response_empty(self):
        """Test processing of empty route response raises error"""
        empty_responses = [
            {'features': []},
            {'features': [{}]},
            {}
        ]
        
        for response in empty_responses:
            with self.subTest(response=response):
                with self.assertRaises(RoutingError) as context:
                    self.service._process_route_response(response, 'wheelchair')
                self.assertIn("No route found", str(context.exception))
    
    def test_assess_wheelchair_accessibility(self):
        """Test wheelchair accessibility assessment"""
        mock_segments = [
            {
                'distance': 5000,
                'steps': [
                    {'instruction': 'Head north', 'distance': 2500},
                    {'instruction': 'Turn right', 'distance': 2500}
                ],
                'extras': {
                    'steepness': [{'value': 3}],  # 3% incline
                    'surface': [{'value': 'paved'}]
                }
            }
        ]
        
        accessibility_info = self.service._assess_wheelchair_accessibility(mock_segments)
        
        self.assertIn('score', accessibility_info)
        self.assertIn('max_incline', accessibility_info)
        self.assertIn('surface_warnings', accessibility_info)
        self.assertIn('accessible_distance_km', accessibility_info)
        self.assertIn('total_distance_km', accessibility_info)
        
        # Check data types and ranges
        self.assertIsInstance(accessibility_info['score'], float)
        self.assertGreaterEqual(accessibility_info['score'], 0)
        self.assertLessEqual(accessibility_info['score'], 100)
        self.assertEqual(accessibility_info['max_incline'], 3)
    
    def test_extract_warnings(self):
        """Test warning extraction from route segments"""
        mock_segments = [
            {
                'steps': [
                    {'instruction': 'Take the stairs to the platform'},
                    {'instruction': 'Head north on steep incline'},
                    {'instruction': 'Construction area ahead'},
                    {'instruction': 'Normal turn right'}
                ]
            }
        ]
        
        warnings = self.service._extract_warnings(mock_segments)
        
        # Check that problematic instructions generate warnings
        warning_text = ' '.join(warnings).lower()
        self.assertIn('stairs', warning_text)
        self.assertIn('steep', warning_text)
        self.assertIn('construction', warning_text)
        
        # Should not have duplicates
        self.assertEqual(len(warnings), len(set(warnings)))
    
    def test_calculate_distance(self):
        """Test distance calculation using Haversine formula"""
        # Distance between Lisbon center and Hospital Santa Maria
        lat1, lon1 = 38.7223, -9.1393
        lat2, lon2 = 38.7492, -9.1607
        
        distance = self.service._calculate_distance(lat1, lon1, lat2, lon2)
        
        # Should be approximately 2-3 km
        self.assertGreater(distance, 1.0)
        self.assertLess(distance, 5.0)
        self.assertIsInstance(distance, float)
    
    def test_get_route_cache_key_generation(self):
        """Test cache key generation for routes"""
        coordinates = [[-9.1393, 38.7223], [-9.1607, 38.7492]]
        
        key1 = self.service._get_route_cache_key(coordinates, 'wheelchair', True, 'shortest')
        key2 = self.service._get_route_cache_key(coordinates, 'wheelchair', True, 'shortest')
        key3 = self.service._get_route_cache_key(coordinates, 'driving', True, 'shortest')
        
        # Same parameters should generate same key
        self.assertEqual(key1, key2)
        
        # Different profile should generate different key
        self.assertNotEqual(key1, key3)
        
        # Keys should contain relevant information
        self.assertIn('wheelchair', key1)
        self.assertIn('driving', key3)
    
    def test_get_fallback_route(self):
        """Test fallback route generation when API is unavailable"""
        coordinates = [[-9.1393, 38.7223], [-9.1607, 38.7492]]
        
        fallback_route = self.service._get_fallback_route(coordinates)
        
        self.assertIsNotNone(fallback_route)
        self.assertEqual(fallback_route['profile'], 'fallback')
        
        # Check required fields are present
        self.assertIn('geometry', fallback_route)
        self.assertIn('summary', fallback_route)
        self.assertIn('instructions', fallback_route)
        self.assertIn('accessibility', fallback_route)
        self.assertIn('warnings', fallback_route)
        
        # Check that fallback warning is present
        self.assertIn('fallback method', fallback_route['warnings'][0])
        
        # Check accessibility score is conservative
        self.assertLessEqual(fallback_route['accessibility']['score'], 80.0)
    
    def test_get_multiple_routes(self):
        """Test getting multiple route alternatives"""
        with patch.object(self.service, 'get_wheelchair_route') as mock_wheelchair:
            # Mock different routes for different preferences
            mock_wheelchair.side_effect = [
                {'summary': {'distance': 5.0}, 'profile': 'wheelchair'},  # recommended
                {'summary': {'distance': 4.5}, 'profile': 'wheelchair'},  # fastest
                {'summary': {'distance': 4.8}, 'profile': 'wheelchair'},  # shortest
            ]
            
            routes = self.service.get_multiple_routes(self.valid_coordinates, alternatives=3)
            
            self.assertIsInstance(routes, list)
            self.assertLessEqual(len(routes), 3)
            
            # Check that routes have alternative numbers and descriptions
            for i, route in enumerate(routes):
                self.assertIn('alternative', route)
                self.assertIn('description', route)
                self.assertEqual(route['alternative'], i)
    
    def test_get_multiple_routes_error_handling(self):
        """Test multiple routes with errors returns partial results"""
        with patch.object(self.service, 'get_wheelchair_route') as mock_wheelchair:
            # First call succeeds, subsequent calls fail
            mock_wheelchair.side_effect = [
                {'summary': {'distance': 5.0}, 'profile': 'wheelchair'},
                RoutingError("API Error"),
                RoutingError("API Error")
            ]
            
            routes = self.service.get_multiple_routes(self.valid_coordinates, alternatives=3)
            
            # Should return at least the successful route
            self.assertGreaterEqual(len(routes), 1)
            self.assertEqual(routes[0]['summary']['distance'], 5.0)
    
    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_service_with_different_cache_backend(self):
        """Test service works with different cache backends"""
        service = RoutingService()
        
        # Test basic routing still works with different cache
        result = service.get_wheelchair_route(self.valid_coordinates)
        self.assertIsNotNone(result)
        self.assertIn('summary', result)


class RoutingServiceIntegrationTest(TestCase):
    """Integration tests that may require external services (if configured)"""
    
    def setUp(self):
        self.service = RoutingService()
        self.valid_coordinates = [[-9.1393, 38.7223], [-9.1607, 38.7492]]
    
    @unittest.skipUnless(
        hasattr(__import__('django.conf').conf.settings, 'OPENROUTESERVICE_API_KEY'),
        "OpenRouteService API key not configured"
    )
    def test_real_ors_integration(self):
        """Test with real OpenRouteService API if configured (integration test)"""
        # This test would run if OPENROUTESERVICE_API_KEY is properly configured
        # It's skipped by default to avoid external dependencies in unit tests
        try:
            result = self.service.get_wheelchair_route(self.valid_coordinates)
            if result and result['profile'] != 'fallback':
                self.assertIn('summary', result)
                self.assertGreater(result['summary']['distance'], 0)
                self.assertGreater(result['summary']['duration'], 0)
        except RoutingError:
            # Expected if API has issues or rate limits
            pass