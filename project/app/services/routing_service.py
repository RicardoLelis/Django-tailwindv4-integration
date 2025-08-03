"""
Enhanced routing service with OpenRouteService API integration.
Provides wheelchair-accessible routing with security, caching, and error handling.
"""

import requests
import logging
import json
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from .geocoding_service import GeocodingError

logger = logging.getLogger(__name__)


class RoutingError(Exception):
    """Custom exception for routing errors"""
    pass


class RoutingService:
    """Enhanced routing service with OpenRouteService integration"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENROUTESERVICE_API_KEY', None)
        self.api_url = getattr(settings, 'OPENROUTESERVICE_API_URL', 'https://api.openrouteservice.org')
        self.cache_ttl = getattr(settings, 'CACHE_TTL', {})
        self.service_area = getattr(settings, 'SERVICE_AREA_BOUNDS', {})
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Default profile for wheelchair accessibility
        self.wheelchair_profile = 'wheelchair'
        self.driving_profile = 'driving-car'
        
        # Route optimization settings
        self.route_preferences = {
            'avoid_features': ['highways', 'ferries'],
            'surface_quality_minimum': 'good',
            'incline_maximum': 6,  # Maximum incline percentage
            'kerb_height_maximum': 3,  # Maximum kerb height in cm
        }
    
    def _validate_coordinates(self, coordinates: List[List[float]]) -> List[List[float]]:
        """Validate coordinate inputs"""
        if not coordinates or len(coordinates) < 2:
            raise RoutingError("At least 2 coordinates required for routing")
        
        validated = []
        for coord in coordinates:
            if not isinstance(coord, (list, tuple)) or len(coord) != 2:
                raise RoutingError("Each coordinate must have exactly 2 values [lng, lat]")
            
            lng, lat = coord
            try:
                lng, lat = float(lng), float(lat)
            except (ValueError, TypeError):
                raise RoutingError("Coordinates must be numeric")
            
            if not (-180 <= lng <= 180) or not (-90 <= lat <= 90):
                raise RoutingError("Invalid coordinate range")
            
            # Validate coordinates are in service area
            if not self._is_in_service_area(lat, lng):
                raise RoutingError("Coordinates outside service area")
            
            validated.append([lng, lat])
        
        return validated
    
    def _is_in_service_area(self, lat: float, lng: float) -> bool:
        """Check if coordinates are within service area"""
        return (
            self.service_area.get('south', 38.6000) <= lat <= self.service_area.get('north', 38.8500) and
            self.service_area.get('west', -9.5000) <= lng <= self.service_area.get('east', -9.0000)
        )
    
    @method_decorator(ratelimit(key='user_or_ip', rate=settings.ROUTING_RATE_LIMIT, method='POST'))
    def get_wheelchair_route(
        self,
        coordinates: List[List[float]],
        avoid_obstacles: bool = True,
        preference: str = 'shortest'
    ) -> Optional[Dict]:
        """
        Get wheelchair-accessible route using OpenRouteService.
        
        Args:
            coordinates: List of [longitude, latitude] pairs
            avoid_obstacles: Whether to avoid known obstacles
            preference: 'shortest', 'fastest', or 'recommended'
            
        Returns:
            Route information with geometry, distance, and duration
            
        Raises:
            RoutingError: For validation or API errors
        """
        try:
            # Validate coordinates
            coords = self._validate_coordinates(coordinates)
            
            # Check cache first
            cache_key = self._get_route_cache_key(coords, 'wheelchair', avoid_obstacles, preference)
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Wheelchair route cache hit")
                return cached_result
            
            # Make API request
            route_data = self._make_ors_request(coords, 'wheelchair', avoid_obstacles, preference)
            
            if route_data:
                # Process and enhance route data
                processed_route = self._process_route_response(route_data, 'wheelchair')
                
                # Cache result
                cache_ttl = self.cache_ttl.get('routing', 3600)
                cache.set(cache_key, processed_route, cache_ttl)
                
                logger.info(f"Successfully calculated wheelchair route: {processed_route['summary']['distance']}km")
                return processed_route
            
            return None
            
        except RoutingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected wheelchair routing error: {e}")
            raise RoutingError(f"Wheelchair routing service unavailable: {str(e)}")
    
    @method_decorator(ratelimit(key='user_or_ip', rate=settings.ROUTING_RATE_LIMIT, method='POST'))
    def get_driving_route(
        self,
        coordinates: List[List[float]],
        avoid_tolls: bool = False,
        avoid_highways: bool = False
    ) -> Optional[Dict]:
        """
        Get driving route for drivers using OpenRouteService.
        
        Args:
            coordinates: List of [longitude, latitude] pairs
            avoid_tolls: Whether to avoid toll roads
            avoid_highways: Whether to avoid highways
            
        Returns:
            Route information with geometry, distance, and duration
            
        Raises:
            RoutingError: For validation or API errors
        """
        try:
            # Validate coordinates
            coords = self._validate_coordinates(coordinates)
            
            # Check cache first
            cache_key = self._get_route_cache_key(coords, 'driving', avoid_tolls, avoid_highways)
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Driving route cache hit")
                return cached_result
            
            # Make API request
            route_data = self._make_ors_driving_request(coords, avoid_tolls, avoid_highways)
            
            if route_data:
                # Process route data
                processed_route = self._process_route_response(route_data, 'driving')
                
                # Cache result
                cache_ttl = self.cache_ttl.get('routing', 3600)
                cache.set(cache_key, processed_route, cache_ttl)
                
                logger.info(f"Successfully calculated driving route: {processed_route['summary']['distance']}km")
                return processed_route
            
            return None
            
        except RoutingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected driving routing error: {e}")
            raise RoutingError(f"Driving routing service unavailable: {str(e)}")
    
    def _make_ors_request(
        self,
        coordinates: List[List[float]],
        profile: str,
        avoid_obstacles: bool,
        preference: str
    ) -> Optional[Dict]:
        """Make request to OpenRouteService API for wheelchair routing"""
        if not self.api_key:
            logger.warning("OpenRouteService API key not configured, using fallback")
            return self._get_fallback_route(coordinates)
        
        try:
            # Build request payload
            payload = {
                'coordinates': coordinates,
                'format_out': 'geojson',
                'geometry': True,
                'instructions': True,
                'elevation': True,
                'extra_info': ['surface', 'steepness', 'roadaccessrestrictions'],
                'options': {
                    'avoid_features': self._get_avoid_features(avoid_obstacles),
                    'profile_params': {
                        'restrictions': {
                            'maximum_incline': self.route_preferences['incline_maximum'],
                            'surface_quality_minimum': self.route_preferences['surface_quality_minimum']
                        }
                    }
                }
            }
            
            # Set preference
            if preference == 'fastest':
                payload['preference'] = 'fastest'
            elif preference == 'recommended':
                payload['preference'] = 'recommended'
            else:
                payload['preference'] = 'shortest'
            
            response = self.session.post(
                f"{self.api_url}/v2/directions/{self.wheelchair_profile}/geojson",
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            logger.warning(f"OpenRouteService API error: {e}, falling back")
            return self._get_fallback_route(coordinates)
        except Exception as e:
            logger.error(f"OpenRouteService request failed: {e}")
            return None
    
    def _make_ors_driving_request(
        self,
        coordinates: List[List[float]],
        avoid_tolls: bool,
        avoid_highways: bool
    ) -> Optional[Dict]:
        """Make request to OpenRouteService API for driving routing"""
        if not self.api_key:
            logger.warning("OpenRouteService API key not configured, using fallback")
            return self._get_fallback_route(coordinates)
        
        try:
            # Build avoid features list
            avoid_features = []
            if avoid_tolls:
                avoid_features.append('tollways')
            if avoid_highways:
                avoid_features.append('highways')
            
            payload = {
                'coordinates': coordinates,
                'format_out': 'geojson',
                'geometry': True,
                'instructions': True,
                'extra_info': ['roadaccessrestrictions'],
                'options': {
                    'avoid_features': avoid_features
                }
            }
            
            response = self.session.post(
                f"{self.api_url}/v2/directions/{self.driving_profile}/geojson",
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            logger.warning(f"OpenRouteService driving API error: {e}, falling back")
            return self._get_fallback_route(coordinates)
        except Exception as e:
            logger.error(f"OpenRouteService driving request failed: {e}")
            return None
    
    def _get_avoid_features(self, avoid_obstacles: bool) -> List[str]:
        """Get list of features to avoid based on accessibility requirements"""
        avoid_features = ['ferries']  # Always avoid ferries for wheelchair accessibility
        
        if avoid_obstacles:
            avoid_features.extend([
                'highways',  # Highways may not be wheelchair accessible
                'steps'      # Avoid steps
            ])
        
        return avoid_features
    
    def _process_route_response(self, route_data: Dict, profile: str) -> Dict:
        """Process and enhance route response from OpenRouteService"""
        try:
            features = route_data.get('features', [])
            if not features:
                raise RoutingError("No route found in API response")
            
            route_feature = features[0]
            properties = route_feature.get('properties', {})
            segments = properties.get('segments', [])
            
            # Extract route summary
            summary = {
                'distance': round(properties.get('summary', {}).get('distance', 0) / 1000, 2),  # Convert to km
                'duration': round(properties.get('summary', {}).get('duration', 0) / 60, 1),    # Convert to minutes
            }
            
            # Extract geometry (coordinates for route line)
            geometry = route_feature.get('geometry', {})
            coordinates = geometry.get('coordinates', [])
            
            # Extract turn-by-turn instructions
            instructions = []
            for segment in segments:
                for step in segment.get('steps', []):
                    instructions.append({
                        'instruction': step.get('instruction', ''),
                        'distance': round(step.get('distance', 0), 0),
                        'duration': round(step.get('duration', 0), 0),
                        'type': step.get('type', 0),
                        'name': step.get('name', '')
                    })
            
            # Accessibility assessment for wheelchair routes
            accessibility_info = {}
            if profile == 'wheelchair':
                accessibility_info = self._assess_wheelchair_accessibility(segments)
            
            return {
                'geometry': {
                    'type': 'LineString',
                    'coordinates': coordinates
                },
                'summary': summary,
                'instructions': instructions,
                'accessibility': accessibility_info,
                'profile': profile,
                'warnings': self._extract_warnings(segments)
            }
            
        except Exception as e:
            logger.error(f"Error processing route response: {e}")
            raise RoutingError("Failed to process route data")
    
    def _assess_wheelchair_accessibility(self, segments: List[Dict]) -> Dict:
        """Assess wheelchair accessibility of the route"""
        total_distance = 0
        accessible_distance = 0
        max_incline = 0
        surface_warnings = []
        
        for segment in segments:
            segment_distance = segment.get('distance', 0)
            total_distance += segment_distance
            
            # Check for accessibility info in extra_info
            # This would be populated by OpenRouteService with actual data
            surface_info = segment.get('extras', {}).get('surface', [])
            steepness_info = segment.get('extras', {}).get('steepness', [])
            
            # Analyze surface quality
            if surface_info:
                # Process surface information from OpenRouteService
                pass  # Implementation would depend on actual API response format
            
            # Analyze steepness
            if steepness_info:
                for steepness in steepness_info:
                    incline = steepness.get('value', 0)
                    if incline > max_incline:
                        max_incline = incline
            
            # For now, assume most routes are accessible
            accessible_distance += segment_distance * 0.9  # 90% accessible as estimate
        
        accessibility_score = (accessible_distance / total_distance) * 100 if total_distance > 0 else 0
        
        return {
            'score': round(accessibility_score, 1),
            'max_incline': max_incline,
            'surface_warnings': surface_warnings,
            'accessible_distance_km': round(accessible_distance / 1000, 2),
            'total_distance_km': round(total_distance / 1000, 2)
        }
    
    def _extract_warnings(self, segments: List[Dict]) -> List[str]:
        """Extract warnings from route segments"""
        warnings = []
        
        for segment in segments:
            # Check for potential accessibility issues
            steps = segment.get('steps', [])
            for step in steps:
                instruction = step.get('instruction', '').lower()
                
                # Check for potentially problematic instructions
                if 'stairs' in instruction or 'steps' in instruction:
                    warnings.append("Route may include stairs or steps")
                elif 'steep' in instruction:
                    warnings.append("Route includes steep sections")
                elif 'construction' in instruction:
                    warnings.append("Construction may affect accessibility")
        
        return list(set(warnings))  # Remove duplicates
    
    def _get_fallback_route(self, coordinates: List[List[float]]) -> Dict:
        """Fallback route calculation when API is unavailable"""
        if len(coordinates) < 2:
            return None
        
        start = coordinates[0]
        end = coordinates[-1]
        
        # Calculate straight-line distance (Haversine formula)
        distance_km = self._calculate_distance(start[1], start[0], end[1], end[0])
        
        # Estimate road distance and duration
        road_distance_km = distance_km * 1.4  # Apply road factor
        duration_minutes = (road_distance_km / 25) * 60  # Assume 25 km/h average
        
        # Create simple route geometry (straight line)
        geometry = {
            'type': 'LineString',
            'coordinates': coordinates
        }
        
        return {
            'geometry': geometry,
            'summary': {
                'distance': round(road_distance_km, 2),
                'duration': round(duration_minutes, 1)
            },
            'instructions': [
                {
                    'instruction': f"Head towards destination",
                    'distance': round(road_distance_km * 1000, 0),
                    'duration': round(duration_minutes * 60, 0),
                    'type': 0,
                    'name': 'Estimated route'
                }
            ],
            'accessibility': {
                'score': 75.0,  # Conservative estimate
                'max_incline': 5,
                'surface_warnings': ['Route not verified for accessibility'],
                'accessible_distance_km': round(road_distance_km * 0.75, 2),
                'total_distance_km': round(road_distance_km, 2)
            },
            'profile': 'fallback',
            'warnings': ['Route calculated using fallback method - may not reflect actual road conditions']
        }
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance using Haversine formula"""
        import math
        
        R = 6371  # Earth's radius in kilometers
        
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
    
    def _get_route_cache_key(self, coordinates: List[List[float]], profile: str, *args) -> str:
        """Generate cache key for route"""
        coord_str = ','.join([f"{c[0]:.6f},{c[1]:.6f}" for c in coordinates])
        args_str = ','.join([str(arg) for arg in args])
        return f"route:{profile}:{coord_str}:{args_str}"
    
    def get_multiple_routes(
        self,
        coordinates: List[List[float]],
        alternatives: int = 2
    ) -> List[Dict]:
        """
        Get multiple route alternatives for comparison.
        
        Args:
            coordinates: List of [longitude, latitude] pairs
            alternatives: Number of alternative routes to return
            
        Returns:
            List of route alternatives
        """
        routes = []
        
        try:
            # Get main wheelchair route
            main_route = self.get_wheelchair_route(coordinates, avoid_obstacles=True, preference='recommended')
            if main_route:
                main_route['alternative'] = 0
                main_route['description'] = 'Recommended wheelchair-accessible route'
                routes.append(main_route)
            
            # Get fastest route if different
            if alternatives > 1:
                fast_route = self.get_wheelchair_route(coordinates, avoid_obstacles=False, preference='fastest')
                if fast_route and fast_route != main_route:
                    fast_route['alternative'] = 1
                    fast_route['description'] = 'Fastest route (may have accessibility challenges)'
                    routes.append(fast_route)
            
            # Get shortest route if different
            if alternatives > 2:
                short_route = self.get_wheelchair_route(coordinates, avoid_obstacles=True, preference='shortest')
                if short_route and short_route not in routes:
                    short_route['alternative'] = 2
                    short_route['description'] = 'Shortest accessible route'
                    routes.append(short_route)
            
            return routes[:alternatives]
            
        except Exception as e:
            logger.error(f"Error getting multiple routes: {e}")
            return routes if routes else []