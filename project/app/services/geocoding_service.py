"""
Geocoding service for address validation and route calculations.
Abstraction layer for geographic operations.
"""

import requests
import logging
from typing import Dict, Optional, Tuple
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for geocoding and route calculations"""
    
    # Cache settings
    CACHE_TIMEOUT = 86400  # 24 hours for geocoding results
    ROUTE_CACHE_TIMEOUT = 3600  # 1 hour for route calculations
    
    def __init__(self):
        # In production, use appropriate geocoding API (Google Maps, Mapbox, etc.)
        self.api_key = getattr(settings, 'GEOCODING_API_KEY', '')
        self.base_url = getattr(settings, 'GEOCODING_API_URL', '')
    
    def geocode(self, address: str) -> Optional[Dict[str, float]]:
        """
        Convert address to coordinates.
        
        Args:
            address: Address string to geocode
            
        Returns:
            Dict with 'lat' and 'lng' or None if failed
        """
        # Check cache first
        cache_key = f"geocode:{address}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # In production, make actual API call
            # For now, return mock data for common Lisbon locations
            mock_locations = {
                "Hospital São José": {"lat": 38.7223, "lng": -9.1393},
                "Hospital Santa Maria": {"lat": 38.7492, "lng": -9.1607},
                "Rossio": {"lat": 38.7139, "lng": -9.1394},
                "Belém": {"lat": 38.6968, "lng": -9.2034},
                "Marquês de Pombal": {"lat": 38.7205, "lng": -9.1495},
                "Aeroporto de Lisboa": {"lat": 38.7756, "lng": -9.1354},
                "Cascais": {"lat": 38.6968, "lng": -9.4215},
                "Sintra": {"lat": 38.8029, "lng": -9.3817},
            }
            
            # Simple matching
            for location, coords in mock_locations.items():
                if location.lower() in address.lower():
                    cache.set(cache_key, coords, self.CACHE_TIMEOUT)
                    return coords
            
            # Default to Lisbon center if not found
            default_coords = {"lat": 38.7223, "lng": -9.1393}
            cache.set(cache_key, default_coords, self.CACHE_TIMEOUT)
            return default_coords
            
        except Exception as e:
            logger.error(f"Geocoding error for address '{address}': {e}")
            return None
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        """
        Convert coordinates to address.
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            Address string or None if failed
        """
        cache_key = f"reverse_geocode:{lat},{lng}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # In production, make actual API call
            # For now, return mock address
            address = f"Rua Example {int(abs(lat*100) % 100)}, Lisboa"
            cache.set(cache_key, address, self.CACHE_TIMEOUT)
            return address
            
        except Exception as e:
            logger.error(f"Reverse geocoding error for {lat},{lng}: {e}")
            return None
    
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
            
            cache.set(cache_key, result, self.ROUTE_CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Route calculation error: {e}")
            # Return reasonable defaults
            return {
                'distance_km': 10.0,
                'duration_minutes': 30,
            }
    
    def validate_service_area(
        self,
        lat: float,
        lng: float
    ) -> bool:
        """
        Check if coordinates are within service area.
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            True if within service area
        """
        # Define service area boundaries (Greater Lisbon area)
        service_area = {
            'north': 38.8500,
            'south': 38.6000,
            'east': -9.0000,
            'west': -9.5000,
        }
        
        return (
            service_area['south'] <= lat <= service_area['north'] and
            service_area['west'] <= lng <= service_area['east']
        )
    
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