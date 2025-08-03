# Phase 1: Core Infrastructure Implementation Plan

## Overview

This document provides a detailed implementation plan for Phase 1 of the wheelchair ride-sharing MVP, focusing on mapping infrastructure, external API integrations, and environment configuration. The implementation prioritizes security, efficiency, and scalability while maintaining code quality through comprehensive testing.

## Architecture Design

### System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
├─────────────────────────────────────────────────────────────┤
│  MapLibre GL JS  │  Protomaps  │  Address Autocomplete      │
├─────────────────────────────────────────────────────────────┤
│                    API Gateway Layer                         │
├─────────────────────────────────────────────────────────────┤
│  Django REST Framework  │  Rate Limiting  │  Auth           │
├─────────────────────────────────────────────────────────────┤
│                   Service Layer                              │
├──────────────────┬────────────────┬────────────────────────┤
│ Enhanced         │ Routing        │ Map Tile               │
│ Geocoding        │ Service        │ Service                │
│ Service          │                │                        │
├──────────────────┴────────────────┴────────────────────────┤
│                    Cache Layer (Redis)                       │
├─────────────────────────────────────────────────────────────┤
│              External Services                               │
├──────────────────┬────────────────┬────────────────────────┤
│ Nominatim API    │ OpenRouteService│ Cloudflare R2         │
└──────────────────┴────────────────┴────────────────────────┘
```

## 1. Environment Configuration

### 1.1 Settings Structure

```python
# project/settings/base.py
import os
from pathlib import Path
from decouple import config, Csv

class Settings:
    """Base settings with security-first approach"""
    
    # Security
    SECRET_KEY = config('SECRET_KEY')
    DEBUG = False
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
    
    # API Keys (encrypted at rest)
    NOMINATIM_API_URL = config('NOMINATIM_API_URL', default='https://nominatim.openstreetmap.org')
    NOMINATIM_USER_AGENT = config('NOMINATIM_USER_AGENT', default='WheelchairRideShare/1.0')
    
    OPENROUTESERVICE_API_KEY = config('OPENROUTESERVICE_API_KEY')
    OPENROUTESERVICE_API_URL = config('OPENROUTESERVICE_API_URL', default='https://api.openrouteservice.org')
    
    # Cloudflare R2
    R2_ACCOUNT_ID = config('R2_ACCOUNT_ID')
    R2_ACCESS_KEY_ID = config('R2_ACCESS_KEY_ID')
    R2_SECRET_ACCESS_KEY = config('R2_SECRET_ACCESS_KEY')
    R2_BUCKET_NAME = config('R2_BUCKET_NAME', default='wheelchair-maps')
    R2_PUBLIC_URL = config('R2_PUBLIC_URL')
    
    # Redis Configuration
    REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')
    
    # Rate Limiting
    RATELIMIT_ENABLE = True
    RATELIMIT_USE_CACHE = 'default'
    RATELIMIT_VIEW = '100/h'  # Default rate limit
    
    # API Rate Limits
    GEOCODING_RATE_LIMIT = config('GEOCODING_RATE_LIMIT', default='60/m')
    ROUTING_RATE_LIMIT = config('ROUTING_RATE_LIMIT', default='100/m')
    
    # Service Area (Lisbon District)
    SERVICE_AREA_BOUNDS = {
        'north': 38.8500,
        'south': 38.6000,
        'east': -9.0000,
        'west': -9.5000,
    }
    
    # Cache TTLs
    CACHE_TTL = {
        'geocoding': 86400,  # 24 hours
        'routing': 3600,     # 1 hour
        'tiles': 604800,     # 7 days
    }

# project/settings/development.py
from .base import Settings

class DevelopmentSettings(Settings):
    DEBUG = True
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
    
    # Development API endpoints (with rate limiting)
    NOMINATIM_API_URL = 'http://localhost:8080'  # Local Nominatim instance
    
    # Relaxed rate limits for development
    GEOCODING_RATE_LIMIT = '1000/m'
    ROUTING_RATE_LIMIT = '1000/m'

# project/settings/production.py
from .base import Settings

class ProductionSettings(Settings):
    # Security headers
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Strict rate limits
    GEOCODING_RATE_LIMIT = '30/m'
    ROUTING_RATE_LIMIT = '50/m'
```

### 1.2 Environment Variables Template

```bash
# .env.template
# Security
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://user:password@localhost:5432/wheelchair_rides

# Redis
REDIS_URL=redis://localhost:6379/0

# External APIs
NOMINATIM_API_URL=https://nominatim.openstreetmap.org
NOMINATIM_USER_AGENT=WheelchairRideShare/1.0

OPENROUTESERVICE_API_KEY=your-api-key-here
OPENROUTESERVICE_API_URL=https://api.openrouteservice.org

# Cloudflare R2
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=wheelchair-maps
R2_PUBLIC_URL=https://maps.yourdomain.com

# Rate Limiting
GEOCODING_RATE_LIMIT=60/m
ROUTING_RATE_LIMIT=100/m
```

## 2. Enhanced Geocoding Service

### 2.1 Service Implementation

```python
# project/app/services/geocoding_service.py
import logging
import requests
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import hashlib
import json
from functools import wraps
import time

logger = logging.getLogger(__name__)

def rate_limit(key_prefix: str, max_calls: int, period: int):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Create unique key for rate limiting
            key = f"rate_limit:{key_prefix}:{self.__class__.__name__}"
            
            # Get current count
            current_count = cache.get(key, 0)
            
            if current_count >= max_calls:
                raise RateLimitExceeded(f"Rate limit exceeded for {key_prefix}")
            
            # Increment counter
            cache.set(key, current_count + 1, period)
            
            return func(self, *args, **kwargs)
        return wrapper
    return decorator

class RateLimitExceeded(Exception):
    """Raised when API rate limit is exceeded"""
    pass

