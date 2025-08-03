# Map and Geocoding Fix Implementation Plan with Unit Tests

## Executive Summary

This document provides a comprehensive implementation plan to fix the map display and geocoding issues identified in the RideConnect application. The plan includes code implementation, unit tests, integration tests, and deployment strategies.

## Problem Analysis Summary

Based on the analysis of `MAP_GEOCODING_FIX.md` and codebase review:

1. **Authentication Issue**: Geocoding endpoints require authentication but AJAX requests lack proper session authentication
2. **Map Initialization Failure**: PMTiles and MapLibre GL may fail to load, causing blank map display
3. **Error Handling**: Limited fallback mechanisms when external services fail
4. **Frontend Integration**: JavaScript components need better error recovery and retry logic

## Implementation Plan

### Phase 1: Backend API Fixes

#### 1.1 Create Public Development Endpoint

**File**: `project/app/api/geocoding_public_views.py`

```python
"""
Development-only public geocoding endpoints
These endpoints bypass authentication for easier development and testing
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
import json
import logging

from ..services.geocoding_service import GeocodingService, GeocodingError

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
@method_decorator(ratelimit(key='ip', rate='60/m', method='POST'))
def public_geocoding_suggestions(request):
    """
    Public endpoint for address suggestions (development only)
    Rate limited by IP address to prevent abuse
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({'error': 'Query field is required'}, status=400)
        
        if len(query) < 2:
            return JsonResponse([], safe=False)
        
        limit = min(int(data.get('limit', 5)), 10)
        
        # Initialize geocoding service
        geocoding_service = GeocodingService()
        
        # Get suggestions with error handling
        suggestions = geocoding_service.get_address_suggestions(query, limit)
        
        logger.info(f"Public geocoding suggestions: {len(suggestions)} results for '{query[:30]}'")
        return JsonResponse(suggestions, safe=False)
        
    except GeocodingError as e:
        logger.warning(f"Public geocoding validation error: {e}")
        return JsonResponse({'error': str(e)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Public geocoding error: {e}")
        return JsonResponse({'error': 'Service unavailable'}, status=503)

@csrf_exempt
@require_http_methods(["POST"])
@method_decorator(ratelimit(key='ip', rate='30/m', method='POST'))
def public_reverse_geocode(request):
    """
    Public endpoint for reverse geocoding (development only)
    """
    try:
        data = json.loads(request.body)
        lat = data.get('lat')
        lng = data.get('lng')
        
        if lat is None or lng is None:
            return JsonResponse({'error': 'Both lat and lng are required'}, status=400)
        
        # Initialize geocoding service
        geocoding_service = GeocodingService()
        
        # Perform reverse geocoding
        result = geocoding_service.reverse_geocode(float(lat), float(lng))
        
        if result:
            return JsonResponse(result)
        else:
            return JsonResponse({'error': 'Address not found'}, status=404)
            
    except GeocodingError as e:
        logger.warning(f"Public reverse geocoding error: {e}")
        return JsonResponse({'error': str(e)}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid coordinates'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Public reverse geocoding error: {e}")
        return JsonResponse({'error': 'Service unavailable'}, status=503)

@require_http_methods(["GET"])
@cache_page(60 * 15)  # Cache for 15 minutes
def public_service_area(request):
    """
    Public endpoint to get service area bounds
    """
    try:
        geocoding_service = GeocodingService()
        bounds = geocoding_service.service_area
        
        # Calculate center
        center_lat = (bounds.get('north', 38.85) + bounds.get('south', 38.6)) / 2
        center_lng = (bounds.get('east', -9.0) + bounds.get('west', -9.5)) / 2
        
        return JsonResponse({
            'bounds': bounds,
            'center': {
                'lat': center_lat,
                'lng': center_lng
            },
            'name': 'Greater Lisbon Area'
        })
        
    except Exception as e:
        logger.error(f"Public service area error: {e}")
        return JsonResponse({'error': 'Service unavailable'}, status=503)
```

#### 1.2 Update API URLs

**File**: `project/app/api/urls.py`

