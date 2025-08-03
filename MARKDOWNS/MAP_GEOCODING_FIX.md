# Map Display and Geocoding Fix Implementation Guide

## Problem Analysis

The application is experiencing multiple issues:
1. **503 Service Unavailable** errors on `/api/geocoding/suggestions/` endpoint
2. **Error message**: `'str' object has no attribute 'method'` 
3. **Map not displaying** - showing placeholder text instead of interactive map
4. **Address autocomplete not working** due to API endpoint failures

## Root Causes

1. **Authentication Issue**: The geocoding suggestions endpoint requires authentication (`@permission_classes([IsAuthenticated])`) but the AJAX requests may not be properly authenticated.

2. **Request Processing Error**: The error suggests the request object is being handled incorrectly, possibly due to middleware or authentication issues.

3. **Map Library Loading**: The map might not be initializing properly due to missing PMTiles or configuration issues.

## Fix Implementation

### Step 1: Fix Authentication Headers

Update the `address-autocomplete.js` file to properly include authentication headers:

```javascript
// In address-autocomplete.js, update the searchAddresses function (line 242)
async searchAddresses(query) {
    try {
        this.setLoading(true);
        
        // Get CSRF token
        const csrfToken = this.getCSRFToken();
        
        const response = await fetch(`${this.config.apiEndpoint}/geocoding/suggestions/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                // Add session authentication header
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin', // Include cookies for session auth
            body: JSON.stringify({
                query: query,
                limit: this.config.maxSuggestions
            })
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Authentication required - please log in');
            }
            throw new Error(`Search request failed: ${response.status}`);
        }
        
        const suggestions = await response.json();
        this.displaySuggestions(suggestions);
        
    } catch (error) {
        this.handleError('Failed to search addresses: ' + error.message);
        this.hideSuggestions();
    } finally {
        this.setLoading(false);
    }
}
```

### Step 2: Create a Temporary Unauthenticated Endpoint

As a quick fix, create a temporary endpoint that doesn't require authentication for development:

Create a new file `project/app/api/geocoding_public_views.py`:

```python
"""
Temporary public geocoding endpoints for development
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging

from ..services.geocoding_service import GeocodingService, GeocodingError

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def public_geocoding_suggestions(request):
    """
    Public endpoint for address suggestions (development only)
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({'error': 'Query required'}, status=400)
        
        limit = min(int(data.get('limit', 5)), 10)
        
        # Initialize geocoding service
        geocoding_service = GeocodingService()
        
        # Get suggestions
        suggestions = geocoding_service.get_address_suggestions(query, limit)
        
        return JsonResponse(suggestions, safe=False)
        
    except Exception as e:
        logger.error(f"Public geocoding error: {e}")
        return JsonResponse({'error': 'Service unavailable'}, status=503)
```

Update `project/app/api/urls.py` to include the public endpoint:

```python
# Add this import at the top
from .geocoding_public_views import public_geocoding_suggestions