class GeocodingService:
    """
    Enhanced geocoding service with security and efficiency features:
    - Rate limiting
    - Caching with encryption
    - Input validation
    - Error handling with fallbacks
    """
    
    def __init__(self):
        self.nominatim_url = settings.NOMINATIM_API_URL
        self.user_agent = settings.NOMINATIM_USER_AGENT
        self.cache_ttl = settings.CACHE_TTL['geocoding']
        self.service_bounds = settings.SERVICE_AREA_BOUNDS
        
    def _get_cache_key(self, operation: str, data: str) -> str:
        """Generate secure cache key"""
        hash_input = f"{operation}:{data}".encode('utf-8')
        return f"geocoding:{hashlib.sha256(hash_input).hexdigest()}"
    
    def _validate_address(self, address: str) -> str:
        """Validate and sanitize address input"""
        if not address or not isinstance(address, str):
            raise ValueError("Invalid address format")
        
        # Remove potentially harmful characters
        sanitized = address.strip()
        
        # Check length limits
        if len(sanitized) < 3 or len(sanitized) > 500:
            raise ValueError("Address length must be between 3 and 500 characters")
        
        # Basic SQL injection prevention (though we're not using SQL here)
        dangerous_patterns = ['--', ';', '/*', '*/', 'xp_', 'sp_']
        for pattern in dangerous_patterns:
            if pattern in sanitized.lower():
                raise ValueError("Invalid characters in address")
        
        return sanitized
    
    def _is_within_service_area(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within service area"""
        return (
            self.service_bounds['south'] <= lat <= self.service_bounds['north'] and
            self.service_bounds['west'] <= lon <= self.service_bounds['east']
        )
    
    @rate_limit('geocoding', 60, 60)  # 60 calls per minute
    def geocode(self, address: str, country: str = 'Portugal') -> Optional[Dict[str, float]]:
        """
        Geocode address with caching and validation
        
        Args:
            address: Address to geocode
            country: Country to limit search (default: Portugal)
            
        Returns:
            Dict with 'lat', 'lon', 'display_name' or None
        """
        try:
            # Validate input
            address = self._validate_address(address)
            
            # Check cache
            cache_key = self._get_cache_key('geocode', f"{address}:{country}")
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Geocoding cache hit for: {address}")
                return cached_result
            
            # Build request
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'pt',  # Limit to Portugal
                'bounded': 1,
                'viewbox': f"{self.service_bounds['west']},{self.service_bounds['south']},"
                          f"{self.service_bounds['east']},{self.service_bounds['north']}"
            }
            
            headers = {
                'User-Agent': self.user_agent,
                'Accept-Language': 'pt,en'
            }
            
            # Make request with timeout
            response = requests.get(
                f"{self.nominatim_url}/search",
                params=params,
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            if not data:
                logger.warning(f"No results found for address: {address}")
                return None
            
            # Extract first result
            result = data[0]
            lat = float(result['lat'])
            lon = float(result['lon'])
            
            # Validate location is within service area
            if not self._is_within_service_area(lat, lon):
                logger.warning(f"Address outside service area: {address}")
                return None
            
            geocoded = {
                'lat': lat,
                'lon': lon,
                'display_name': result.get('display_name', address),
                'place_id': result.get('place_id'),
                'confidence': float(result.get('importance', 0.5))
            }
            
            # Cache result
            cache.set(cache_key, geocoded, self.cache_ttl)
            
            logger.info(f"Successfully geocoded: {address}")
            return geocoded
            
        except requests.RequestException as e:
            logger.error(f"Geocoding API error: {e}")
            # Fallback to cached approximate location if available
            return self._get_fallback_location(address)
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None
    
    @rate_limit('geocoding', 60, 60)
    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Reverse geocode coordinates to address
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Address string or None
        """
        try:
            # Validate coordinates
            if not self._is_within_service_area(lat, lon):
                raise ValueError("Coordinates outside service area")
            
            # Check cache
            cache_key = self._get_cache_key('reverse', f"{lat:.6f},{lon:.6f}")
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'zoom': 18,  # Street level detail
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': self.user_agent,
                'Accept-Language': 'pt,en'
            }
            
            response = requests.get(
                f"{self.nominatim_url}/reverse",
                params=params,
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Build address from components
            addr_parts = []
            addr = data.get('address', {})
            
            for key in ['road', 'house_number', 'neighbourhood', 'suburb', 'city']:
                if key in addr:
                    addr_parts.append(addr[key])
            
            address = ', '.join(addr_parts) if addr_parts else data.get('display_name', '')
            
            # Cache result
            if address:
                cache.set(cache_key, address, self.cache_ttl)
            
            return address
            
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return None
    
    def search_nearby(
        self, 
        query: str, 
        lat: float, 
        lon: float, 
        radius_m: int = 5000,
        amenity_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for nearby places
        
        Args:
            query: Search query
            lat: Center latitude
            lon: Center longitude
            radius_m: Search radius in meters
            amenity_type: OSM amenity type (e.g., 'hospital', 'clinic')
            
        Returns:
            List of nearby places
        """
        try:
            # Validate inputs
            if not self._is_within_service_area(lat, lon):
                return []
            
            cache_key = self._get_cache_key(
                'nearby', 
                f"{query}:{lat:.4f},{lon:.4f}:{radius_m}:{amenity_type}"
            )
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            # Calculate bounding box
            lat_delta = radius_m / 111000.0  # Rough conversion
            lon_delta = radius_m / (111000.0 * abs(math.cos(math.radians(lat))))
            
            params = {
                'q': query,
                'format': 'json',
                'limit': 10,
                'bounded': 1,
                'viewbox': f"{lon-lon_delta},{lat-lat_delta},{lon+lon_delta},{lat+lat_delta}"
            }
            
            if amenity_type:
                params['amenity'] = amenity_type
            
            headers = {
                'User-Agent': self.user_agent,
                'Accept-Language': 'pt,en'
            }
            
            response = requests.get(
                f"{self.nominatim_url}/search",
                params=params,
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
            
            results = []
            for item in response.json():
                place_lat = float(item['lat'])
                place_lon = float(item['lon'])
                
                # Calculate distance
                distance = self._calculate_distance(lat, lon, place_lat, place_lon)
                
                if distance <= radius_m:
                    results.append({
                        'name': item.get('display_name', '').split(',')[0],
                        'address': item.get('display_name', ''),
                        'lat': place_lat,
                        'lon': place_lon,
                        'distance_m': int(distance),
                        'type': item.get('type', 'unknown'),
                        'place_id': item.get('place_id')
                    })
            
            # Sort by distance
            results.sort(key=lambda x: x['distance_m'])
            
            # Cache results
            cache.set(cache_key, results, self.cache_ttl // 2)  # Shorter TTL for searches
            
            return results
            
        except Exception as e:
            logger.error(f"Nearby search error: {e}")
            return []
    
    def get_address_suggestions(
        self, 
        partial: str, 
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        Get address autocomplete suggestions
        
        Args:
            partial: Partial address string
            limit: Maximum number of suggestions
            
        Returns:
            List of suggestions with 'address' and 'place_id'
        """
        try:
            # Validate input
            partial = self._validate_address(partial)
            
            if len(partial) < 3:
                return []
            
            # Use lighter cache for autocomplete
            cache_key = self._get_cache_key('suggest', partial[:10])
            cached_result = cache.get(cache_key)
            if cached_result:
                # Filter cached results based on current input
                return [s for s in cached_result if partial.lower() in s['address'].lower()][:limit]
            
            params = {
                'q': partial,
                'format': 'json',
                'limit': limit * 2,  # Get more to filter
                'countrycodes': 'pt',
                'bounded': 1,
                'viewbox': f"{self.service_bounds['west']},{self.service_bounds['south']},"
                          f"{self.service_bounds['east']},{self.service_bounds['north']}"
            }
            
            headers = {
                'User-Agent': self.user_agent,
                'Accept-Language': 'pt,en'
            }
            
            response = requests.get(
                f"{self.nominatim_url}/search",
                params=params,
                headers=headers,
                timeout=3  # Shorter timeout for autocomplete
            )
            response.raise_for_status()
            
            suggestions = []
            for item in response.json():
                lat = float(item['lat'])
                lon = float(item['lon'])
                
                # Only include results within service area
                if self._is_within_service_area(lat, lon):
                    suggestions.append({
                        'address': item.get('display_name', ''),
                        'place_id': item.get('place_id', ''),
                        'lat': lat,
                        'lon': lon
                    })
            
            # Cache for short period
            cache.set(cache_key, suggestions[:limit*2], 300)  # 5 minutes
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Address suggestion error: {e}")
            return []
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in meters using Haversine formula"""
        import math
        
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (
            math.sin(delta_lat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) *
            math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _get_fallback_location(self, address: str) -> Optional[Dict[str, float]]:
        """Get approximate location from fallback data"""
        # Common Lisbon landmarks as fallback
        fallbacks = {
            'hospital': {'lat': 38.7223, 'lon': -9.1393, 'name': 'Hospital São José'},
            'airport': {'lat': 38.7756, 'lon': -9.1354, 'name': 'Aeroporto de Lisboa'},
            'center': {'lat': 38.7223, 'lon': -9.1393, 'name': 'Lisboa Centro'},
        }
        
        address_lower = address.lower()
        for key, location in fallbacks.items():
            if key in address_lower:
                return {
                    'lat': location['lat'],
                    'lon': location['lon'],
                    'display_name': location['name'],
                    'confidence': 0.3  # Low confidence for fallback
                }
        
        return None
```

### 2.2 Unit Tests for Geocoding Service

```python
# project/app/tests/test_geocoding_service.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.core.cache import cache
from decimal import Decimal
import requests

from app.services.geocoding_service import GeocodingService, RateLimitExceeded


class TestGeocodingService(TestCase):
    """Comprehensive tests for geocoding service"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = GeocodingService()
        cache.clear()
        
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_address_validation(self):
        """Test address validation and sanitization"""
        # Valid addresses
        valid_addresses = [
            "Rua do Carmo 10, Lisboa",
            "Hospital São José",
            "Aeroporto de Lisboa"
        ]
        
        for address in valid_addresses:
            result = self.service._validate_address(address)
            self.assertIsNotNone(result)
        
        # Invalid addresses
        invalid_addresses = [
            "",  # Empty
            "ab",  # Too short
            "a" * 501,  # Too long
            "test; DROP TABLE users;--",  # SQL injection attempt
            "test /* comment */",  # SQL comment
        ]
        
        for address in invalid_addresses:
            with self.assertRaises(ValueError):
                self.service._validate_address(address)
    
    def test_service_area_validation(self):
        """Test service area boundary checking"""
        # Inside service area (Lisbon)
        self.assertTrue(self.service._is_within_service_area(38.7223, -9.1393))
        
        # Outside service area
        self.assertFalse(self.service._is_within_service_area(40.0, -8.0))  # Porto
        self.assertFalse(self.service._is_within_service_area(37.0, -8.0))  # Algarve
    
    @patch('requests.get')
    def test_geocode_success(self, mock_get):
        """Test successful geocoding"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [{
            'lat': '38.7223',
            'lon': '-9.1393',
            'display_name': 'Hospital São José, Lisboa',
            'place_id': '12345',
            'importance': 0.8
        }]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test geocoding
        result = self.service.geocode("Hospital São José")
        
        self.assertIsNotNone(result)
        self.assertEqual(result['lat'], 38.7223)
        self.assertEqual(result['lon'], -9.1393)
        self.assertIn('Hospital', result['display_name'])
        
        # Verify caching
        cache_key = self.service._get_cache_key('geocode', 'Hospital São José:Portugal')
        cached = cache.get(cache_key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached['lat'], result['lat'])
    
    @patch('requests.get')
    def test_geocode_cache_hit(self, mock_get):
        """Test geocoding cache functionality"""
        # Pre-populate cache
        test_result = {
            'lat': 38.7223,
            'lon': -9.1393,
            'display_name': 'Cached Location',
            'confidence': 0.9
        }
        cache_key = self.service._get_cache_key('geocode', 'Test Location:Portugal')
        cache.set(cache_key, test_result, 3600)
        
        # Geocode should use cache
        result = self.service.geocode("Test Location")
        
        # Verify no API call was made
        mock_get.assert_not_called()
        
        # Verify cached result returned
        self.assertEqual(result['display_name'], 'Cached Location')
    
    @patch('requests.get')
    def test_geocode_outside_service_area(self, mock_get):
        """Test geocoding location outside service area"""
        # Mock response for location outside Lisbon
        mock_response = MagicMock()
        mock_response.json.return_value = [{
            'lat': '41.1579',
            'lon': '-8.6291',
            'display_name': 'Porto, Portugal'
        }]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Should return None for outside service area
        result = self.service.geocode("Porto")
        self.assertIsNone(result)
    
    @patch('requests.get')
    def test_geocode_api_error(self, mock_get):
        """Test geocoding with API error"""
        # Mock API error
        mock_get.side_effect = requests.RequestException("API Error")
        
        # Should handle error gracefully
        result = self.service.geocode("Test Location")
        self.assertIsNone(result)
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # Mock the geocode method to avoid actual API calls
        with patch.object(self.service, 'geocode') as mock_geocode:
            mock_geocode.return_value = {'lat': 38.7, 'lon': -9.1}
            
            # Clear rate limit cache
            rate_limit_key = "rate_limit:geocoding:GeocodingService"
            cache.delete(rate_limit_key)
            
            # Make calls up to the limit (60 per minute)
            for i in range(60):
                result = self.service.geocode(f"Address {i}")
                self.assertIsNotNone(result)
            
            # 61st call should raise rate limit error
            with self.assertRaises(RateLimitExceeded):
                self.service.geocode("Address 61")
    
    @patch('requests.get')
    def test_reverse_geocode_success(self, mock_get):
        """Test successful reverse geocoding"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'address': {
                'road': 'Rua do Carmo',
                'house_number': '10',
                'neighbourhood': 'Chiado',
                'city': 'Lisboa'
            },
            'display_name': 'Rua do Carmo 10, Chiado, Lisboa'
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test reverse geocoding
        result = self.service.reverse_geocode(38.7223, -9.1393)
        
        self.assertIsNotNone(result)
        self.assertIn('Rua do Carmo', result)
        self.assertIn('Lisboa', result)
    
    @patch('requests.get')
    def test_search_nearby_medical_facilities(self, mock_get):
        """Test searching for nearby medical facilities"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'lat': '38.7223',
                'lon': '-9.1393',
                'display_name': 'Hospital São José, Lisboa',
                'type': 'hospital',
                'place_id': '12345'
            },
            {
                'lat': '38.7250',
                'lon': '-9.1400',
                'display_name': 'Centro de Saúde, Lisboa',
                'type': 'clinic',
                'place_id': '12346'
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Search nearby
        results = self.service.search_nearby(
            'hospital',
            38.7223,
            -9.1393,
            radius_m=5000,
            amenity_type='hospital'
        )
        
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn('distance_m', results[0])
        self.assertLess(results[0]['distance_m'], 5000)
    
    @patch('requests.get')
    def test_address_suggestions(self, mock_get):
        """Test address autocomplete suggestions"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'lat': '38.7223',
                'lon': '-9.1393',
                'display_name': 'Rua do Carmo, Lisboa',
                'place_id': '12345'
            },
            {
                'lat': '38.7123',
                'lon': '-9.1293',
                'display_name': 'Rua do Carmo 10, Lisboa',
                'place_id': '12346'
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Get suggestions
        suggestions = self.service.get_address_suggestions("Rua do Car")
        
        self.assertIsInstance(suggestions, list)
        self.assertLessEqual(len(suggestions), 5)
        if suggestions:
            self.assertIn('address', suggestions[0])
            self.assertIn('place_id', suggestions[0])
    
    def test_distance_calculation(self):
        """Test Haversine distance calculation"""
        # Test known distance (Rossio to Belém ~7km)
        distance = self.service._calculate_distance(
            38.7139, -9.1394,  # Rossio
            38.6968, -9.2034   # Belém
        )
        
        # Should be approximately 7km (7000m)
        self.assertAlmostEqual(distance, 7000, delta=500)
    
    def test_fallback_location(self):
        """Test fallback location functionality"""
        # Test hospital fallback
        result = self.service._get_fallback_location("Something hospital related")
        self.assertIsNotNone(result)
        self.assertEqual(result['confidence'], 0.3)
        
        # Test no fallback match
        result = self.service._get_fallback_location("Random address")
        self.assertIsNone(result)


@pytest.mark.django_db
class TestGeocodingServiceIntegration(TestCase):
    """Integration tests requiring database"""
    
    def setUp(self):
        self.service = GeocodingService()
    
    @override_settings(
        NOMINATIM_API_URL='https://nominatim.openstreetmap.org',
        SERVICE_AREA_BOUNDS={
            'north': 38.8500,
            'south': 38.6000,
            'east': -9.0000,
            'west': -9.5000,
        }
    )
    def test_real_api_integration(self):
        """Test with real API (should be skipped in CI)"""
        if not pytest.config.getoption("--run-integration"):
            pytest.skip("Skipping integration tests")
        
        # Test real geocoding
        result = self.service.geocode("Praça do Comércio, Lisboa")
        
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['lat'], 38.7076, delta=0.01)
        self.assertAlmostEqual(result['lon'], -9.1365, delta=0.01)