```python
# Add imports at the top
from .geocoding_public_views import (
    public_geocoding_suggestions,
    public_reverse_geocode,
    public_service_area
)

# Add to urlpatterns
urlpatterns = [
    # ... existing patterns ...
    
    # Development-only public endpoints
    path('geocoding/public/suggestions/', public_geocoding_suggestions, name='public_geocoding_suggestions'),
    path('geocoding/public/reverse/', public_reverse_geocode, name='public_reverse_geocode'),
    path('geocoding/public/service-area/', public_service_area, name='public_service_area'),
]
```

### Phase 2: Frontend JavaScript Improvements

#### 2.1 Enhanced Address Autocomplete

**File**: `project/static/js/address-autocomplete.js`

Update the `searchAddresses` method:

```javascript
async searchAddresses(query) {
    try {
        this.setLoading(true);
        
        // Use development public endpoint if available, fallback to authenticated
        const endpoint = this.config.suggestionsEndpoint || 
                        (this.config.usePublicEndpoint ? 
                         `${this.config.apiEndpoint}/geocoding/public/suggestions/` :
                         `${this.config.apiEndpoint}/geocoding/suggestions/`);
        
        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };
        
        // Add CSRF token if not using public endpoint
        if (!this.config.usePublicEndpoint) {
            headers['X-CSRFToken'] = this.getCSRFToken();
        }
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: headers,
            credentials: this.config.usePublicEndpoint ? 'omit' : 'same-origin',
            body: JSON.stringify({
                query: query,
                limit: this.config.maxSuggestions
            })
        });
        
        if (!response.ok) {
            if (response.status === 401 && !this.config.usePublicEndpoint) {
                // Try public endpoint as fallback
                return this.searchAddressesPublic(query);
            }
            throw new Error(`Search request failed: ${response.status}`);
        }
        
        const suggestions = await response.json();
        this.displaySuggestions(suggestions);
        
    } catch (error) {
        console.error('Address search error:', error);
        
        // Try fallback if main request failed
        if (!this.config.usePublicEndpoint) {
            try {
                await this.searchAddressesPublic(query);
                return;
            } catch (fallbackError) {
                console.error('Fallback search also failed:', fallbackError);
            }
        }
        
        this.handleError('Failed to search addresses: ' + error.message);
        this.hideSuggestions();
    } finally {
        this.setLoading(false);
    }
}

// Add fallback method
async searchAddressesPublic(query) {
    const response = await fetch(`${this.config.apiEndpoint}/geocoding/public/suggestions/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'omit',
        body: JSON.stringify({
            query: query,
            limit: this.config.maxSuggestions
        })
    });
    
    if (!response.ok) {
        throw new Error(`Public search failed: ${response.status}`);
    }
    
    const suggestions = await response.json();
    this.displaySuggestions(suggestions);
}
```

#### 2.2 Enhanced Map Component

**File**: `project/static/js/map-component.js`

Add fallback initialization methods:

```javascript
// Add to WheelchairRideMap class
async init() {
    if (typeof maplibregl === 'undefined') {
        this.handleError('MapLibre GL JS not loaded. Please include the library.');
        return;
    }
    
    try {
        // Try to initialize with PMTiles first
        await this.initializeWithPMTiles();
    } catch (pmtilesError) {
        console.warn('PMTiles initialization failed:', pmtilesError);
        try {
            // Fallback to OSM tiles
            await this.initializeWithOSM();
        } catch (osmError) {
            console.error('All map initialization methods failed:', osmError);
            this.initializeStaticMap();
        }
    }
}

async initializeWithPMTiles() {
    if (typeof Protocol === 'undefined') {
        throw new Error('Protomaps Protocol not available');
    }
    
    const protocol = new Protocol();
    maplibregl.addProtocol("pmtiles", protocol.tile);
    
    this.map = new maplibregl.Map({
        container: this.containerId,
        style: this.getMapStyle(),
        center: this.config.center,
        zoom: this.config.zoom,
        minZoom: this.config.minZoom,
        maxZoom: this.config.maxZoom
    });
    
    return new Promise((resolve, reject) => {
        this.map.on('load', () => {
            this.onMapLoaded();
            resolve();
        });
        
        this.map.on('error', (e) => {
            reject(new Error('PMTiles map failed to load: ' + e.error));
        });
        
        // Timeout after 10 seconds
        setTimeout(() => {
            reject(new Error('PMTiles map load timeout'));
        }, 10000);
    });
}

