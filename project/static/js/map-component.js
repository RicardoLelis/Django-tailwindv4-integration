/**
 * Enhanced Map Component for Wheelchair Ride-Sharing
 * Provides interactive mapping with accessibility routing and address autocomplete
 * Uses MapLibre GL JS with Protomaps for offline-capable mapping
 */

class WheelchairRideMap {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.map = null;
        this.markers = {
            pickup: null,
            dropoff: null
        };
        this.routeLayer = null;
        this.currentRoute = null;
        
        // Configuration
        this.config = {
            center: [-9.1393, 38.7223], // Lisbon center
            zoom: 12,
            minZoom: 10,
            maxZoom: 18,
            tilesUrl: options.tilesUrl || 'pmtiles://https://pub-0c733fd2ba8f4e67a71b8e13d61af44e.r2.dev/portugal.pmtiles',
            apiEndpoint: options.apiEndpoint || '/api',
            ...options
        };
        
        // Event callbacks
        this.callbacks = {
            onLocationSelect: options.onLocationSelect || null,
            onRouteCalculated: options.onRouteCalculated || null,
            onError: options.onError || null
        };
        
        // State
        this.isLoading = false;
        this.selectedLocations = {
            pickup: null,
            dropoff: null
        };
        
        this.init();
    }
    
    /**
     * Initialize the map component
     */
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
    
    /**
     * Initialize with PMTiles
     */
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
                this.addMapControls();
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
    
    /**
     * Initialize with OSM tiles as fallback
     */
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
                this.addMapControls();
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
    
    /**
     * Initialize static map when all else fails
     */
    initializeStaticMap() {
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
    
    /**
     * Add map controls (extracted from init)
     */
    addMapControls() {
        // Add click handler for location selection
        this.map.on('click', (e) => {
            this.handleMapClick(e);
        });
        
        // Add navigation controls
        this.map.addControl(new maplibregl.NavigationControl(), 'top-right');
        
        // Add accessibility controls
        this.addAccessibilityControls();
    }
    
    /**
     * Get map style configuration with Protomaps
     */
    getMapStyle() {
        return {
            version: 8,
            sources: {
                "protomaps": {
                    type: "vector",
                    tiles: [this.config.tilesUrl + "/{z}/{x}/{y}"],
                    maxzoom: 14
                }
            },
            layers: [
                {
                    id: "background",
                    type: "background",
                    paint: {
                        "background-color": "#f8f9fa"
                    }
                },
                {
                    id: "roads",
                    type: "line",
                    source: "protomaps",
                    "source-layer": "roads",
                    paint: {
                        "line-color": [
                            "case",
                            ["==", ["get", "kind"], "highway"],
                            "#e74694",
                            ["==", ["get", "kind"], "major_road"],
                            "#fb923c",
                            ["==", ["get", "kind"], "minor_road"],
                            "#94a3b8",
                            "#cbd5e1"
                        ],
                        "line-width": [
                            "case",
                            ["==", ["get", "kind"], "highway"],
                            4,
                            ["==", ["get", "kind"], "major_road"],
                            3,
                            2
                        ]
                    }
                },
                {
                    id: "buildings",
                    type: "fill",
                    source: "protomaps",
                    "source-layer": "buildings",
                    paint: {
                        "fill-color": "#e2e8f0",
                        "fill-opacity": 0.8
                    }
                },
                {
                    id: "places",
                    type: "symbol",
                    source: "protomaps",
                    "source-layer": "places",
                    layout: {
                        "text-field": ["get", "name"],
                        "text-font": ["sans-serif"],
                        "text-size": 12,
                        "text-anchor": "center"
                    },
                    paint: {
                        "text-color": "#1f2937",
                        "text-halo-color": "#ffffff",
                        "text-halo-width": 1
                    }
                }
            ]
        };
    }
    
    /**
     * Handle map loaded event
     */
    onMapLoaded() {
        console.log('Map loaded successfully');
        
        // Add route layer
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
                'line-color': '#2563eb',
                'line-width': 4,
                'line-opacity': 0.8
            }
        });
        
        // Add accessibility route layer (alternative)
        this.map.addLayer({
            id: 'accessibility-route',
            type: 'line',
            source: 'route',
            layout: {
                'line-join': 'round',
                'line-cap': 'round'
            },
            paint: {
                'line-color': '#16a34a',
                'line-width': 3,
                'line-opacity': 0.6,
                'line-dasharray': [2, 2]
            }
        });
    }
    
    /**
     * Handle map click for location selection
     */
    async handleMapClick(e) {
        const { lng, lat } = e.lngLat;
        
        // Validate coordinates are in service area
        if (!this.isInServiceArea(lat, lng)) {
            this.showMessage('Location is outside service area', 'warning');
            return;
        }
        
        try {
            this.setLoading(true);
            
            // Reverse geocode the clicked location
            const address = await this.reverseGeocode(lat, lng);
            
            if (address) {
                this.selectLocation(lat, lng, address.formatted);
            } else {
                this.showMessage('Could not determine address for this location', 'error');
            }
            
        } catch (error) {
            this.handleError('Failed to process location: ' + error.message);
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Select a location (pickup or dropoff)
     */
    selectLocation(lat, lng, address) {
        // Determine if this is pickup or dropoff
        const locationType = this.selectedLocations.pickup ? 'dropoff' : 'pickup';
        
        // Store the location
        this.selectedLocations[locationType] = {
            lat: lat,
            lng: lng,
            address: address
        };
        
        // Add or update marker
        this.addMarker(lat, lng, locationType, address);
        
        // Notify callback
        if (this.callbacks.onLocationSelect) {
            this.callbacks.onLocationSelect(locationType, {
                lat: lat,
                lng: lng,
                address: address
            });
        }
        
        // If both locations are selected, calculate route
        if (this.selectedLocations.pickup && this.selectedLocations.dropoff) {
            this.calculateRoute();
        }
        
        this.showMessage(`${locationType.charAt(0).toUpperCase() + locationType.slice(1)} location set: ${address}`, 'success');
    }
    
    /**
     * Add marker to map
     */
    addMarker(lat, lng, type, address) {
        // Remove existing marker of this type
        if (this.markers[type]) {
            this.markers[type].remove();
        }
        
        // Create marker element
        const markerEl = document.createElement('div');
        markerEl.className = `map-marker map-marker-${type}`;
        markerEl.innerHTML = type === 'pickup' ? '📍' : '🏁';
        markerEl.title = `${type}: ${address}`;
        
        // Add marker to map
        this.markers[type] = new maplibregl.Marker(markerEl)
            .setLngLat([lng, lat])
            .addTo(this.map);
    }
    
    /**
     * Calculate wheelchair-accessible route
     */
    async calculateRoute() {
        if (!this.selectedLocations.pickup || !this.selectedLocations.dropoff) {
            return;
        }
        
        try {
            this.setLoading(true);
            
            const pickup = this.selectedLocations.pickup;
            const dropoff = this.selectedLocations.dropoff;
            
            // Prepare coordinates for routing API (format: [lng, lat])
            const coordinates = [
                [pickup.lng, pickup.lat],
                [dropoff.lng, dropoff.lat]
            ];
            
            // Call routing API
            const response = await fetch(`${this.config.apiEndpoint}/routing/wheelchair/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    coordinates: coordinates,
                    avoid_obstacles: true,
                    preference: 'recommended'
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to calculate route');
            }
            
            const routeData = await response.json();
            
            if (routeData.geometry && routeData.geometry.coordinates) {
                this.displayRoute(routeData);
                this.currentRoute = routeData;
                
                // Notify callback
                if (this.callbacks.onRouteCalculated) {
                    this.callbacks.onRouteCalculated(routeData);
                }
                
                // Show route summary
                this.showRouteSummary(routeData);
                
            } else {
                throw new Error('Invalid route data received');
            }
            
        } catch (error) {
            this.handleError('Failed to calculate route: ' + error.message);
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Display route on map
     */
    displayRoute(routeData) {
        const coordinates = routeData.geometry.coordinates;
        
        // Update route source
        this.map.getSource('route').setData({
            type: 'Feature',
            properties: {},
            geometry: {
                type: 'LineString',
                coordinates: coordinates
            }
        });
        
        // Fit map to route bounds
        const bounds = new maplibregl.LngLatBounds();
        coordinates.forEach(coord => bounds.extend(coord));
        
        this.map.fitBounds(bounds, {
            padding: 50,
            duration: 1000
        });
    }
    
    /**
     * Show route summary information
     */
    showRouteSummary(routeData) {
        const summary = routeData.summary;
        const accessibility = routeData.accessibility;
        
        let summaryHtml = `
            <div class="route-summary">
                <h4>Route Summary</h4>
                <div class="route-stats">
                    <span class="stat">
                        <strong>Distance:</strong> ${summary.distance}km
                    </span>
                    <span class="stat">
                        <strong>Duration:</strong> ${summary.duration} minutes
                    </span>
                </div>
        `;
        
        if (accessibility) {
            summaryHtml += `
                <div class="accessibility-info">
                    <h5>Accessibility Information</h5>
                    <div class="accessibility-score ${this.getAccessibilityClass(accessibility.score)}">
                        <strong>Accessibility Score:</strong> ${accessibility.score}%
                    </div>
                    <div class="accessibility-details">
                        <span><strong>Max Incline:</strong> ${accessibility.max_incline}%</span>
                        <span><strong>Accessible Distance:</strong> ${accessibility.accessible_distance_km}km</span>
                    </div>
                </div>
            `;
            
            if (accessibility.surface_warnings && accessibility.surface_warnings.length > 0) {
                summaryHtml += `
                    <div class="warnings">
                        <h6>Surface Warnings:</h6>
                        <ul>
                            ${accessibility.surface_warnings.map(warning => `<li>${warning}</li>`).join('')}
                        </ul>
                    </div>
                `;
            }
        }
        
        if (routeData.warnings && routeData.warnings.length > 0) {
            summaryHtml += `
                <div class="route-warnings">
                    <h6>Route Warnings:</h6>
                    <ul>
                        ${routeData.warnings.map(warning => `<li>${warning}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        summaryHtml += '</div>';
        
        // Display summary in designated area or create popup
        const summaryElement = document.getElementById('route-summary');
        if (summaryElement) {
            summaryElement.innerHTML = summaryHtml;
        } else {
            this.showMessage(summaryHtml, 'info', 5000);
        }
    }
    
    /**
     * Get CSS class for accessibility score
     */
    getAccessibilityClass(score) {
        if (score >= 80) return 'accessibility-excellent';
        if (score >= 60) return 'accessibility-good';
        if (score >= 40) return 'accessibility-fair';
        return 'accessibility-poor';
    }
    
    /**
     * Reverse geocode coordinates to address
     */
    async reverseGeocode(lat, lng) {
        try {
            const response = await fetch(`${this.config.apiEndpoint}/geocoding/reverse/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    lat: lat,
                    lng: lng
                })
            });
            
            if (!response.ok) {
                throw new Error('Geocoding request failed');
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('Reverse geocoding failed:', error);
            return null;
        }
    }
    
    /**
     * Check if coordinates are in service area
     */
    isInServiceArea(lat, lng) {
        // Service area bounds for Lisbon district
        const bounds = {
            north: 38.8500,
            south: 38.6000,
            east: -9.0000,
            west: -9.5000
        };
        
        return lat >= bounds.south && lat <= bounds.north &&
               lng >= bounds.west && lng <= bounds.east;
    }
    
    /**
     * Add accessibility-specific controls
     */
    addAccessibilityControls() {
        // Create control container
        const controlContainer = document.createElement('div');
        controlContainer.className = 'maplibregl-ctrl maplibregl-ctrl-group accessibility-controls';
        
        // High contrast toggle
        const contrastBtn = document.createElement('button');
        contrastBtn.className = 'accessibility-btn';
        contrastBtn.innerHTML = '🔆';
        contrastBtn.title = 'Toggle High Contrast';
        contrastBtn.onclick = () => this.toggleHighContrast();
        
        // Zoom to user location
        const locationBtn = document.createElement('button');
        locationBtn.className = 'accessibility-btn';
        locationBtn.innerHTML = '📍';
        locationBtn.title = 'Show My Location';
        locationBtn.onclick = () => this.showUserLocation();
        
        // Clear route
        const clearBtn = document.createElement('button');
        clearBtn.className = 'accessibility-btn';
        clearBtn.innerHTML = '🗑️';
        clearBtn.title = 'Clear Route';
        clearBtn.onclick = () => this.clearRoute();
        
        controlContainer.appendChild(contrastBtn);
        controlContainer.appendChild(locationBtn);
        controlContainer.appendChild(clearBtn);
        
        // Add to map
        this.map.getContainer().appendChild(controlContainer);
    }
    
    /**
     * Toggle high contrast mode
     */
    toggleHighContrast() {
        const mapContainer = this.map.getContainer();
        mapContainer.classList.toggle('high-contrast');
        
        // Update map style for high contrast
        if (mapContainer.classList.contains('high-contrast')) {
            this.map.setPaintProperty('roads', 'line-color', '#000000');
            this.map.setPaintProperty('buildings', 'fill-color', '#ffffff');
            this.map.setPaintProperty('background', 'background-color', '#ffffff');
        } else {
            // Reset to original colors
            this.map.setPaintProperty('roads', 'line-color', [
                "case",
                ["==", ["get", "kind"], "highway"], "#e74694",
                ["==", ["get", "kind"], "major_road"], "#fb923c",
                ["==", ["get", "kind"], "minor_road"], "#94a3b8",
                "#cbd5e1"
            ]);
            this.map.setPaintProperty('buildings', 'fill-color', '#e2e8f0');
            this.map.setPaintProperty('background', 'background-color', '#f8f9fa');
        }
    }
    
    /**
     * Show user's current location
     */
    showUserLocation() {
        if (!navigator.geolocation) {
            this.showMessage('Geolocation is not supported by this browser', 'error');
            return;
        }
        
        this.setLoading(true);
        
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                
                if (this.isInServiceArea(latitude, longitude)) {
                    this.map.flyTo({
                        center: [longitude, latitude],
                        zoom: 15,
                        duration: 2000
                    });
                    
                    // Add temporary marker
                    const userMarker = new maplibregl.Marker({ color: '#ff0000' })
                        .setLngLat([longitude, latitude])
                        .addTo(this.map);
                    
                    // Remove marker after 5 seconds
                    setTimeout(() => userMarker.remove(), 5000);
                    
                    this.showMessage('Current location found', 'success');
                } else {
                    this.showMessage('Your location is outside our service area', 'warning');
                }
                
                this.setLoading(false);
            },
            (error) => {
                this.handleError('Could not get your location: ' + error.message);
                this.setLoading(false);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    }
    
    /**
     * Clear current route and markers
     */
    clearRoute() {
        // Clear route data
        this.map.getSource('route').setData({
            type: 'Feature',
            properties: {},
            geometry: {
                type: 'LineString',
                coordinates: []
            }
        });
        
        // Remove markers
        Object.values(this.markers).forEach(marker => {
            if (marker) marker.remove();
        });
        
        // Reset state
        this.markers = { pickup: null, dropoff: null };
        this.selectedLocations = { pickup: null, dropoff: null };
        this.currentRoute = null;
        
        // Clear summary
        const summaryElement = document.getElementById('route-summary');
        if (summaryElement) {
            summaryElement.innerHTML = '';
        }
        
        this.showMessage('Route cleared', 'info');
    }
    
    /**
     * Set loading state
     */
    setLoading(isLoading) {
        this.isLoading = isLoading;
        const mapContainer = this.map.getContainer();
        
        if (isLoading) {
            mapContainer.classList.add('loading');
        } else {
            mapContainer.classList.remove('loading');
        }
    }
    
    /**
     * Show message to user
     */
    showMessage(message, type = 'info', duration = 3000) {
        // Create message element
        const messageEl = document.createElement('div');
        messageEl.className = `map-message map-message-${type}`;
        messageEl.innerHTML = message;
        
        // Add to map container
        const mapContainer = this.map.getContainer();
        mapContainer.appendChild(messageEl);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, duration);
    }
    
    /**
     * Handle errors
     */
    handleError(message) {
        console.error('Map Error:', message);
        this.showMessage(message, 'error');
        
        if (this.callbacks.onError) {
            this.callbacks.onError(message);
        }
    }
    
    /**
     * Get CSRF token for API requests
     */
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        // Fallback to meta tag
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
    
    /**
     * Get current route data
     */
    getRoute() {
        return this.currentRoute;
    }
    
    /**
     * Get selected locations
     */
    getSelectedLocations() {
        return this.selectedLocations;
    }
    
    /**
     * Programmatically set pickup location
     */
    setPickupLocation(lat, lng, address) {
        this.selectedLocations.pickup = { lat, lng, address };
        this.addMarker(lat, lng, 'pickup', address);
        
        if (this.selectedLocations.dropoff) {
            this.calculateRoute();
        }
    }
    
    /**
     * Programmatically set dropoff location
     */
    setDropoffLocation(lat, lng, address) {
        this.selectedLocations.dropoff = { lat, lng, address };
        this.addMarker(lat, lng, 'dropoff', address);
        
        if (this.selectedLocations.pickup) {
            this.calculateRoute();
        }
    }
    
    /**
     * Destroy map instance
     */
    destroy() {
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    }
}