```

## 3. Routing Service Implementation

### 3.1 Service Implementation

```python
# project/app/services/routing_service.py
import logging
import requests
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
import polyline
import hashlib

logger = logging.getLogger(__name__)


class RoutingService:
    """
    Routing service using OpenRouteService API
    Features:
    - Wheelchair-accessible routing
    - Route optimization
    - Turn-by-turn instructions
    - Elevation awareness
    """
    
    def __init__(self):
        self.api_key = settings.OPENROUTESERVICE_API_KEY
        self.api_url = settings.OPENROUTESERVICE_API_URL
        self.cache_ttl = settings.CACHE_TTL['routing']
        
    def _get_cache_key(self, operation: str, data: str) -> str:
        """Generate cache key for routing operations"""
        hash_input = f"{operation}:{data}".encode('utf-8')
        return f"routing:{hashlib.sha256(hash_input).hexdigest()}"
    
    def calculate_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        profile: str = 'wheelchair',
        options: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Calculate route between two points
        
        Args:
            start: (lat, lon) tuple
            end: (lat, lon) tuple
            profile: Routing profile (wheelchair, driving-car)
            options: Additional routing options
            
        Returns:
            Route information including geometry, distance, duration
        """
        try:
            # Create cache key
            cache_key = self._get_cache_key(
                'route',
                f"{start[0]:.5f},{start[1]:.5f}-{end[0]:.5f},{end[1]:.5f}-{profile}"
            )
            
            # Check cache
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("Route cache hit")
                return cached_result
            
            # Prepare request
            coordinates = [
                [start[1], start[0]],  # ORS uses lon,lat
                [end[1], end[0]]
            ]
            
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            }
            
            body = {
                'coordinates': coordinates,
                'profile': profile,
                'elevation': True,
                'instructions': True,
                'units': 'km',
                'language': 'pt',
                'options': options or {
                    'avoid_features': ['ferries', 'steps'],
                    'profile_params': {
                        'restrictions': {
                            'surface_type': 'cobblestone:flattened',
                            'track_type': 'grade1',
                            'smoothness_type': 'good',
                            'maximum_incline': 6
                        }
                    }
                }
            }
            
            # Make request
            response = requests.post(
                f"{self.api_url}/v2/directions/{profile}",
                json=body,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'routes' not in data or not data['routes']:
                logger.warning("No routes found")
                return None
            
            route = data['routes'][0]
            
            # Process route data
            result = {
                'geometry': route['geometry'],  # Encoded polyline
                'distance_km': route['summary']['distance'] / 1000,
                'duration_min': route['summary']['duration'] / 60,
                'elevation_gain': route.get('elevation_gain', 0),
                'elevation_loss': route.get('elevation_loss', 0),
                'bbox': route.get('bbox', []),
                'waypoints': self._extract_waypoints(route),
                'warnings': route.get('warnings', []),
                'segments': self._process_segments(route.get('segments', []))
            }
            
            # Check for accessibility warnings
            if result['elevation_gain'] > 50:
                result['warnings'].append({
                    'code': 'HIGH_ELEVATION_GAIN',
                    'message': 'This route has significant elevation changes'
                })
            
            # Cache result
            cache.set(cache_key, result, self.cache_ttl)
            
            return result
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("Rate limit exceeded for routing API")
                raise RateLimitExceeded("Routing API rate limit exceeded")
            logger.error(f"Routing API HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Routing calculation error: {e}")
            return None
    
    def calculate_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
        profile: str = 'wheelchair'
    ) -> Optional[Dict]:
        """
        Calculate distance/time matrix between multiple points
        
        Args:
            origins: List of (lat, lon) tuples
            destinations: List of (lat, lon) tuples
            profile: Routing profile
            
        Returns:
            Matrix of distances and durations
        """
        try:
            # Convert coordinates
            locations = []
            for lat, lon in origins + destinations:
                locations.append([lon, lat])  # ORS uses lon,lat
            
            sources = list(range(len(origins)))
            destinations_idx = list(range(len(origins), len(origins) + len(destinations)))
            
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            }
            
            body = {
                'locations': locations,
                'sources': sources,
                'destinations': destinations_idx,
                'profile': profile,
                'metrics': ['distance', 'duration'],
                'units': 'km'
            }
            
            response = requests.post(
                f"{self.api_url}/v2/matrix/{profile}",
                json=body,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'distances': data['distances'],  # km
                'durations': data['durations'],  # seconds
                'sources': origins,
                'destinations': destinations
            }
            
        except Exception as e:
            logger.error(f"Matrix calculation error: {e}")
            return None
    
    def decode_polyline(self, encoded: str) -> List[Tuple[float, float]]:
        """Decode polyline to list of coordinates"""
        try:
            # ORS returns polyline5 format
            decoded = polyline.decode(encoded, 5)
            return [(lat, lon) for lon, lat in decoded]  # Convert to lat,lon
        except Exception as e:
            logger.error(f"Polyline decode error: {e}")
            return []
    
    def optimize_waypoints(
        self,
        waypoints: List[Tuple[float, float]],
        start: Optional[Tuple[float, float]] = None,
        end: Optional[Tuple[float, float]] = None,
        profile: str = 'wheelchair'
    ) -> Optional[List[int]]:
        """
        Optimize order of waypoints for shortest route
        
        Args:
            waypoints: List of (lat, lon) tuples to visit
            start: Fixed start point
            end: Fixed end point
            profile: Routing profile
            
        Returns:
            Optimized order as list of indices
        """
        try:
            # Build location list
            locations = []
            if start:
                locations.append([start[1], start[0]])
            
            for lat, lon in waypoints:
                locations.append([lon, lat])
            
            if end:
                locations.append([end[1], end[0]])
            
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            }
            
            # Configure optimization
            jobs = []
            for i, wp in enumerate(waypoints):
                job_index = i
                if start:
                    job_index += 1
                    
                jobs.append({
                    'id': i,
                    'location_index': job_index
                })
            
            vehicles = [{
                'id': 0,
                'profile': profile,
                'start_index': 0 if start else None,
                'end_index': len(locations) - 1 if end else None
            }]
            
            body = {
                'locations': locations,
                'jobs': jobs,
                'vehicles': vehicles
            }
            
            response = requests.post(
                f"{self.api_url}/optimization",
                json=body,
                headers=headers,
                timeout=20
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract optimized order
            if 'routes' in data and data['routes']:
                route = data['routes'][0]
                order = []
                for step in route['steps']:
                    if step['type'] == 'job':
                        order.append(step['job'])
                return order
            
            return None
            
        except Exception as e:
            logger.error(f"Waypoint optimization error: {e}")
            return None
    
    def _extract_waypoints(self, route: Dict) -> List[Dict]:
        """Extract key waypoints from route"""
        waypoints = []
        
        if 'segments' not in route:
            return waypoints
        
        for segment in route['segments']:
            for step in segment.get('steps', []):
                if step['type'] in ['depart', 'arrive', 'turn']:
                    waypoints.append({
                        'location': step.get('location', []),
                        'instruction': step.get('instruction', ''),
                        'type': step['type'],
                        'distance': step.get('distance', 0),
                        'duration': step.get('duration', 0)
                    })
        
        return waypoints
    
    def _process_segments(self, segments: List[Dict]) -> List[Dict]:
        """Process route segments for accessibility info"""
        processed = []
        
        for segment in segments:
            seg_info = {
                'distance': segment.get('distance', 0),
                'duration': segment.get('duration', 0),
                'ascent': segment.get('ascent', 0),
                'descent': segment.get('descent', 0),
                'steps': []
            }
            
            # Check for accessibility issues
            for step in segment.get('steps', []):
                step_info = {
                    'instruction': step.get('instruction', ''),
                    'distance': step.get('distance', 0),
                    'type': step.get('type', ''),
                    'way_points': step.get('way_points', [])
                }
                
                # Flag potential issues
                if 'stairs' in step_info['instruction'].lower():
                    step_info['warning'] = 'Contains stairs'
                elif 'steep' in step_info['instruction'].lower():
                    step_info['warning'] = 'Steep incline'
                
                seg_info['steps'].append(step_info)
            
            processed.append(seg_info)
        
        return processed
```

### 3.2 Unit Tests for Routing Service

```python
# project/app/tests/test_routing_service.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.cache import cache
import json

from app.services.routing_service import RoutingService


class TestRoutingService(TestCase):
    """Tests for routing service"""
    
    def setUp(self):
        self.service = RoutingService()
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    @patch('requests.post')
    def test_calculate_route_success(self, mock_post):
        """Test successful route calculation"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'routes': [{
                'summary': {
                    'distance': 5432.1,
                    'duration': 987.6
                },
                'geometry': 'encodedPolylineString',
                'elevation_gain': 12.5,
                'elevation_loss': 8.3,
                'bbox': [-9.15, 38.70, -9.13, 38.72],
                'segments': [{
                    'distance': 5432.1,
                    'duration': 987.6,
                    'steps': []
                }]
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Calculate route
        result = self.service.calculate_route(
            (38.7223, -9.1393),  # Hospital São José
            (38.7076, -9.1365)   # Praça do Comércio
        )
        
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['distance_km'], 5.432, places=2)
        self.assertAlmostEqual(result['duration_min'], 16.46, places=1)
        self.assertEqual(result['geometry'], 'encodedPolylineString')
        
        # Verify caching
        cached = cache.get(self.service._get_cache_key(
            'route',
            '38.72230,-9.13930-38.70760,-9.13650-wheelchair'
        ))
        self.assertIsNotNone(cached)
    
    @patch('requests.post')
    def test_calculate_route_with_elevation_warning(self, mock_post):
        """Test route with high elevation gain warning"""
        # Mock response with high elevation
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'routes': [{
                'summary': {'distance': 1000, 'duration': 300},
                'geometry': 'encoded',
                'elevation_gain': 75,  # High elevation
                'elevation_loss': 10,
                'segments': []
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.service.calculate_route(
            (38.7223, -9.1393),
            (38.7076, -9.1365)
        )
        
        # Should have elevation warning
        self.assertIn('warnings', result)
        self.assertTrue(any(
            w.get('code') == 'HIGH_ELEVATION_GAIN' 
            for w in result['warnings']
        ))
    
    @patch('requests.post')
    def test_calculate_route_no_routes(self, mock_post):
        """Test when no routes are found"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'routes': []}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.service.calculate_route(
            (38.7223, -9.1393),
            (38.7076, -9.1365)
        )
        
        self.assertIsNone(result)
    
    @patch('requests.post')
    def test_calculate_matrix(self, mock_post):
        """Test distance/time matrix calculation"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'distances': [[0, 5.4], [5.4, 0]],
            'durations': [[0, 600], [600, 0]]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        origins = [(38.7223, -9.1393)]
        destinations = [(38.7076, -9.1365)]
        
        result = self.service.calculate_matrix(origins, destinations)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['distances']), 1)
        self.assertEqual(len(result['distances'][0]), 1)
        self.assertEqual(result['distances'][0][0], 5.4)
    
    def test_decode_polyline(self):
        """Test polyline decoding"""
        # Test with known polyline
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        
        decoded = self.service.decode_polyline(encoded)
        
        self.assertIsInstance(decoded, list)
        self.assertGreater(len(decoded), 0)
        self.assertIsInstance(decoded[0], tuple)
        self.assertEqual(len(decoded[0]), 2)
    
    @patch('requests.post')
    def test_optimize_waypoints(self, mock_post):
        """Test waypoint optimization"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'routes': [{
                'steps': [
                    {'type': 'start'},
                    {'type': 'job', 'job': 2},
                    {'type': 'job', 'job': 0},
                    {'type': 'job', 'job': 1},
                    {'type': 'end'}
                ]
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        waypoints = [
            (38.7223, -9.1393),
            (38.7076, -9.1365),
            (38.7150, -9.1400)
        ]
        
        result = self.service.optimize_waypoints(
            waypoints,
            start=(38.7200, -9.1350),
            end=(38.7100, -9.1450)
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result, [2, 0, 1])  # Optimized order
    
    @patch('requests.post')
    def test_rate_limit_handling(self, mock_post):
        """Test rate limit error handling"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_post.return_value = mock_response
        
        from app.services.geocoding_service import RateLimitExceeded
        
        with self.assertRaises(RateLimitExceeded):
            self.service.calculate_route(
                (38.7223, -9.1393),
                (38.7076, -9.1365)
            )
