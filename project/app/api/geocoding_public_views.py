"""
Development-only public geocoding endpoints
These endpoints bypass authentication for easier development and testing
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
import json
import logging

from ..services.geocoding_service import GeocodingService, GeocodingError

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='60/m', method='POST')
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
@ratelimit(key='ip', rate='30/m', method='POST')
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