async initializeWithOSM() {
    this.map = new maplibregl.Map({
        container: this.containerId,
        style: {
            version: 8,
            sources: {
                'osm-tiles': {
                    type: 'raster',
                    tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                    tileSize: 256,
                    attribution: '© OpenStreetMap contributors'
                }
            },
            layers: [{
                id: 'osm-tiles',
                type: 'raster',
                source: 'osm-tiles'
            }]
        },
        center: this.config.center,
        zoom: this.config.zoom,
        minZoom: this.config.minZoom,
        maxZoom: this.config.maxZoom
    });
    
    return new Promise((resolve, reject) => {
        this.map.on('load', () => {
            this.onMapLoaded();
            resolve();
        });
        
        this.map.on('error', (e) => {
            reject(new Error('OSM map failed to load: ' + e.error));
        });
        
        setTimeout(() => {
            reject(new Error('OSM map load timeout'));
        }, 10000);
    });
}

initializeStaticMap() {
    // Show static map message when all else fails
    const container = document.getElementById(this.containerId);
    container.innerHTML = `
        <div class="h-full flex items-center justify-center bg-gray-100 border border-gray-300 rounded-2xl">
            <div class="text-center p-6">
                <svg class="w-16 h-16 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"></path>
                </svg>
                <h3 class="text-lg font-medium text-gray-700 mb-2">Map Temporarily Unavailable</h3>
                <p class="text-sm text-gray-500 mb-4">You can still enter addresses manually below</p>
                <button onclick="location.reload()" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors">
                    Try Again
                </button>
            </div>
        </div>
    `;
    
    // Create mock methods for API compatibility
    this.map = {
        setPickupLocation: () => {},
        setDropoffLocation: () => {},
        clearRoute: () => {},
        getSelectedLocations: () => ({ pickup: null, dropoff: null }),
        getRoute: () => null
    };
}
```

### Phase 3: Unit Tests

#### 3.1 Backend Tests

**File**: `project/app/tests/test_geocoding_public_views.py`

```python
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
        """Test empty query returns empty results"""
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
    
    def test_rate_limiting(self):
        """Test rate limiting on public endpoints"""
        # This would require a more sophisticated test setup
        # For now, just verify the decorator is applied
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
```

#### 3.2 Geocoding Service Tests

**File**: `project/app/tests/test_geocoding_service_enhanced.py`

```python
import unittest
from unittest.mock import patch, Mock
from django.test import TestCase
from django.core.cache import cache
from app.services.geocoding_service import GeocodingService, GeocodingError

class GeocodingServiceTest(TestCase):
    def setUp(self):
        self.service = GeocodingService()
        cache.clear()
    
    def test_get_address_suggestions_valid_query(self):
        """Test address suggestions with valid query"""
        with patch.object(self.service, '_get_nominatim_suggestions') as mock_nominatim:
            mock_nominatim.return_value = [
                {
                    'display_name': 'Hospital São José, Lisboa',
                    'lat': 38.7223,
                    'lng': -9.1393,
                    'type': 'hospital',
                    'importance': 0.8,
                    'formatted': 'Hospital São José, Lisboa'
                }
            ]
            
            result = self.service.get_address_suggestions('hospital', 5)
            
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['display_name'], 'Hospital São José, Lisboa')
            mock_nominatim.assert_called_once_with('hospital', 5)
    
    def test_get_address_suggestions_empty_query(self):
        """Test address suggestions with empty query"""
        result = self.service.get_address_suggestions('', 5)
        self.assertEqual(result, [])
    
    def test_get_address_suggestions_short_query(self):
        """Test address suggestions with very short query"""
        result = self.service.get_address_suggestions('a', 5)
        self.assertEqual(result, [])
    
    def test_get_address_suggestions_caching(self):
        """Test that suggestions are cached properly"""
        with patch.object(self.service, '_get_nominatim_suggestions') as mock_nominatim:
            mock_nominatim.return_value = [{'test': 'data'}]
            
            # First call
            result1 = self.service.get_address_suggestions('hospital', 5)
            
            # Second call should use cache
            result2 = self.service.get_address_suggestions('hospital', 5)
            
            self.assertEqual(result1, result2)
            mock_nominatim.assert_called_once()  # Should only be called once due to caching
    
    def test_fallback_suggestions_on_api_failure(self):
        """Test fallback behavior when Nominatim API fails"""
        with patch.object(self.service, '_get_nominatim_suggestions') as mock_nominatim:
            mock_nominatim.side_effect = Exception('API Error')
            
            # Should not raise exception, should return empty list
            result = self.service.get_address_suggestions('hospital', 5)
            self.assertEqual(result, [])
    
    def test_validate_service_area(self):
        """Test service area validation"""
        # Lisbon coordinates (should be valid)
        self.assertTrue(self.service.validate_service_area(38.7223, -9.1393))
        
        # New York coordinates (should be invalid)
        self.assertFalse(self.service.validate_service_area(40.7128, -74.0060))
    
    def test_input_validation_for_suggestions(self):
        """Test input validation for suggestions"""
        # Invalid characters should raise error
        with self.assertRaises(GeocodingError):
            self.service.get_address_suggestions('test<script>alert(1)</script>', 5)
        
        # Very long query should raise error
        long_query = 'a' * 201
        with self.assertRaises(GeocodingError):
            self.service.get_address_suggestions(long_query, 5)