```

## 4. Map Component Implementation

### 4.1 Frontend Map Service

```javascript
// project/static/js/services/mapService.js

import maplibregl from 'maplibre-gl';
import { Protocol } from 'protomaps';

class MapService {
    constructor() {
        this.map = null;
        this.markers = {
            pickup: null,
            dropoff: null,
            drivers: []
        };
        this.routeLayer = null;
        this.protocol = new Protocol();
        this.geocodingCache = new Map();
    }

    /**
     * Initialize map with Protomaps tiles
     * @param {string} containerId - DOM element ID for map
     * @param {Object} options - Map configuration options
     */
    async initializeMap(containerId, options = {}) {
        try {
            // Add Protomaps protocol
            maplibregl.addProtocol("pmtiles", this.protocol.tile);

            // Default center on Lisbon
            const defaultOptions = {
                container: containerId,
                style: await this.getMapStyle(),
                center: [-9.1393, 38.7223],
                zoom: 12,
                minZoom: 10,
                maxZoom: 18,
                maxBounds: [
                    [-9.5000, 38.6000], // Southwest
                    [-9.0000, 38.8500]  // Northeast
                ]
            };

            this.map = new maplibregl.Map({
                ...defaultOptions,
                ...options
            });

            // Add navigation controls
            this.map.addControl(new maplibregl.NavigationControl(), 'top-right');

            // Add geolocation control
            this.map.addControl(
                new maplibregl.GeolocateControl({
                    positionOptions: {
                        enableHighAccuracy: true
                    },
                    trackUserLocation: true,
                    showUserHeading: true
                }),
                'top-right'
            );

            // Add scale control
            this.map.addControl(
                new maplibregl.ScaleControl({
                    maxWidth: 200,
                    unit: 'metric'
                }),
                'bottom-left'
            );

            // Wait for map to load
            await new Promise((resolve) => {
                this.map.on('load', resolve);
            });

            // Initialize layers
            this.initializeLayers();

            return this.map;

        } catch (error) {
            console.error('Map initialization error:', error);
            throw new Error('Failed to initialize map');
        }
    }