# Add this URL pattern
urlpatterns = [
    # ... existing patterns ...
    
    # Temporary public endpoint for development
    path('geocoding/public/suggestions/', public_geocoding_suggestions, name='public_geocoding_suggestions'),
]
```

### Step 3: Update JavaScript to Use Public Endpoint

Update the address autocomplete configuration in `home.html`:

```javascript
// In home.html, update the autocomplete initialization (around line 449)
pickupAutocomplete = new AddressAutocomplete(
    document.getElementById('pickup-input'),
    {
        apiEndpoint: '/api',
        placeholder: 'Enter pickup address...',
        // Override the endpoint for suggestions
        suggestionsEndpoint: '/api/geocoding/public/suggestions/',
        onSelect: function(suggestion) {
            handleAddressSelect('pickup', suggestion);
        },
        onError: handleAutocompleteError
    }
);
```

Also update `address-autocomplete.js` to use the custom endpoint:

```javascript
// Update the searchAddresses function to use custom endpoint if provided
async searchAddresses(query) {
    try {
        this.setLoading(true);
        
        // Use custom suggestions endpoint if provided
        const endpoint = this.config.suggestionsEndpoint || 
                        `${this.config.apiEndpoint}/geocoding/suggestions/`;
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                query: query,
                limit: this.config.maxSuggestions
            })
        });
        
        // ... rest of the function
    }
}
```

### Step 4: Fix Map Display

The map container needs proper initialization. Update the map initialization in `home.html`:

```javascript
// In initializeSmartBooking function (around line 437)
function initializeSmartBooking() {
    try {
        // Wait for libraries to load
        if (typeof maplibregl === 'undefined' || typeof Protocol === 'undefined') {
            console.log('Waiting for map libraries to load...');
            setTimeout(initializeSmartBooking, 500);
            return;
        }
        
        // Initialize map with proper error handling
        mapInstance = new WheelchairRideMap('map', {
            apiEndpoint: '/api',
            onLocationSelect: handleLocationSelect,
            onRouteCalculated: handleRouteCalculated,
            onError: handleMapError,
            // Use a fallback style if PMTiles fails
            fallbackStyle: {
                version: 8,
                sources: {},
                layers: [{
                    id: 'background',
                    type: 'background',
                    paint: {
                        'background-color': '#e5e7eb'
                    }
                }]
            }
        });
        
        // ... rest of initialization
    } catch (error) {
        console.error('Map initialization error:', error);
        // Show a fallback static map or message
        document.getElementById('map').innerHTML = `
            <div class="h-full flex items-center justify-center bg-gray-100">
                <div class="text-center p-4">
                    <p class="text-gray-600 mb-2">Interactive map loading...</p>
                    <p class="text-sm text-gray-500">You can still enter addresses manually</p>
                </div>
            </div>
        `;
    }
}
```

### Step 5: Add Error Recovery

Update `map-component.js` to handle PMTiles loading errors:

```javascript
// In the init function of WheelchairRideMap (around line 49)
async init() {
    if (typeof maplibregl === 'undefined') {
        this.handleError('MapLibre GL JS not loaded. Please include the library.');
        return;
    }
    
    try {
        // Try to add Protomaps protocol if available
        if (typeof Protocol !== 'undefined') {
            const protocol = new Protocol();
            maplibregl.addProtocol("pmtiles", protocol.tile);
        }
        
        // Initialize map with fallback style
        const style = this.config.fallbackStyle || this.getMapStyle();
        
        this.map = new maplibregl.Map({
            container: this.containerId,
            style: style,
            center: this.config.center,
            zoom: this.config.zoom,
            minZoom: this.config.minZoom,
            maxZoom: this.config.maxZoom
        });
        
        // ... rest of initialization
    } catch (error) {
        console.error('Map initialization error:', error);
        // Try to initialize with a basic style
        this.initializeBasicMap();
    }
}

// Add fallback basic map initialization
initializeBasicMap() {
    try {
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
            zoom: this.config.zoom
        });
        
        this.map.on('load', () => {
            this.onMapLoaded();
        });
    } catch (error) {
        this.handleError('Unable to initialize map: ' + error.message);
    }
}
```

## Testing Steps

1. **Restart Django development server**:
   ```bash
   cd project
   python manage.py runserver
   ```

2. **Clear browser cache** and reload the page

3. **Test address autocomplete**:
   - Type at least 2 characters in pickup field
   - Verify suggestions appear without errors

4. **Test map display**:
   - Check if map loads (even if basic)
   - Click "Use My Location" button
   - Verify location appears on map

5. **Check browser console** for any JavaScript errors

## Production Considerations

1. **Security**: The public geocoding endpoint should be:
   - Rate limited
   - Protected by CORS
   - Removed or secured in production

2. **Authentication**: Implement proper token-based authentication for API endpoints

3. **Map Tiles**: Ensure PMTiles are properly served with correct CORS headers

4. **Error Handling**: Add comprehensive error tracking and user-friendly messages

## Alternative Solutions

If the above fixes don't work:

1. **Use OpenStreetMap tiles directly** instead of PMTiles
2. **Implement session-based authentication** for API endpoints
3. **Use a different geocoding service** (like Mapbox or Google Maps)
4. **Add request logging** to debug the exact error location

## Monitoring

Add logging to track:
- API endpoint response times
- Authentication failures
- Map initialization errors
- Geocoding service availability

This should resolve the immediate issues and allow the map and geocoding features to work properly.