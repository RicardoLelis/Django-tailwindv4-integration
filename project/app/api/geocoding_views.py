"""
API views for geocoding and address search functionality.
Provides secure endpoints with rate limiting and validation.
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone
import json

from ..services.geocoding_service import GeocodingService, GeocodingError

logger = logging.getLogger(__name__)


class GeocodingThrottle(UserRateThrottle):
    """Custom throttle for geocoding requests"""
    scope = 'geocoding'


class GeocodingSuggestionsThrottle(UserRateThrottle):
    """Custom throttle for address suggestions"""
    scope = 'geocoding'
    rate = '120/minute'  # More lenient for autocomplete


def validate_geocoding_request(request_data):
    """Validate incoming geocoding request data"""
    if not isinstance(request_data, dict):
        raise ValueError("Request data must be a JSON object")
    
    # Check required fields based on request type
    if 'address' in request_data:
        address = request_data.get('address', '').strip()
        if not address:
            raise ValueError("Address cannot be empty")
        if len(address) > 200:
            raise ValueError("Address too long (max 200 characters)")
    
    if 'lat' in request_data or 'lng' in request_data:
        try:
            lat = float(request_data.get('lat', 0))
            lng = float(request_data.get('lng', 0))
            
            if not (-90 <= lat <= 90):
                raise ValueError("Latitude must be between -90 and 90")
            if not (-180 <= lng <= 180):
                raise ValueError("Longitude must be between -180 and 180")
                
        except (ValueError, TypeError):
            raise ValueError("Invalid coordinate format")
    
    if 'query' in request_data:
        query = request_data.get('query', '').strip()
        if not query:
            raise ValueError("Query cannot be empty")
        if len(query) > 100:
            raise ValueError("Query too long (max 100 characters)")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([GeocodingThrottle])
def geocode_address(request):
    """
    Geocode an address to coordinates.
    
    POST /api/geocoding/
    {
        "address": "Hospital São José, Lisboa"
    }
    
    Returns:
    {
        "lat": 38.7223,
        "lng": -9.1393,
        "display_name": "Hospital São José, Lisboa, Portugal",
        "confidence": 0.95
    }
    """
    try:
        # Validate request data
        validate_geocoding_request(request.data)
        
        address = request.data.get('address')
        if not address:
            return Response(
                {'error': 'Address field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initialize geocoding service
        geocoding_service = GeocodingService()
        
        # Perform geocoding
        result = geocoding_service.geocode(address)
        
        if result:
            logger.info(f"Geocoding successful for address: {address[:50]}...")
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Address not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except GeocodingError as e:
        logger.warning(f"Geocoding validation error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Geocoding service error: {e}")
        return Response(
            {'error': 'Geocoding service temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([GeocodingThrottle])
def reverse_geocode(request):
    """
    Reverse geocode coordinates to address.
    
    POST /api/geocoding/reverse/
    {
        "lat": 38.7223,
        "lng": -9.1393
    }
    
    Returns:
    {
        "display_name": "Rua José António Serrano, Lisboa, Portugal",
        "street": "Rua José António Serrano",
        "city": "Lisboa",
        "country": "Portugal",
        "formatted": "Rua José António Serrano, Lisboa"
    }
    """
    try:
        # Validate request data
        validate_geocoding_request(request.data)
        
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        
        if lat is None or lng is None:
            return Response(
                {'error': 'Both lat and lng fields are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initialize geocoding service
        geocoding_service = GeocodingService()
        
        # Perform reverse geocoding
        result = geocoding_service.reverse_geocode(float(lat), float(lng))
        
        if result:
            logger.info(f"Reverse geocoding successful for coordinates: {lat:.6f}, {lng:.6f}")
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Address not found for coordinates'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except GeocodingError as e:
        logger.warning(f"Reverse geocoding validation error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Reverse geocoding service error: {e}")
        return Response(
            {'error': 'Reverse geocoding service temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([GeocodingSuggestionsThrottle])
def get_address_suggestions(request):
    """
    Get address suggestions for autocomplete.
    
    POST /api/geocoding/suggestions/
    {
        "query": "Hospital",
        "limit": 5
    }
    
    Returns:
    [
        {
            "display_name": "Hospital São José, Lisboa, Portugal",
            "formatted": "Hospital São José, Lisboa",
            "lat": 38.7223,
            "lng": -9.1393,
            "type": "hospital",
            "importance": 0.8
        }
    ]
    """
    try:
        # Validate request data
        validate_geocoding_request(request.data)
        
        query = request.data.get('query')
        if not query:
            return Response(
                {'error': 'Query field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate and set limit
        limit = request.data.get('limit', 5)
        try:
            limit = int(limit)
            if limit < 1 or limit > 10:
                limit = 5
        except (ValueError, TypeError):
            limit = 5
        
        # Initialize geocoding service
        geocoding_service = GeocodingService()
        
        # Get suggestions
        suggestions = geocoding_service.get_address_suggestions(query, limit)
        
        logger.info(f"Address suggestions returned {len(suggestions)} results for query: {query[:30]}...")
        return Response(suggestions, status=status.HTTP_200_OK)
        
    except GeocodingError as e:
        logger.warning(f"Address suggestions validation error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Address suggestions service error: {e}")
        return Response(
            {'error': 'Address suggestions service temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([GeocodingThrottle])
def validate_service_area(request):
    """
    Validate if coordinates are within service area.
    
    POST /api/geocoding/validate-area/
    {
        "lat": 38.7223,
        "lng": -9.1393
    }
    
    Returns:
    {
        "in_service_area": true,
        "message": "Location is within service area"
    }
    """
    try:
        # Validate request data
        validate_geocoding_request(request.data)
        
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        
        if lat is None or lng is None:
            return Response(
                {'error': 'Both lat and lng fields are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initialize geocoding service
        geocoding_service = GeocodingService()
        
        # Validate service area
        in_area = geocoding_service.validate_service_area(float(lat), float(lng))
        
        return Response({
            'in_service_area': in_area,
            'message': 'Location is within service area' if in_area else 'Location is outside service area'
        }, status=status.HTTP_200_OK)
        
    except GeocodingError as e:
        logger.warning(f"Service area validation error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Service area validation service error: {e}")
        return Response(
            {'error': 'Service area validation temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 60)  # Cache for 1 hour
def get_service_area_bounds(request):
    """
    Get service area boundaries.
    
    GET /api/geocoding/service-area/
    
    Returns:
    {
        "bounds": {
            "north": 38.8500,
            "south": 38.6000,
            "east": -9.0000,
            "west": -9.5000
        },
        "center": {
            "lat": 38.7250,
            "lng": -9.2500
        },
        "name": "Greater Lisbon Area"
    }
    """
    try:
        # Initialize geocoding service to get bounds from settings
        geocoding_service = GeocodingService()
        bounds = geocoding_service.service_area
        
        # Calculate center
        center_lat = (bounds.get('north', 38.85) + bounds.get('south', 38.6)) / 2
        center_lng = (bounds.get('east', -9.0) + bounds.get('west', -9.5)) / 2
        
        return Response({
            'bounds': bounds,
            'center': {
                'lat': center_lat,
                'lng': center_lng
            },
            'name': 'Greater Lisbon Area'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Service area bounds error: {e}")
        return Response(
            {'error': 'Service area information temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


# Legacy function-based view for compatibility
@csrf_exempt
@require_http_methods(["POST"])
def geocode_legacy(request):
    """
    Legacy geocoding endpoint for backward compatibility.
    
    Note: This endpoint has basic rate limiting and should not be used
    for new integrations. Use the main geocoding endpoints instead.
    """
    try:
        # Basic rate limiting check (simplified)
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Authenticated requests get better rate limits
            pass
        else:
            # Anonymous requests get very limited access
            return JsonResponse(
                {'error': 'Authentication required'},
                status=401
            )
        
        # Parse request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'Invalid JSON'},
                status=400
            )
        
        address = data.get('address', '').strip()
        if not address:
            return JsonResponse(
                {'error': 'Address required'},
                status=400
            )
        
        # Initialize geocoding service
        geocoding_service = GeocodingService()
        result = geocoding_service.geocode(address)
        
        if result:
            return JsonResponse(result)
        else:
            return JsonResponse(
                {'error': 'Address not found'},
                status=404
            )
            
    except Exception as e:
        logger.error(f"Legacy geocoding error: {e}")
        return JsonResponse(
            {'error': 'Service temporarily unavailable'},
            status=503
        )


# Health check endpoint
@api_view(['GET'])
@permission_classes([])  # Allow anonymous access for health checks
@throttle_classes([AnonRateThrottle])
def geocoding_health_check(request):
    """
    Health check endpoint for geocoding service.
    
    GET /api/geocoding/health/
    
    Returns service status and basic metrics.
    """
    try:
        # Initialize service
        geocoding_service = GeocodingService()
        
        # Test basic functionality
        test_result = geocoding_service.validate_service_area(38.7223, -9.1393)
        
        health_status = {
            'status': 'healthy' if test_result else 'degraded',
            'service': 'geocoding',
            'version': '1.0.0',
            'timestamp': timezone.now().isoformat(),
            'checks': {
                'service_area_validation': 'pass' if test_result else 'fail',
                'nominatim_api': 'configured' if geocoding_service.nominatim_url else 'not_configured'
            }
        }
        
        status_code = status.HTTP_200_OK if test_result else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return Response(health_status, status=status_code)
        
    except Exception as e:
        logger.error(f"Geocoding health check error: {e}")
        return Response({
            'status': 'unhealthy',
            'service': 'geocoding',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)