    /**
     * Get map style configuration
     */
    async getMapStyle() {
        // Fetch map configuration from API
        const response = await fetch('/api/maps/config/');
        const config = await response.json();

        return {
            version: 8,
            glyphs: config.glyphs_url,
            sprite: config.sprite_url,
            sources: {
                "lisbon": {
                    type: "vector",
                    tiles: [`pmtiles://${config.tiles_url}/{z}/{x}/{y}`],
                    minzoom: 0,
                    maxzoom: 14
                }
            },
            layers: [
                // Background
                {
                    id: "background",
                    type: "background",
                    paint: {
                        "background-color": "#f8f9fa"
                    }
                },
                // Water
                {
                    id: "water",
                    type: "fill",
                    source: "lisbon",
                    "source-layer": "water",
                    paint: {
                        "fill-color": "#a0c4e8"
                    }
                },
                // Parks
                {
                    id: "parks",
                    type: "fill",
                    source: "lisbon",
                    "source-layer": "parks",
                    paint: {
                        "fill-color": "#c8e6c9",
                        "fill-opacity": 0.8
                    }
                },
                // Buildings
                {
                    id: "buildings",
                    type: "fill",
                    source: "lisbon",
                    "source-layer": "buildings",
                    paint: {
                        "fill-color": "#e0e0e0",
                        "fill-opacity": 0.7
                    }
                },
                // Roads
                {
                    id: "roads",
                    type: "line",
                    source: "lisbon",
                    "source-layer": "roads",
                    paint: {
                        "line-color": "#ffffff",
                        "line-width": {
                            "base": 1.4,
                            "stops": [
                                [6, 0.5],
                                [20, 30]
                            ]
                        }
                    }
                },
                // Road labels
                {
                    id: "road-labels",
                    type: "symbol",
                    source: "lisbon",
                    "source-layer": "roads",
                    layout: {
                        "text-field": "{name}",
                        "text-font": ["Open Sans Regular"],
                        "text-size": 12,
                        "symbol-placement": "line",
                        "text-rotation-alignment": "map"
                    },
                    paint: {
                        "text-color": "#666666",
                        "text-halo-color": "#ffffff",
                        "text-halo-width": 1
                    }
                }
            ]
        };
    }

    /**
     * Initialize custom layers
     */
    initializeLayers() {
        // Route layer
        this.map.addSource('route', {
            type: 'geojson',
            data: {
                type: 'Feature',
                properties: {},
                geometry: {
                    type: 'LineString',
                    coordinates: []
                }
            }
        });

        this.map.addLayer({
            id: 'route',
            type: 'line',
            source: 'route',
            layout: {
                'line-join': 'round',
                'line-cap': 'round'
            },
            paint: {
                'line-color': '#9333ea',
                'line-width': 6,
                'line-opacity': 0.8
            }
        });

        // Wheelchair accessible route highlight
        this.map.addLayer({
            id: 'route-accessible',
            type: 'line',
            source: 'route',
            layout: {
                'line-join': 'round',
                'line-cap': 'round'
            },
            paint: {
                'line-color': '#22c55e',
                'line-width': 8,
                'line-opacity': 0.6,
                'line-dasharray': [2, 2]
            }
        });
    }

    /**
     * Add location marker
     * @param {string} type - 'pickup' or 'dropoff'
     * @param {number} lat - Latitude
     * @param {number} lng - Longitude
     */
    addLocationMarker(type, lat, lng) {
        // Remove existing marker
        if (this.markers[type]) {
            this.markers[type].remove();
        }

        // Create custom marker element
        const el = document.createElement('div');
        el.className = `marker marker-${type}`;
        
        if (type === 'pickup') {
            el.innerHTML = `
                <svg width="40" height="40" viewBox="0 0 40 40">
                    <circle cx="20" cy="20" r="18" fill="#22c55e" stroke="#fff" stroke-width="2"/>
                    <text x="20" y="26" text-anchor="middle" fill="#fff" font-size="20" font-weight="bold">P</text>
                </svg>
            `;
        } else {
            el.innerHTML = `
                <svg width="40" height="40" viewBox="0 0 40 40">
                    <circle cx="20" cy="20" r="18" fill="#ef4444" stroke="#fff" stroke-width="2"/>
                    <text x="20" y="26" text-anchor="middle" fill="#fff" font-size="20" font-weight="bold">D</text>
                </svg>
            `;
        }

        // Add marker to map
        this.markers[type] = new maplibregl.Marker(el)
            .setLngLat([lng, lat])
            .addTo(this.map);

        // Add popup
        const popup = new maplibregl.Popup({ offset: 25 })
            .setText(type === 'pickup' ? 'Pickup Location' : 'Dropoff Location');
        
        this.markers[type].setPopup(popup);
    }

