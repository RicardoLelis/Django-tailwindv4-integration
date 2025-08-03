import json
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, Mock
from django.core.cache import cache

class PublicGeocodingViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()
    
    def test_public_geocoding_suggestions_success(self):
        """Test successful address suggestions via public endpoint"""
        with patch('app.services.geocoding_service.GeocodingService.get_address_suggestions') as mock_service:
            mock_service.return_value = [
                {
                    'display_name': 'Hospital São José, Lisboa',
                    'lat': 38.7223,
                    'lng': -9.1393,
                    'formatted': 'Hospital São José, Lisboa',
                    'type': 'hospital'
                }
            ]
            
            response = self.client.post(
                '/api/geocoding/public/suggestions/',
                data=json.dumps({'query': 'hospital', 'limit': 5}),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['display_name'], 'Hospital São José, Lisboa')
            mock_service.assert_called_once_with('hospital', 5)
    
    def test_public_geocoding_suggestions_empty_query(self):
        """Test empty query returns error"""
        response = self.client.post(
            '/api/geocoding/public/suggestions/',
            data=json.dumps({'query': ''}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
    
    def test_public_geocoding_suggestions_short_query(self):
        """Test very short query returns empty list"""
        response = self.client.post(
            '/api/geocoding/public/suggestions/',
            data=json.dumps({'query': 'a'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])
    
    def test_public_reverse_geocode_success(self):
        """Test successful reverse geocoding"""
        with patch('app.services.geocoding_service.GeocodingService.reverse_geocode') as mock_service:
            mock_service.return_value = {
                'display_name': 'Rua José António Serrano, Lisboa',
                'formatted': 'Rua José António Serrano, Lisboa'
            }
            
            response = self.client.post(
                '/api/geocoding/public/reverse/',
                data=json.dumps({'lat': 38.7223, 'lng': -9.1393}),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['display_name'], 'Rua José António Serrano, Lisboa')
            mock_service.assert_called_once_with(38.7223, -9.1393)
    
    def test_public_reverse_geocode_missing_coordinates(self):
        """Test reverse geocoding with missing coordinates"""
        response = self.client.post(
            '/api/geocoding/public/reverse/',
            data=json.dumps({'lat': 38.7223}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
    
    def test_public_service_area(self):
        """Test service area endpoint"""
        response = self.client.get('/api/geocoding/public/service-area/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('bounds', data)
        self.assertIn('center', data)
        self.assertIn('name', data)
    
    def test_rate_limiting_applied(self):
        """Test rate limiting decorators are applied"""
        from app.api.geocoding_public_views import public_geocoding_suggestions
        
        # Check if the view has rate limiting decorators
        self.assertTrue(hasattr(public_geocoding_suggestions, '__wrapped__'))
    
    def test_geocoding_service_error_handling(self):
        """Test error handling when geocoding service fails"""
        with patch('app.services.geocoding_service.GeocodingService.get_address_suggestions') as mock_service:
            mock_service.side_effect = Exception('Service error')
            
            response = self.client.post(
                '/api/geocoding/public/suggestions/',
                data=json.dumps({'query': 'test'}),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 503)
            data = response.json()
            self.assertEqual(data['error'], 'Service unavailable')
    
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON input"""
        response = self.client.post(
            '/api/geocoding/public/suggestions/',
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'Invalid JSON')
    
    def test_limit_parameter_validation(self):
        """Test limit parameter is properly validated and capped"""
        with patch('app.services.geocoding_service.GeocodingService.get_address_suggestions') as mock_service:
            mock_service.return_value = []
            
            # Test limit is capped at 10
            response = self.client.post(
                '/api/geocoding/public/suggestions/',
                data=json.dumps({'query': 'test', 'limit': 20}),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            mock_service.assert_called_once_with('test', 10)  # Should be capped at 10