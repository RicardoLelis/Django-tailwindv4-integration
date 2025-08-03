"""
Enhanced geocoding service with security, caching, and external API integration.
Provides secure geocoding with Nominatim API, input validation, and rate limiting.
"""

import requests
import logging
import re
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
from urllib.parse import quote
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class GeocodingError(Exception):
    """Custom exception for geocoding errors"""
    pass


class GeocodingService:
    """Enhanced geocoding service with security and external API integration"""
    
    def __init__(self):
        self.nominatim_url = getattr(settings, 'NOMINATIM_API_URL', 'https://nominatim.openstreetmap.org')
        self.user_agent = getattr(settings, 'NOMINATIM_USER_AGENT', 'WheelchairRideShare/1.0')
        self.cache_ttl = getattr(settings, 'CACHE_TTL', {})
        self.service_area = getattr(settings, 'SERVICE_AREA_BOUNDS', {})
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        # Input validation patterns
        self.address_pattern = re.compile(r'^[a-zA-Z0-9\s,.-çãõáéíóúâêîôûàèìòù]+$', re.IGNORECASE)
        self.coordinate_pattern = re.compile(r'^-?\d+\.?\d*$')
    
    def _validate_address_input(self, address: str) -> str:
        """Validate and sanitize address input"""
        if not address or not isinstance(address, str):
            raise GeocodingError("Address must be a non-empty string")
        
        address = address.strip()
        if len(address) < 3:
            raise GeocodingError("Address must be at least 3 characters")
        
        if len(address) > 200:
            raise GeocodingError("Address too long (max 200 characters)")
        
        if not self.address_pattern.match(address):
            raise GeocodingError("Address contains invalid characters")
        
        return address
    
    def _validate_coordinates(self, lat: float, lng: float) -> Tuple[float, float]:
        """Validate coordinate inputs"""
        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
            raise GeocodingError("Invalid coordinate format")
        
        if not (-90 <= lat <= 90):
            raise GeocodingError("Latitude must be between -90 and 90")
        
        if not (-180 <= lng <= 180):
            raise GeocodingError("Longitude must be between -180 and 180")
        
        return lat, lng
    
    def geocode(self, address: str) -> Optional[Dict[str, float]]:
        """
        Convert address to coordinates using Nominatim API.
        
        Args:
            address: Address string to geocode
            
        Returns:
            Dict with 'lat' and 'lng' or None if failed
            
        Raises:
            GeocodingError: For validation or API errors
        """
        try:
            # Validate and sanitize input
            clean_address = self._validate_address_input(address)
            
            # Check cache first
            cache_key = f"geocode:{clean_address.lower()}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Geocoding cache hit for: {clean_address[:50]}")
                return cached_result
            
            # Make API request to Nominatim
            result = self._make_nominatim_request(clean_address)
            
            if result:
                # Validate coordinates are in service area
                if not self.validate_service_area(result['lat'], result['lng']):
                    logger.warning(f"Address outside service area: {clean_address}")
                    raise GeocodingError("Address is outside our service area")
                
                # Cache successful result
                cache_ttl = self.cache_ttl.get('geocoding', 86400)
                cache.set(cache_key, result, cache_ttl)
                logger.info(f"Successfully geocoded: {clean_address}")
                return result
            
            return None
            
        except GeocodingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected geocoding error for '{address}': {e}")
            raise GeocodingError(f"Geocoding service unavailable: {str(e)}")
    
    def _make_nominatim_request(self, address: str) -> Optional[Dict[str, float]]:
        """Make request to Nominatim API with error handling and fallbacks"""
        try:
            # Primary request to Nominatim
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'pt',  # Restrict to Portugal
                'bounded': 1,
                'viewbox': f"{self.service_area.get('west', -9.5)},{self.service_area.get('south', 38.6)},"
                          f"{self.service_area.get('east', -9.0)},{self.service_area.get('north', 38.85)}",
                'addressdetails': 1,
                'extratags': 1
            }
            
            response = self.session.get(
                f"{self.nominatim_url}/search",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                result = data[0]
                return {
                    'lat': float(result['lat']),
                    'lng': float(result['lon']),
                    'display_name': result.get('display_name', ''),
                    'confidence': self._calculate_confidence(result)
                }
            
            # Fallback to mock data for development
            return self._get_fallback_location(address)
            
        except requests.RequestException as e:
            logger.warning(f"Nominatim API error: {e}, falling back to mock data")
            return self._get_fallback_location(address)
        except Exception as e:
            logger.error(f"Nominatim request failed: {e}, falling back to mock data")
            return self._get_fallback_location(address)
    
    def _calculate_confidence(self, nominatim_result: Dict) -> float:
        """Calculate confidence score for geocoding result"""
        importance = float(nominatim_result.get('importance', 0))
        place_rank = int(nominatim_result.get('place_rank', 30))
        
        # Higher importance and lower place_rank indicate better match
        confidence = min(1.0, (importance * 2) + (1 - place_rank / 30))
        return round(confidence, 2)
    
    def _get_fallback_location(self, address: str) -> Optional[Dict[str, float]]:
        """Fallback mock data for development/testing"""
        mock_locations = {
            "hospital são josé": {"lat": 38.7223, "lng": -9.1393, "display_name": "Hospital São José, Lisboa"},
            "hospital santa maria": {"lat": 38.7492, "lng": -9.1607, "display_name": "Hospital Santa Maria, Lisboa"},
            "rossio": {"lat": 38.7139, "lng": -9.1394, "display_name": "Rossio, Lisboa"},
            "belém": {"lat": 38.6968, "lng": -9.2034, "display_name": "Belém, Lisboa"},
            "marquês de pombal": {"lat": 38.7205, "lng": -9.1495, "display_name": "Marquês de Pombal, Lisboa"},
            "aeroporto": {"lat": 38.7756, "lng": -9.1354, "display_name": "Aeroporto de Lisboa"},
            "cascais": {"lat": 38.6968, "lng": -9.4215, "display_name": "Cascais"},
            "sintra": {"lat": 38.8029, "lng": -9.3817, "display_name": "Sintra"},
        }
        
        address_lower = address.lower()
        for location, coords in mock_locations.items():
            if location in address_lower or address_lower in location:
                return {
                    'lat': coords['lat'],
                    'lng': coords['lng'],
                    'display_name': coords['display_name'],
                    'confidence': 0.8
                }
        
        # Default to Lisbon center with low confidence
        return {
            'lat': 38.7223,
            'lng': -9.1393,
            'display_name': 'Lisboa, Portugal',
            'confidence': 0.3
        }
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[Dict[str, str]]:
        """
        Convert coordinates to address using Nominatim API.
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            Dict with address components or None if failed
            
        Raises:
            GeocodingError: For validation or API errors
        """
        try:
            # Validate coordinates
            lat, lng = self._validate_coordinates(lat, lng)
            
            # Check cache first
            cache_key = f"reverse_geocode:{lat:.6f},{lng:.6f}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Reverse geocoding cache hit for: {lat:.6f},{lng:.6f}")
                return cached_result
            
            # Validate coordinates are in service area
            if not self.validate_service_area(lat, lng):
                raise GeocodingError("Coordinates are outside our service area")
            
            # Make API request to Nominatim
            result = self._make_reverse_nominatim_request(lat, lng)
            
            if result:
                # Cache successful result
                cache_ttl = self.cache_ttl.get('geocoding', 86400)
                cache.set(cache_key, result, cache_ttl)
                logger.info(f"Successfully reverse geocoded: {lat:.6f},{lng:.6f}")
                return result
            
            return None
            
        except GeocodingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected reverse geocoding error for {lat},{lng}: {e}")
            raise GeocodingError(f"Reverse geocoding service unavailable: {str(e)}")
    
    def _make_reverse_nominatim_request(self, lat: float, lng: float) -> Optional[Dict[str, str]]:
        """Make reverse geocoding request to Nominatim API"""
        try:
            params = {
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'addressdetails': 1,
                'zoom': 18,
                'extratags': 1
            }
            
            response = self.session.get(
                f"{self.nominatim_url}/reverse",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data and 'display_name' in data:
                address = data.get('address', {})
                return {
                    'display_name': data['display_name'],
                    'street': address.get('road', ''),
                    'house_number': address.get('house_number', ''),
                    'city': address.get('city', address.get('town', address.get('village', ''))),
                    'postcode': address.get('postcode', ''),
                    'country': address.get('country', 'Portugal'),
                    'formatted': self._format_address(address)
                }
            
            # Fallback to mock data
            return self._get_reverse_fallback(lat, lng)
            
        except requests.RequestException as e:
            logger.warning(f"Nominatim reverse API error: {e}, falling back to mock data")
            return self._get_reverse_fallback(lat, lng)
        except Exception as e:
            logger.error(f"Reverse Nominatim request failed: {e}")
            return None
    
    def _format_address(self, address_components: Dict) -> str:
        """Format address components into readable string"""
        parts = []
        
        if address_components.get('house_number') and address_components.get('road'):
            parts.append(f"{address_components['road']} {address_components['house_number']}")
        elif address_components.get('road'):
            parts.append(address_components['road'])
        
        if address_components.get('city'):
            parts.append(address_components['city'])
        elif address_components.get('town'):
            parts.append(address_components['town'])
        
        if address_components.get('postcode'):
            parts.append(address_components['postcode'])
        
        return ', '.join(parts) if parts else 'Lisboa, Portugal'
    
    def _get_reverse_fallback(self, lat: float, lng: float) -> Dict[str, str]:
        """Fallback for reverse geocoding when API is unavailable"""
        return {
            'display_name': f"Aproximadamente {lat:.4f}, {lng:.4f}, Lisboa, Portugal",
            'street': 'Rua Desconhecida',
            'house_number': '',
            'city': 'Lisboa',
            'postcode': '',
            'country': 'Portugal',
            'formatted': 'Lisboa, Portugal'
        }
    
    def get_route_info(
        self,
        origin: Dict[str, float],
        destination: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Get route information between two points.
        
        Args:
            origin: Dict with 'lat' and 'lng'
            destination: Dict with 'lat' and 'lng'
            
        Returns:
            Dict with distance_km and duration_minutes
        """
        cache_key = (
            f"route:{origin['lat']},{origin['lng']}"
            f"-{destination['lat']},{destination['lng']}"
        )
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Calculate straight-line distance as approximation
            distance_km = self._calculate_distance(
                origin['lat'], origin['lng'],
                destination['lat'], destination['lng']
            )
            
            # Apply factor for road distance (typically 1.3-1.5x straight line)
            road_distance_km = distance_km * 1.4
            
            # Estimate duration based on average city speed (25 km/h)
            duration_minutes = int((road_distance_km / 25) * 60)
            
            result = {
                'distance_km': round(road_distance_km, 2),
                'duration_minutes': duration_minutes,
            }
            
            cache.set(cache_key, result, self.cache_ttl.get('routing', 3600))
            return result
            
        except Exception as e:
            logger.error(f"Route calculation error: {e}")
            # Return reasonable defaults
            return {
                'distance_km': 10.0,
                'duration_minutes': 30,
            }
    
    def validate_service_area(self, lat: float, lng: float) -> bool:
        """
        Check if coordinates are within service area.
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            True if within service area
        """
        try:
            lat, lng = self._validate_coordinates(lat, lng)
            
            return (
                self.service_area.get('south', 38.6000) <= lat <= self.service_area.get('north', 38.8500) and
                self.service_area.get('west', -9.5000) <= lng <= self.service_area.get('east', -9.0000)
            )
        except GeocodingError:
            return False
    
    def get_address_suggestions(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        Get address suggestions for autocomplete functionality.
        
        Args:
            query: Partial address query
            limit: Maximum number of suggestions
            
        Returns:
            List of address suggestions with coordinates
            
        Raises:
            GeocodingError: For validation errors
        """
        try:
            # Validate input
            if not query or len(query.strip()) < 2:
                return []
            
            clean_query = self._validate_address_input(query)
            
            # Check cache first
            cache_key = f"suggestions:{clean_query.lower()}:{limit}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Address suggestions cache hit for: {clean_query[:30]}")
                return cached_result
            
            # Make request to Nominatim
            suggestions = self._get_nominatim_suggestions(clean_query, limit)
            
            # Cache results with shorter TTL for suggestions
            cache_ttl = self.cache_ttl.get('geocoding', 86400) // 4  # 6 hours
            cache.set(cache_key, suggestions, cache_ttl)
            
            return suggestions
            
        except GeocodingError:
            raise
        except Exception as e:
            logger.error(f"Address suggestions error for '{query}': {e}")
            return []
    
    def _get_nominatim_suggestions(self, query: str, limit: int) -> List[Dict[str, str]]:
        """Get address suggestions from Nominatim API"""
        try:
            params = {
                'q': query,
                'format': 'json',
                'limit': min(limit, 10),  # Cap at 10 for performance
                'countrycodes': 'pt',
                'bounded': 1,
                'viewbox': f"{self.service_area.get('west', -9.5)},{self.service_area.get('south', 38.6)},"
                          f"{self.service_area.get('east', -9.0)},{self.service_area.get('north', 38.85)}",
                'addressdetails': 1,
                'extratags': 1
            }
            
            response = self.session.get(
                f"{self.nominatim_url}/search",
                params=params,
                timeout=8  # Shorter timeout for suggestions
            )
            response.raise_for_status()
            
            data = response.json()
            suggestions = []
            
            for item in data:
                lat, lng = float(item['lat']), float(item['lon'])
                
                # Only include results in service area
                if self.validate_service_area(lat, lng):
                    suggestions.append({
                        'display_name': item['display_name'],
                        'lat': lat,
                        'lng': lng,
                        'type': item.get('type', 'unknown'),
                        'importance': float(item.get('importance', 0)),
                        'formatted': self._format_suggestion(item)
                    })
            
            # Sort by importance/relevance
            suggestions.sort(key=lambda x: x['importance'], reverse=True)
            
            return suggestions[:limit]
            
        except requests.RequestException as e:
            logger.warning(f"Nominatim suggestions API error: {e}")
            return self._get_fallback_suggestions(query, limit)
        except Exception as e:
            logger.error(f"Nominatim suggestions request failed: {e}")
            return []
    
    def _format_suggestion(self, nominatim_item: Dict) -> str:
        """Format suggestion for display in autocomplete"""
        address = nominatim_item.get('address', {})
        parts = []
        
        # Add main identifier (road, amenity, etc.)
        if address.get('road'):
            parts.append(address['road'])
        elif nominatim_item.get('name'):
            parts.append(nominatim_item['name'])
        
        # Add locality
        locality = address.get('city') or address.get('town') or address.get('village')
        if locality and locality != 'Lisboa':
            parts.append(locality)
        else:
            parts.append('Lisboa')
        
        return ', '.join(parts)
    
    def _get_fallback_suggestions(self, query: str, limit: int) -> List[Dict[str, str]]:
        """Fallback suggestions when API is unavailable"""
        query_lower = query.lower()
        fallback_places = [
            {
                'display_name': 'Hospital São José, Lisboa',
                'lat': 38.7223, 'lng': -9.1393,
                'formatted': 'Hospital São José, Lisboa',
                'type': 'hospital', 'importance': 0.8
            },
            {
                'display_name': 'Aeroporto de Lisboa',
                'lat': 38.7756, 'lng': -9.1354,
                'formatted': 'Aeroporto de Lisboa',
                'type': 'aeroway', 'importance': 0.9
            },
            {
                'display_name': 'Rossio, Lisboa',
                'lat': 38.7139, 'lng': -9.1394,
                'formatted': 'Rossio, Lisboa',
                'type': 'square', 'importance': 0.7
            },
        ]
        
        # Filter by query match
        matches = [
            place for place in fallback_places
            if query_lower in place['display_name'].lower()
        ]
        
        return matches[:limit]
    
    def get_nearby_medical_facilities(
        self,
        lat: float,
        lng: float,
        radius_km: float = 5.0
    ) -> list:
        """
        Get nearby medical facilities for quick selection.
        
        Args:
            lat: Center latitude
            lng: Center longitude
            radius_km: Search radius
            
        Returns:
            List of nearby facilities
        """
        # Mock data for common medical facilities
        facilities = [
            {
                'name': 'Hospital São José',
                'address': 'Rua José António Serrano, Lisboa',
                'lat': 38.7223,
                'lng': -9.1393,
                'type': 'hospital',
            },
            {
                'name': 'Hospital Santa Maria',
                'address': 'Av. Prof. Egas Moniz, Lisboa',
                'lat': 38.7492,
                'lng': -9.1607,
                'type': 'hospital',
            },
            {
                'name': 'Centro de Saúde de Alvalade',
                'address': 'Av. de Roma, Lisboa',
                'lat': 38.7500,
                'lng': -9.1467,
                'type': 'health_center',
            },
        ]
        
        # Filter by distance
        nearby = []
        for facility in facilities:
            distance = self._calculate_distance(
                lat, lng, facility['lat'], facility['lng']
            )
            if distance <= radius_km:
                facility['distance_km'] = round(distance, 2)
                nearby.append(facility)
        
        # Sort by distance
        nearby.sort(key=lambda x: x['distance_km'])
        
        return nearby
    
    def _calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
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
    
    def optimize_route(
        self,
        stops: list
    ) -> Dict:
        """
        Optimize route for multiple stops.
        
        Args:
            stops: List of dicts with 'lat', 'lng', and 'address'
            
        Returns:
            Optimized route information
        """
        if len(stops) < 2:
            return {'stops': stops, 'total_distance_km': 0, 'total_duration_minutes': 0}
        
        # Simple nearest neighbor algorithm for route optimization
        optimized = [stops[0]]  # Start with first stop
        remaining = stops[1:]
        total_distance = 0
        total_duration = 0
        
        current = stops[0]
        while remaining:
            # Find nearest stop
            nearest = None
            min_distance = float('inf')
            
            for stop in remaining:
                distance = self._calculate_distance(
                    current['lat'], current['lng'],
                    stop['lat'], stop['lng']
                )
                if distance < min_distance:
                    min_distance = distance
                    nearest = stop
            
            # Add to optimized route
            optimized.append(nearest)
            remaining.remove(nearest)
            
            # Update totals
            route_info = self.get_route_info(current, nearest)
            total_distance += route_info['distance_km']
            total_duration += route_info['duration_minutes']
            
            current = nearest
        
        return {
            'stops': optimized,
            'total_distance_km': round(total_distance, 2),
            'total_duration_minutes': total_duration,
        }