    /**
     * Display route on map
     * @param {string} encodedPolyline - Encoded polyline from routing service
     * @param {Object} bounds - Route bounding box
     */
    displayRoute(encodedPolyline, bounds) {
        // Decode polyline
        const decoded = this.decodePolyline(encodedPolyline);
        
        // Convert to GeoJSON
        const routeGeoJSON = {
            type: 'Feature',
            properties: {},
            geometry: {
                type: 'LineString',
                coordinates: decoded.map(coord => [coord[1], coord[0]]) // Convert to lng,lat
            }
        };

        // Update route source
        this.map.getSource('route').setData(routeGeoJSON);

        // Fit map to route bounds
        if (bounds && bounds.length === 4) {
            this.map.fitBounds([
                [bounds[0], bounds[1]], // Southwest
                [bounds[2], bounds[3]]  // Northeast
            ], {
                padding: 50
            });
        }
    }

    /**
     * Decode polyline5 format
     * @param {string} encoded - Encoded polyline string
     * @returns {Array} Decoded coordinates
     */
    decodePolyline(encoded) {
        const points = [];
        let index = 0;
        let lat = 0;
        let lng = 0;

        while (index < encoded.length) {
            let shift = 0;
            let result = 0;
            let byte;

            do {
                byte = encoded.charCodeAt(index++) - 63;
                result |= (byte & 0x1f) << shift;
                shift += 5;
            } while (byte >= 0x20);

            const deltaLat = ((result & 1) ? ~(result >> 1) : (result >> 1));
            lat += deltaLat;

            shift = 0;
            result = 0;

            do {
                byte = encoded.charCodeAt(index++) - 63;
                result |= (byte & 0x1f) << shift;
                shift += 5;
            } while (byte >= 0x20);

            const deltaLng = ((result & 1) ? ~(result >> 1) : (result >> 1));
            lng += deltaLng;

            points.push([lat / 1e5, lng / 1e5]);
        }

        return points;
    }

    /**
     * Show driver locations
     * @param {Array} drivers - Array of driver locations
     */
    showDrivers(drivers) {
        // Clear existing driver markers
        this.markers.drivers.forEach(marker => marker.remove());
        this.markers.drivers = [];

        drivers.forEach((driver, index) => {
            const el = document.createElement('div');
            el.className = 'marker marker-driver';
            el.innerHTML = `
                <svg width="30" height="30" viewBox="0 0 30 30">
                    <circle cx="15" cy="15" r="14" fill="#6366f1" stroke="#fff" stroke-width="2"/>
                    <text x="15" y="20" text-anchor="middle" fill="#fff" font-size="16">🚗</text>
                </svg>
            `;

            const marker = new maplibregl.Marker(el)
                .setLngLat([driver.lng, driver.lat])
                .addTo(this.map);

            const popup = new maplibregl.Popup({ offset: 25 })
                .setHTML(`
                    <div class="driver-popup">
                        <strong>${driver.name}</strong><br>
                        Rating: ${driver.rating} ⭐<br>
                        ${driver.vehicle_type}
                    </div>
                `);

            marker.setPopup(popup);
            this.markers.drivers.push(marker);
        });
    }

    /**
     * Enable location picker mode
     * @param {Function} callback - Called with {lat, lng} when location is picked
     */
    enableLocationPicker(callback) {
        const cursor = 'crosshair';
        this.map.getCanvas().style.cursor = cursor;

        const onClick = (e) => {
            const { lng, lat } = e.lngLat;
            
            // Disable picker mode
            this.map.getCanvas().style.cursor = '';
            this.map.off('click', onClick);

            // Call callback with location
            callback({ lat, lng });
        };

        this.map.on('click', onClick);
    }

    /**
     * Search and suggest addresses
     * @param {string} query - Search query
     * @returns {Promise<Array>} Address suggestions
     */
    async searchAddress(query) {
        // Check cache first
        if (this.geocodingCache.has(query)) {
            return this.geocodingCache.get(query);
        }

        try {
            const response = await fetch('/api/geocode/suggest/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ query })
            });

            if (!response.ok) {
                throw new Error('Geocoding request failed');
            }

            const suggestions = await response.json();
            
            // Cache results
            this.geocodingCache.set(query, suggestions);
            
            return suggestions;

        } catch (error) {
            console.error('Address search error:', error);
            return [];
        }
    }

    /**
     * Get CSRF token for API requests
     */
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    /**
     * Clean up map resources
     */
    destroy() {
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
        maplibregl.removeProtocol("pmtiles");
    }
}

export default MapService;
```

### 4.2 Address Autocomplete Component

```javascript
// project/static/js/components/AddressAutocomplete.js

class AddressAutocomplete {
    constructor(inputElement, options = {}) {
        this.input = inputElement;
        this.options = {
            minChars: 3,
            delay: 300,
            maxSuggestions: 5,
            onSelect: null,
            ...options
        };
        
        this.dropdown = null;
        this.selectedIndex = -1;
        this.suggestions = [];
        this.debounceTimer = null;
        
        this.init();
    }

    init() {
        // Create dropdown element
        this.createDropdown();
        
        // Bind events
        this.input.addEventListener('input', this.handleInput.bind(this));
        this.input.addEventListener('keydown', this.handleKeydown.bind(this));
        this.input.addEventListener('blur', this.handleBlur.bind(this));
        
        // Position dropdown on window resize
        window.addEventListener('resize', this.positionDropdown.bind(this));
    }

    createDropdown() {
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'address-autocomplete-dropdown';
        this.dropdown.style.cssText = `
            position: absolute;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 0.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        `;
        document.body.appendChild(this.dropdown);
    }

    handleInput(e) {
        const value = e.target.value.trim();
        
        // Clear previous timer
        clearTimeout(this.debounceTimer);
        
        if (value.length < this.options.minChars) {
            this.hideDropdown();
            return;
        }
        
        // Debounce API calls
        this.debounceTimer = setTimeout(() => {
            this.fetchSuggestions(value);
        }, this.options.delay);
    }

    async fetchSuggestions(query) {
        try {
            const response = await fetch('/api/geocode/suggest/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ query, limit: this.options.maxSuggestions })
            });

            if (!response.ok) {
                throw new Error('Failed to fetch suggestions');
            }

            const data = await response.json();
            this.suggestions = data.suggestions || [];
            this.renderSuggestions();
            
        } catch (error) {
            console.error('Autocomplete error:', error);
            this.hideDropdown();
        }
    }

    renderSuggestions() {
        if (this.suggestions.length === 0) {
            this.hideDropdown();
            return;
        }

        // Clear dropdown
        this.dropdown.innerHTML = '';
        this.selectedIndex = -1;

        // Add suggestions
        this.suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.style.cssText = `
                padding: 0.75rem 1rem;
                cursor: pointer;
                transition: background-color 0.2s;
            `;
            
            // Highlight matching text
            const regex = new RegExp(`(${this.escapeRegex(this.input.value)})`, 'gi');
            const highlighted = suggestion.address.replace(regex, '<strong>$1</strong>');
            
            item.innerHTML = `
                <div class="address-main" style="font-weight: 500;">${highlighted}</div>
                ${suggestion.distance ? `<div class="address-distance" style="font-size: 0.875rem; color: #6b7280;">~${suggestion.distance}m away</div>` : ''}
            `;
            
            // Add hover effect
            item.addEventListener('mouseenter', () => {
                this.selectIndex(index);
            });
            
            item.addEventListener('click', () => {
                this.selectSuggestion(suggestion);
            });
            
            this.dropdown.appendChild(item);
        });

        this.showDropdown();
    }

    selectIndex(index) {
        // Remove previous selection
        const items = this.dropdown.querySelectorAll('.suggestion-item');
        items.forEach(item => {
            item.style.backgroundColor = '';
        });

        // Add new selection
        if (index >= 0 && index < items.length) {
            items[index].style.backgroundColor = '#f3f4f6';
            this.selectedIndex = index;
        }
    }

    selectSuggestion(suggestion) {
        this.input.value = suggestion.address;
        this.hideDropdown();
        
        if (this.options.onSelect) {
            this.options.onSelect(suggestion);
        }
    }

    handleKeydown(e) {
        if (!this.dropdown.style.display || this.dropdown.style.display === 'none') {
            return;
        }

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectIndex(Math.min(this.selectedIndex + 1, this.suggestions.length - 1));
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.selectIndex(Math.max(this.selectedIndex - 1, -1));
                break;
                
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0) {
                    this.selectSuggestion(this.suggestions[this.selectedIndex]);
                }
                break;
                
            case 'Escape':
                this.hideDropdown();
                break;
        }
    }

    handleBlur() {
        // Delay to allow click events to fire
        setTimeout(() => {
            this.hideDropdown();
        }, 200);
    }

    showDropdown() {
        this.positionDropdown();
        this.dropdown.style.display = 'block';
    }

    hideDropdown() {
        this.dropdown.style.display = 'none';
        this.selectedIndex = -1;
        this.suggestions = [];
    }

    positionDropdown() {
        const rect = this.input.getBoundingClientRect();
        this.dropdown.style.top = `${rect.bottom + window.scrollY}px`;
        this.dropdown.style.left = `${rect.left + window.scrollX}px`;
        this.dropdown.style.width = `${rect.width}px`;
    }

    escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    destroy() {
        this.input.removeEventListener('input', this.handleInput);
        this.input.removeEventListener('keydown', this.handleKeydown);
        this.input.removeEventListener('blur', this.handleBlur);
        window.removeEventListener('resize', this.positionDropdown);
        
        if (this.dropdown && this.dropdown.parentNode) {
            this.dropdown.parentNode.removeChild(this.dropdown);
        }
    }
}