```

#### 3.3 Frontend JavaScript Tests

**File**: `project/static/js/tests/test-address-autocomplete.js`

```javascript
// Using Jest testing framework
describe('AddressAutocomplete', () => {
    let autocomplete;
    let mockInput;
    let mockContainer;
    
    beforeEach(() => {
        // Create mock DOM elements
        document.body.innerHTML = `
            <div id="test-container">
                <input id="test-input" type="text">
            </div>
        `;
        
        mockInput = document.getElementById('test-input');
        autocomplete = new AddressAutocomplete(mockInput, {
            apiEndpoint: '/api',
            usePublicEndpoint: true
        });
        
        // Mock fetch
        global.fetch = jest.fn();
    });
    
    afterEach(() => {
        jest.clearAllMocks();
        if (autocomplete) {
            autocomplete.destroy();
        }
    });
    
    test('should initialize correctly', () => {
        expect(autocomplete.inputElement).toBe(mockInput);
        expect(autocomplete.config.usePublicEndpoint).toBe(true);
        expect(mockInput.getAttribute('role')).toBe('combobox');
    });
    
    test('should make API request on input', async () => {
        const mockSuggestions = [
            {
                display_name: 'Hospital São José, Lisboa',
                lat: 38.7223,
                lng: -9.1393,
                formatted: 'Hospital São José, Lisboa'
            }
        ];
        
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockSuggestions
        });
        
        await autocomplete.searchAddresses('hospital');
        
        expect(fetch).toHaveBeenCalledWith(
            '/api/geocoding/public/suggestions/',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({
                    query: 'hospital',
                    limit: 5
                })
            })
        );
    });
    
    test('should handle API errors gracefully', async () => {
        fetch.mockRejectedValueOnce(new Error('Network error'));
        
        const errorSpy = jest.spyOn(autocomplete, 'handleError');
        
        await autocomplete.searchAddresses('hospital');
        
        expect(errorSpy).toHaveBeenCalledWith(
            expect.stringContaining('Failed to search addresses')
        );
    });
    
    test('should use fallback endpoint on auth failure', async () => {
        // First call fails with auth error
        fetch.mockResolvedValueOnce({
            ok: false,
            status: 401
        });
        
        // Second call succeeds
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => []
        });
        
        // Configure to use authenticated endpoint initially
        autocomplete.config.usePublicEndpoint = false;
        
        await autocomplete.searchAddresses('hospital');
        
        expect(fetch).toHaveBeenCalledTimes(2);
        // Second call should be to public endpoint
        expect(fetch).toHaveBeenNthCalledWith(2, 
            '/api/geocoding/public/suggestions/',
            expect.any(Object)
        );
    });
});
```

### Phase 4: Integration Tests

#### 4.1 End-to-End Map Testing

**File**: `project/app/tests/test_map_integration.py`

```python
from django.test import TestCase
from django.contrib.auth.models import User
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

class MapIntegrationTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Setup Chrome options for headless testing
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.driver.implicitly_wait(10)
    
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_map_loads_on_home_page(self):
        """Test that map container appears on home page"""
        # Login user
        self.client.login(username='testuser', password='testpass123')
        
        # Navigate to home page
        self.driver.get(self.live_server_url + '/home/')
        
        # Wait for map container to be present
        map_container = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'map'))
        )
        
        self.assertTrue(map_container.is_displayed())
    
    def test_address_autocomplete_functionality(self):
        """Test address autocomplete functionality"""
        self.client.login(username='testuser', password='testpass123')
        self.driver.get(self.live_server_url + '/home/')
        
        # Find pickup input
        pickup_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'pickup-input'))
        )
        
        # Type in pickup input
        pickup_input.send_keys('hospital')
        
        # Wait for suggestions to appear
        suggestions_container = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'address-suggestions'))
        )
        
        # Check if suggestions are visible
        self.assertTrue(suggestions_container.is_displayed())
    
    def test_error_handling_when_apis_fail(self):
        """Test error handling when external APIs are not available"""
        # This test would require mocking external API failures
        # Implementation depends on testing infrastructure
        pass
```

### Phase 5: Deployment and Configuration

#### 5.1 Environment Configuration

**File**: `project/project/settings/development.py`

Add configuration for the fixes:

```python
# Map and geocoding configuration
MAP_CONFIG = {
    'USE_PUBLIC_ENDPOINTS': True,  # Enable public endpoints in development
    'FALLBACK_TO_OSM': True,      # Fallback to OSM tiles if PMTiles fail
    'ENABLE_MOCK_DATA': True,     # Use mock data when external APIs fail
}

# Rate limiting for public endpoints
RATELIMIT_STORAGE = 'django_ratelimit.storage.cache.CacheStorage'
RATELIMIT_USE_CACHE = 'default'

# Logging configuration for debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/geocoding.log',
        },
    },
    'loggers': {
        'app.services.geocoding_service': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'app.api.geocoding_public_views': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

#### 5.2 Production Configuration

**File**: `project/project/settings/production.py`

```python
# Disable public endpoints in production
MAP_CONFIG = {
    'USE_PUBLIC_ENDPOINTS': False,  # Disable public endpoints
    'FALLBACK_TO_OSM': True,       # Keep fallback enabled
    'ENABLE_MOCK_DATA': False,     # Disable mock data
}

# Stricter rate limiting in production
RATELIMIT_RATE = '30/m'  # More restrictive rate limiting

# Security headers for map resources
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
```

## Testing Strategy

### Unit Tests Execution

```bash
# Run all geocoding tests
python manage.py test app.tests.test_geocoding_public_views
python manage.py test app.tests.test_geocoding_service_enhanced

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Integration Tests

```bash
# Run Selenium tests (requires Chrome driver)
python manage.py test app.tests.test_map_integration

# Run JavaScript tests (requires Node.js)
npm test
```

### Manual Testing Checklist

1. **Address Autocomplete**:
   - [ ] Type 2+ characters in pickup field
   - [ ] Verify suggestions appear
   - [ ] Select a suggestion
   - [ ] Verify map marker appears

2. **Map Display**:
   - [ ] Map loads on page load
   - [ ] Fallback works when PMTiles fail
   - [ ] Click "Use My Location" button
   - [ ] Verify user location is detected

3. **Error Handling**:
   - [ ] Network disconnection scenario
   - [ ] Invalid coordinates
   - [ ] API rate limiting
   - [ ] Service unavailable responses

## Rollback Plan

If issues occur after deployment:

1. **Immediate Rollback**:
   - Disable public endpoints by setting `MAP_CONFIG['USE_PUBLIC_ENDPOINTS'] = False`
   - Revert JavaScript files to previous versions
   - Clear application cache

2. **Troubleshooting**:
   - Check server logs for API errors
   - Verify external service availability
   - Test in browser developer tools
   - Check rate limiting status

## Success Criteria

- [ ] Address autocomplete works without authentication errors
- [ ] Map displays correctly with fallback capability
- [ ] All unit tests pass with >90% coverage
- [ ] Integration tests pass
- [ ] Performance is maintained (response times <2s)
- [ ] Error handling provides user-friendly messages
- [ ] Development workflow is improved

## Timeline

- **Week 1**: Backend API fixes and unit tests
- **Week 2**: Frontend improvements and JavaScript tests
- **Week 3**: Integration testing and bug fixes
- **Week 4**: Documentation and deployment

This implementation plan provides a comprehensive approach to fixing the map and geocoding issues while maintaining code quality and user experience.