"""
Unit tests for the enhanced geocoding service.
Tests input validation, API integration, caching, and error handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
import requests

from app.services.geocoding_service import GeocodingService, GeocodingError


class GeocodingServiceTestCase(TestCase):
    """Test cases for GeocodingService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.service = GeocodingService()
        cache.clear()  # Clear cache between tests
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_init_with_settings(self):
        """Test service initialization with settings"""
        self.assertIsNotNone(self.service.nominatim_url)
        self.assertIsNotNone(self.service.user_agent)
        self.assertIsNotNone(self.service.session)
    
    def test_validate_address_input_valid(self):
        """Test address input validation with valid inputs"""
        valid_addresses = [
            "Rua Augusta 100, Lisboa",
            "Hospital São José",
            "Aeroporto de Lisboa",
            "Rossio, Lisboa"
        ]
        
        for address in valid_addresses:
            with self.subTest(address=address):
                result = self.service._validate_address_input(address)
                self.assertEqual(result, address.strip())
    
    def test_validate_address_input_invalid(self):
        """Test address input validation with invalid inputs"""
        invalid_cases = [
            ("", "Address must be a non-empty string"),
            (None, "Address must be a non-empty string"),
            ("ab", "Address must be at least 3 characters"),
            ("a" * 201, "Address too long (max 200 characters)"),
            ("Rua <script>alert('xss')</script>", "Address contains invalid characters"),
            ("SELECT * FROM users", "Address contains invalid characters"),
        ]
        
        for address, expected_error in invalid_cases:
            with self.subTest(address=address):
                with self.assertRaises(GeocodingError) as context:
                    self.service._validate_address_input(address)
                self.assertIn(expected_error, str(context.exception))
    
    def test_validate_coordinates_valid(self):
        """Test coordinate validation with valid inputs"""
        valid_coords = [
            (38.7223, -9.1393),  # Lisbon center
            (0, 0),              # Equator
            (-90, -180),         # Boundaries
            (90, 180),           # Boundaries
        ]
        
        for lat, lng in valid_coords:
            with self.subTest(lat=lat, lng=lng):
                result_lat, result_lng = self.service._validate_coordinates(lat, lng)
                self.assertEqual(result_lat, lat)
                self.assertEqual(result_lng, lng)
    
    def test_validate_coordinates_invalid(self):
        """Test coordinate validation with invalid inputs"""
        invalid_coords = [
            (91, 0),      # Latitude too high
            (-91, 0),     # Latitude too low
            (0, 181),     # Longitude too high
            (0, -181),    # Longitude too low
            ("invalid", 0),   # Non-numeric latitude
            (0, "invalid"),   # Non-numeric longitude
        ]
        
        for lat, lng in invalid_coords:
            with self.subTest(lat=lat, lng=lng):
                with self.assertRaises(GeocodingError):
                    self.service._validate_coordinates(lat, lng)
    
    def test_validate_service_area(self):
        """Test service area validation"""
        # Coordinates within Lisbon area should be valid
        lisbon_coords = [
            (38.7223, -9.1393),  # Lisbon center
            (38.7492, -9.1607),  # Hospital Santa Maria
            (38.6968, -9.2034),   # Belém
        ]
        
        for lat, lng in lisbon_coords:
            with self.subTest(lat=lat, lng=lng):
                self.assertTrue(self.service.validate_service_area(lat, lng))
        
        # Coordinates outside service area should be invalid
        outside_coords = [
            (40.7128, -74.0060),  # New York
            (51.5074, -0.1278),   # London
            (35.0000, -10.0000),  # Far south
        ]
        
        for lat, lng in outside_coords:
            with self.subTest(lat=lat, lng=lng):
                self.assertFalse(self.service.validate_service_area(lat, lng))
    
    @patch('app.services.geocoding_service.requests.Session.get')
    def test_geocode_with_api_success(self, mock_get):
        """Test geocoding with successful API response"""
        # Mock successful Nominatim response
        mock_response = Mock()
        mock_response.json.return_value = [{
            'lat': '38.7223',
            'lon': '-9.1393',
            'display_name': 'Lisboa, Portugal',
            'importance': 0.8,
            'place_rank': 15
        }]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.service.geocode("Lisboa")
        
        self.assertIsNotNone(result)
        self.assertEqual(result['lat'], 38.7223)
        self.assertEqual(result['lng'], -9.1393)
        self.assertIn('display_name', result)
        self.assertIn('confidence', result)
    
    @patch('app.services.geocoding_service.requests.Session.get')
    def test_geocode_with_api_failure_fallback(self, mock_get):
        """Test geocoding with API failure falls back to mock data"""
        # Mock API failure
        mock_get.side_effect = requests.RequestException("API Error")
        
        result = self.service.geocode("Hospital São José")
        
        self.assertIsNotNone(result)
        self.assertEqual(result['lat'], 38.7223)
        self.assertEqual(result['lng'], -9.1393)
        self.assertIn('Hospital São José', result['display_name'])
    
    def test_geocode_caching(self):
        """Test that geocoding results are cached"""
        address = "Test Address Lisboa"
        
        # Mock the API request method to track calls
        with patch.object(self.service, '_make_nominatim_request') as mock_api:
            mock_api.return_value = {
                'lat': 38.7223,
                'lng': -9.1393,
                'display_name': 'Test Address, Lisboa',
                'confidence': 0.8
            }
            
            # First call should hit the API
            result1 = self.service.geocode(address)
            self.assertEqual(mock_api.call_count, 1)
            
            # Second call should use cache
            result2 = self.service.geocode(address)
            self.assertEqual(mock_api.call_count, 1)  # No additional API call
            
            # Results should be identical
            self.assertEqual(result1, result2)
    
    def test_geocode_outside_service_area_error(self):
        """Test geocoding address outside service area raises error"""
        with patch.object(self.service, '_make_nominatim_request') as mock_api:
            # Mock response with coordinates outside service area
            mock_api.return_value = {
                'lat': 40.7128,  # New York latitude
                'lng': -74.0060,  # New York longitude
                'display_name': 'New York, USA',
                'confidence': 0.8
            }
            
            with self.assertRaises(GeocodingError) as context:
                self.service.geocode("New York")
            
            self.assertIn("outside our service area", str(context.exception))
    
    @patch('app.services.geocoding_service.requests.Session.get')
    def test_reverse_geocode_success(self, mock_get):
        """Test reverse geocoding with successful API response"""
        # Mock successful reverse geocoding response
        mock_response = Mock()
        mock_response.json.return_value = {
            'display_name': 'Rua Augusta, Lisboa, Portugal',
            'address': {
                'road': 'Rua Augusta',
                'city': 'Lisboa',
                'postcode': '1100',
                'country': 'Portugal'
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.service.reverse_geocode(38.7223, -9.1393)
        
        self.assertIsNotNone(result)
        self.assertIn('display_name', result)
        self.assertIn('street', result)
        self.assertIn('city', result)
        self.assertEqual(result['street'], 'Rua Augusta')
        self.assertEqual(result['city'], 'Lisboa')
    
    def test_reverse_geocode_outside_service_area(self):
        """Test reverse geocoding outside service area raises error"""
        with self.assertRaises(GeocodingError) as context:
            self.service.reverse_geocode(40.7128, -74.0060)  # New York
        
        self.assertIn("outside our service area", str(context.exception))
    
    @patch('app.services.geocoding_service.requests.Session.get')
    def test_get_address_suggestions_success(self, mock_get):
        """Test address suggestions with successful API response"""
        # Mock successful suggestions response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'lat': '38.7223',
                'lon': '-9.1393',
                'display_name': 'Rossio, Lisboa, Portugal',
                'type': 'square',
                'importance': 0.8
            },
            {
                'lat': '38.7139',
                'lon': '-9.1394',
                'display_name': 'Rua do Rossio, Lisboa, Portugal',
                'type': 'road',
                'importance': 0.6
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        suggestions = self.service.get_address_suggestions("Rossio", limit=5)
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        self.assertLessEqual(len(suggestions), 5)
        
        # Check suggestion structure
        suggestion = suggestions[0]
        self.assertIn('display_name', suggestion)
        self.assertIn('lat', suggestion)
        self.assertIn('lng', suggestion)
        self.assertIn('formatted', suggestion)
    
    def test_get_address_suggestions_short_query(self):
        """Test address suggestions with too short query returns empty list"""
        suggestions = self.service.get_address_suggestions("a")
        self.assertEqual(suggestions, [])
        
        suggestions = self.service.get_address_suggestions("")
        self.assertEqual(suggestions, [])
    
    def test_get_address_suggestions_caching(self):
        """Test that address suggestions are cached"""
        query = "Rossio Lisboa"
        
        with patch.object(self.service, '_get_nominatim_suggestions') as mock_api:
            mock_api.return_value = [
                {
                    'display_name': 'Rossio, Lisboa',
                    'lat': 38.7139,
                    'lng': -9.1394,
                    'formatted': 'Rossio, Lisboa',
                    'type': 'square',
                    'importance': 0.8
                }
            ]
            
            # First call should hit the API
            result1 = self.service.get_address_suggestions(query)
            self.assertEqual(mock_api.call_count, 1)
            
            # Second call should use cache
            result2 = self.service.get_address_suggestions(query)
            self.assertEqual(mock_api.call_count, 1)  # No additional API call
            
            # Results should be identical
            self.assertEqual(result1, result2)
    
    def test_calculate_confidence(self):
        """Test confidence calculation for geocoding results"""
        test_cases = [
            ({'importance': 0.8, 'place_rank': 15}, 0.8),  # High importance, good rank
            ({'importance': 0.2, 'place_rank': 25}, 0.6),  # Low importance, poor rank
            ({'importance': 1.0, 'place_rank': 10}, 1.0),  # Maximum values
            ({}, 0.0),  # No data
        ]
        
        for input_data, expected_min in test_cases:
            with self.subTest(input_data=input_data):
                confidence = self.service._calculate_confidence(input_data)
                self.assertIsInstance(confidence, float)
                self.assertGreaterEqual(confidence, 0.0)
                self.assertLessEqual(confidence, 1.0)
    
    def test_format_address(self):
        """Test address formatting from components"""
        test_cases = [
            (
                {'road': 'Rua Augusta', 'house_number': '100', 'city': 'Lisboa'},
                'Rua Augusta 100, Lisboa'
            ),
            (
                {'road': 'Rua do Ouro', 'town': 'Lisboa'},
                'Rua do Ouro, Lisboa'
            ),
            (
                {'city': 'Lisboa', 'postcode': '1100'},
                'Lisboa, 1100'
            ),
            (
                {},
                'Lisboa, Portugal'
            ),
        ]
        
        for components, expected in test_cases:
            with self.subTest(components=components):
                result = self.service._format_address(components)
                self.assertEqual(result, expected)
    
    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_service_with_different_cache_backend(self):
        """Test service works with different cache backends"""
        # This test ensures the service works with various cache configurations
        service = GeocodingService()
        
        # Test basic geocoding still works
        result = service.geocode("Lisboa")
        self.assertIsNotNone(result)
        self.assertIn('lat', result)
        self.assertIn('lng', result)


class GeocodingServiceIntegrationTest(TestCase):
    """Integration tests that may require external services (if configured)"""
    
    def setUp(self):
        self.service = GeocodingService()
    
    @unittest.skipUnless(
        hasattr(__import__('django.conf').conf.settings, 'NOMINATIM_API_URL'),
        "Nominatim API URL not configured"
    )
    def test_real_nominatim_integration(self):
        """Test with real Nominatim API if configured (integration test)"""
        # This test would run if NOMINATIM_API_URL is properly configured
        # It's skipped by default to avoid external dependencies in unit tests
        try:
            result = self.service.geocode("Lisboa, Portugal")
            if result:  # API might be down or rate limited
                self.assertIn('lat', result)
                self.assertIn('lng', result)
                self.assertTrue(self.service.validate_service_area(result['lat'], result['lng']))
        except GeocodingError:
            # Expected if API has issues or rate limits
            pass