export default AddressAutocomplete;
```

## 5. API Endpoints Implementation

### 5.1 Geocoding API Views

```python
# project/app/api/geocoding_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
import logging

from app.services.geocoding_service import GeocodingService, RateLimitExceeded
from app.services.routing_service import RoutingService

logger = logging.getLogger(__name__)


class GeocodingRateThrottle(UserRateThrottle):
    """Custom throttle for geocoding endpoints"""
    scope = 'geocoding'
    rate = '60/minute'


class RoutingRateThrottle(UserRateThrottle):
    """Custom throttle for routing endpoints"""
    scope = 'routing'
    rate = '100/minute'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([GeocodingRateThrottle])
def geocode_address(request):
    """
    Geocode an address
    
    Request:
        POST /api/geocode/
        {
            "address": "Hospital São José, Lisboa"
        }
    
    Response:
        {
            "success": true,
            "result": {
                "lat": 38.7223,
                "lon": -9.1393,
                "display_name": "Hospital São José, Lisboa",
                "confidence": 0.8
            }
        }
    """
    try:
        address = request.data.get('address', '').strip()
        if not address:
            return Response({
                'success': False,
                'error': 'Address is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        geocoding_service = GeocodingService()
        result = geocoding_service.geocode(address)
        
        if result:
            return Response({
                'success': True,
                'result': result
            })
        else:
            return Response({
                'success': False,
                'error': 'Address not found or outside service area'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except RateLimitExceeded:
        return Response({
            'success': False,
            'error': 'Rate limit exceeded. Please try again later.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return Response({
            'success': False,
            'error': 'Geocoding service error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([GeocodingRateThrottle])
def reverse_geocode(request):
    """
    Reverse geocode coordinates
    
    Request:
        POST /api/geocode/reverse/
        {
            "lat": 38.7223,
            "lon": -9.1393
        }
    """
    try:
        lat = request.data.get('lat')
        lon = request.data.get('lon')
        
        if lat is None or lon is None:
            return Response({
                'success': False,
                'error': 'Latitude and longitude are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        geocoding_service = GeocodingService()
        address = geocoding_service.reverse_geocode(float(lat), float(lon))
        
        if address:
            return Response({
                'success': True,
                'address': address
            })
        else:
            return Response({
                'success': False,
                'error': 'Location outside service area'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        logger.error(f"Reverse geocoding error: {e}")
        return Response({
            'success': False,
            'error': 'Service error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([GeocodingRateThrottle])
def address_suggestions(request):
    """
    Get address autocomplete suggestions
    
    Request:
        POST /api/geocode/suggest/
        {
            "query": "Rua do",
            "limit": 5
        }
    """
    try:
        query = request.data.get('query', '').strip()
        limit = min(int(request.data.get('limit', 5)), 10)
        
        if len(query) < 3:
            return Response({
                'success': True,
                'suggestions': []
            })
        
        geocoding_service = GeocodingService()
        suggestions = geocoding_service.get_address_suggestions(query, limit)
        
        return Response({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        logger.error(f"Address suggestion error: {e}")
        return Response({
            'success': False,
            'error': 'Service error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([GeocodingRateThrottle])
def search_nearby(request):
    """
    Search for nearby places
    
    Request:
        POST /api/geocode/nearby/
        {
            "query": "hospital",
            "lat": 38.7223,
            "lon": -9.1393,
            "radius": 5000,
            "type": "hospital"
        }
    """
    try:
        query = request.data.get('query', '')
        lat = request.data.get('lat')
        lon = request.data.get('lon')
        radius = min(int(request.data.get('radius', 5000)), 10000)
        amenity_type = request.data.get('type')
        
        if not all([query, lat, lon]):
            return Response({
                'success': False,
                'error': 'Query, latitude, and longitude are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        geocoding_service = GeocodingService()
        results = geocoding_service.search_nearby(
            query, float(lat), float(lon), radius, amenity_type
        )
        
        return Response({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Nearby search error: {e}")
        return Response({
            'success': False,
            'error': 'Service error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([RoutingRateThrottle])
def calculate_route(request):
    """
    Calculate route between two points
    
    Request:
        POST /api/route/
        {
            "start": {"lat": 38.7223, "lon": -9.1393},
            "end": {"lat": 38.7076, "lon": -9.1365},
            "profile": "wheelchair"
        }
    """
    try:
        start = request.data.get('start')
        end = request.data.get('end')
        profile = request.data.get('profile', 'wheelchair')
        
        if not all([start, end]):
            return Response({
                'success': False,
                'error': 'Start and end coordinates required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        routing_service = RoutingService()
        route = routing_service.calculate_route(
            (start['lat'], start['lon']),
            (end['lat'], end['lon']),
            profile
        )
        
        if route:
            # Calculate fare estimate
            from app.services.pricing_service import PricingService
            pricing_service = PricingService()
            
            fare_estimate = pricing_service.calculate_pre_booked_fare(
                distance_km=route['distance_km'],
                duration_minutes=int(route['duration_min']),
                wheelchair_required=profile == 'wheelchair'
            )
            
            route['fare_estimate'] = {
                'amount': float(fare_estimate),
                'currency': 'EUR'
            }
            
            return Response({
                'success': True,
                'route': route
            })
        else:
            return Response({
                'success': False,
                'error': 'No accessible route found'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        logger.error(f"Route calculation error: {e}")
        return Response({
            'success': False,
            'error': 'Routing service error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 60)  # Cache for 1 hour
def service_area_bounds(request):
    """
    Get service area boundaries
    
    Response:
        {
            "bounds": {
                "north": 38.8500,
                "south": 38.6000,
                "east": -9.0000,
                "west": -9.5000
            },
            "center": {"lat": 38.7223, "lon": -9.1393}
        }
    """
    from django.conf import settings
    
    return Response({
        'bounds': settings.SERVICE_AREA_BOUNDS,
        'center': {
            'lat': 38.7223,
            'lon': -9.1393
        }
    })
```

### 5.2 Map Configuration API

```python
# project/app/api/map_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
from django.views.decorators.cache import cache_page
import hmac
import hashlib
import time


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 60 * 24)  # Cache for 24 hours
def map_config(request):
    """
    Get map configuration including tile URLs
    
    Response:
        {
            "tiles_url": "https://r2.example.com/lisbon.pmtiles",
            "glyphs_url": "https://r2.example.com/fonts/{fontstack}/{range}.pbf",
            "sprite_url": "https://r2.example.com/sprites/sprite",
            "bounds": {...}
        }
    """
    # Generate signed URL for secure tile access
    timestamp = int(time.time())
    tile_path = f"lisbon.pmtiles?t={timestamp}"
    
    # Create signature
    signature = hmac.new(
        settings.R2_SECRET_ACCESS_KEY.encode(),
        tile_path.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return Response({
        'tiles_url': f"{settings.R2_PUBLIC_URL}/{tile_path}&s={signature}",
        'glyphs_url': f"{settings.R2_PUBLIC_URL}/fonts/{{fontstack}}/{{range}}.pbf",
        'sprite_url': f"{settings.R2_PUBLIC_URL}/sprites/sprite",
        'bounds': settings.SERVICE_AREA_BOUNDS,
        'default_center': [-9.1393, 38.7223],
        'default_zoom': 12,
        'min_zoom': 10,
        'max_zoom': 18
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def tile_proxy(request, z, x, y):
    """
    Proxy for map tiles with caching and access control
    
    This endpoint is used if direct R2 access is not available
    """
    try:
        import requests
        from django.http import HttpResponse
        
        # Validate zoom level
        if not (10 <= int(z) <= 18):
            return Response({
                'error': 'Invalid zoom level'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Build tile URL
        tile_url = f"{settings.R2_PUBLIC_URL}/tiles/{z}/{x}/{y}.pbf"
        
        # Add authentication headers
        headers = {
            'Authorization': f'Bearer {settings.R2_ACCESS_KEY_ID}'
        }
        
        # Fetch tile
        response = requests.get(tile_url, headers=headers, timeout=5)
        response.raise_for_status()
        
        # Return tile with appropriate headers
        return HttpResponse(
            response.content,
            content_type='application/x-protobuf',
            headers={
                'Cache-Control': 'public, max-age=86400',  # 24 hours
                'X-Content-Type-Options': 'nosniff'
            }
        )
        
    except Exception as e:
        logger.error(f"Tile proxy error: {e}")
        return Response({
            'error': 'Tile fetch error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

## 6. Infrastructure Setup

### 6.1 Redis Configuration

```python
# project/settings/cache.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'wheelchair_rides',
        'TIMEOUT': 3600,  # 1 hour default
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

### 6.2 Cloudflare R2 Setup Script

```python
# scripts/setup_r2_maps.py
import boto3
from botocore.config import Config
import os
import sys
from pathlib import Path

def setup_r2_bucket():
    """Set up Cloudflare R2 bucket for map tiles"""
    
    # R2 configuration
    config = Config(
        region_name='auto',
        signature_version='s3v4',
        retries={
            'max_attempts': 3,
            'mode': 'standard'
        }
    )
    
    # Create S3 client for R2
    s3 = boto3.client(
        's3',
        endpoint_url=f'https://{os.environ["R2_ACCOUNT_ID"]}.r2.cloudflarestorage.com',
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
        config=config
    )
    
    bucket_name = os.environ['R2_BUCKET_NAME']
    
    try:
        # Create bucket if it doesn't exist
        s3.create_bucket(Bucket=bucket_name)
        print(f"✓ Created bucket: {bucket_name}")
    except s3.exceptions.BucketAlreadyExists:
        print(f"✓ Bucket already exists: {bucket_name}")
    
    # Set CORS configuration
    cors_config = {
        'CORSRules': [{
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['GET', 'HEAD'],
            'AllowedOrigins': ['*'],  # Restrict in production
            'ExposeHeaders': ['ETag'],
            'MaxAgeSeconds': 86400
        }]
    }
    
    s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_config)
    print("✓ CORS configuration applied")
    
    # Upload map tiles
    tiles_path = Path('data/lisbon.pmtiles')
    if tiles_path.exists():
        with open(tiles_path, 'rb') as f:
            s3.put_object(
                Bucket=bucket_name,
                Key='lisbon.pmtiles',
                Body=f,
                ContentType='application/x-protomaps-tiles',
                CacheControl='public, max-age=2592000'  # 30 days
            )
        print("✓ Uploaded map tiles")
    else:
        print("⚠ Map tiles not found. Download from Protomaps or generate.")
    
    # Create public access policy (if using R2 custom domain)
    print("\n✓ R2 setup complete!")
    print(f"Public URL: https://{os.environ['R2_PUBLIC_URL']}")

if __name__ == '__main__':
    setup_r2_bucket()
```

## 7. Security Implementations

### 7.1 API Security Middleware

```python
# project/app/middleware/api_security.py
import hmac
import hashlib
import time
from django.http import JsonResponse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class APISecurityMiddleware:
    """Security middleware for API endpoints"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Only apply to API endpoints
        if request.path.startswith('/api/'):
            # Check request signature for external APIs
            if request.path.startswith('/api/external/'):
                if not self.verify_request_signature(request):
                    return JsonResponse({
                        'error': 'Invalid request signature'
                    }, status=403)
            
            # Add security headers
            response = self.get_response(request)
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            return response
        
        return self.get_response(request)
    
    def verify_request_signature(self, request):
        """Verify request signature for external API calls"""
        signature = request.headers.get('X-API-Signature')
        timestamp = request.headers.get('X-API-Timestamp')
        
        if not signature or not timestamp:
            return False
        
        # Check timestamp (within 5 minutes)
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - request_time) > 300:
                return False
        except ValueError:
            return False
        
        # Verify signature
        body = request.body.decode('utf-8', errors='ignore')
        message = f"{timestamp}:{request.path}:{body}"
        
        expected_signature = hmac.new(
            settings.API_SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
```

### 7.2 Rate Limiting Configuration

```python
# project/settings/throttling.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/hour',
        'user': '1000/hour',
        'geocoding': '60/minute',
        'routing': '100/minute',
        'tiles': '1000/hour'
    }
}

# Custom rate limit for expensive operations
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_KEY = 'header:x-forwarded-for'
RATELIMIT_RATE = '100/h'
RATELIMIT_SKIP_TIMEOUT = False
RATELIMIT_COUNTS_ONLY_UNSAFE_METHODS = True
```

## 8. Performance Monitoring

### 8.1 Performance Middleware

```python
# project/app/middleware/performance.py
import time
import logging
from django.conf import settings

logger = logging.getLogger('performance')


class PerformanceMonitoringMiddleware:
    """Monitor API performance"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_request_threshold = 3.0  # seconds
        
    def __call__(self, request):
        # Skip for static files
        if request.path.startswith('/static/'):
            return self.get_response(request)
        
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Log slow requests
        if duration > self.slow_request_threshold:
            logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {duration:.2f}s"
            )
        
        # Add performance header
        response['X-Response-Time'] = f"{duration:.3f}s"
        
        # Log to metrics service
        if hasattr(settings, 'METRICS_ENABLED') and settings.METRICS_ENABLED:
            self.log_metrics(request, response, duration)
        
        return response
    
    def log_metrics(self, request, response, duration):
        """Log metrics to monitoring service"""
        # This would integrate with your monitoring solution
        # (e.g., Prometheus, DataDog, New Relic)
        pass
```

## 9. Deployment Configuration

### 9.1 Docker Configuration

```dockerfile
# Dockerfile.phase1
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements-phase1.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-phase1.txt

# Copy application code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations
RUN python manage.py migrate

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "project.wsgi:application"]
```

### 9.2 Requirements for Phase 1

```txt
# requirements-phase1.txt
# Mapping and Geocoding
mapbox-vector-tile==1.2.1
polyline==2.0.0
geopy==2.3.0
shapely==2.0.1
pyproj==3.5.0

# Caching and Performance
django-redis==5.3.0
hiredis==2.2.3

# API Rate Limiting
django-ratelimit==4.1.0

# Cloud Storage
boto3==1.28.0

# Monitoring
django-prometheus==2.3.1

# Security
django-cors-headers==4.2.0
cryptography==41.0.0

# Testing
pytest==7.4.0
pytest-django==4.5.2
pytest-cov==4.1.0
pytest-mock==3.11.1
factory-boy==3.3.0
```

## Conclusion

This comprehensive implementation plan for Phase 1 provides:

1. **Secure Environment Configuration** - Proper API key management and settings structure
2. **Enhanced Geocoding Service** - Rate limiting, caching, input validation, and fallback mechanisms
3. **Routing Service** - Wheelchair-accessible routing with OpenRouteService integration
4. **Map Components** - MapLibre GL integration with Protomaps and address autocomplete
5. **API Endpoints** - RESTful APIs with proper throttling and security
6. **Infrastructure Setup** - Redis caching and Cloudflare R2 configuration
7. **Security Measures** - API security middleware and rate limiting
8. **Performance Monitoring** - Request tracking and slow query detection
9. **Comprehensive Testing** - Unit tests with high coverage

The implementation follows security best practices including:
- Input validation and sanitization
- Rate limiting to prevent abuse
- Secure API key management
- Request signing for external APIs
- Proper error handling without information leakage
- Caching to reduce external API calls

Next steps would be to implement these components incrementally, starting with environment configuration and gradually building up the mapping infrastructure before moving to Phase 2 (Immediate Booking System).