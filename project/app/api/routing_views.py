"""
API views for wheelchair-accessible routing functionality.
Provides secure endpoints for route calculation with accessibility features.
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.utils import timezone
import json

from ..services.routing_service import RoutingService, RoutingError

logger = logging.getLogger(__name__)


class RoutingThrottle(UserRateThrottle):
    """Custom throttle for routing requests"""
    scope = 'routing'


def validate_routing_request(request_data):
    """Validate incoming routing request data"""
    if not isinstance(request_data, dict):
        raise ValueError("Request data must be a JSON object")
    
    # Validate coordinates
    coordinates = request_data.get('coordinates', [])
    if not isinstance(coordinates, list):
        raise ValueError("Coordinates must be a list")
    
    if len(coordinates) < 2:
        raise ValueError("At least 2 coordinate pairs required")
    
    if len(coordinates) > 10:
        raise ValueError("Maximum 10 coordinate pairs allowed")
    
    for i, coord in enumerate(coordinates):
        if not isinstance(coord, (list, tuple)) or len(coord) != 2:
            raise ValueError(f"Coordinate {i+1} must have exactly 2 values [lng, lat]")
        
        try:
            lng, lat = float(coord[0]), float(coord[1])
            
            if not (-180 <= lng <= 180):
                raise ValueError(f"Longitude {lng} out of range (-180 to 180)")
            if not (-90 <= lat <= 90):
                raise ValueError(f"Latitude {lat} out of range (-90 to 90)")
                
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid coordinate format at position {i+1}: {e}")
    
    # Validate optional parameters
    preferences = ['shortest', 'fastest', 'recommended']
    if 'preference' in request_data:
        preference = request_data.get('preference')
        if preference not in preferences:
            raise ValueError(f"Preference must be one of: {', '.join(preferences)}")
    
    # Validate boolean parameters
    boolean_params = ['avoid_obstacles', 'avoid_tolls', 'avoid_highways']
    for param in boolean_params:
        if param in request_data:
            value = request_data.get(param)
            if not isinstance(value, bool):
                raise ValueError(f"{param} must be a boolean value")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([RoutingThrottle])
def get_wheelchair_route(request):
    """
    Calculate wheelchair-accessible route.
    
    POST /api/routing/wheelchair/
    {
        "coordinates": [[-9.1393, 38.7223], [-9.1607, 38.7492]],
        "avoid_obstacles": true,
        "preference": "recommended"
    }
    
    Returns:
    {
        "geometry": {
            "type": "LineString",
            "coordinates": [...]
        },
        "summary": {
            "distance": 2.5,
            "duration": 15.0
        },
        "accessibility": {
            "score": 85.0,
            "max_incline": 4.2,
            "surface_warnings": [],
            "accessible_distance_km": 2.3
        },
        "instructions": [...],
        "warnings": [...]
    }
    """
    try:
        # Validate request data
        validate_routing_request(request.data)
        
        coordinates = request.data.get('coordinates')
        avoid_obstacles = request.data.get('avoid_obstacles', True)
        preference = request.data.get('preference', 'recommended')
        
        # Initialize routing service
        routing_service = RoutingService()
        
        # Calculate wheelchair route
        route = routing_service.get_wheelchair_route(
            coordinates=coordinates,
            avoid_obstacles=avoid_obstacles,
            preference=preference
        )
        
        if route:
            logger.info(
                f"Wheelchair route calculated: {route['summary']['distance']}km, "
                f"{route['summary']['duration']} minutes, "
                f"accessibility score: {route.get('accessibility', {}).get('score', 'N/A')}%"
            )
            return Response(route, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'No wheelchair-accessible route found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except RoutingError as e:
        logger.warning(f"Wheelchair routing validation error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Wheelchair routing service error: {e}")
        return Response(
            {'error': 'Wheelchair routing service temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([RoutingThrottle])
def get_driving_route(request):
    """
    Calculate driving route for drivers.
    
    POST /api/routing/driving/
    {
        "coordinates": [[-9.1393, 38.7223], [-9.1607, 38.7492]],
        "avoid_tolls": false,
        "avoid_highways": false
    }
    
    Returns:
    {
        "geometry": {
            "type": "LineString",
            "coordinates": [...]
        },
        "summary": {
            "distance": 2.1,
            "duration": 8.5
        },
        "instructions": [...],
        "profile": "driving",
        "warnings": [...]
    }
    """
    try:
        # Validate request data  
        validate_routing_request(request.data)
        
        coordinates = request.data.get('coordinates')
        avoid_tolls = request.data.get('avoid_tolls', False)
        avoid_highways = request.data.get('avoid_highways', False)
        
        # Initialize routing service
        routing_service = RoutingService()
        
        # Calculate driving route
        route = routing_service.get_driving_route(
            coordinates=coordinates,
            avoid_tolls=avoid_tolls,
            avoid_highways=avoid_highways
        )
        
        if route:
            logger.info(
                f"Driving route calculated: {route['summary']['distance']}km, "
                f"{route['summary']['duration']} minutes"
            )
            return Response(route, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'No driving route found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except RoutingError as e:
        logger.warning(f"Driving routing validation error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Driving routing service error: {e}")
        return Response(
            {'error': 'Driving routing service temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([RoutingThrottle])
def get_multiple_routes(request):
    """
    Get multiple route alternatives for comparison.
    
    POST /api/routing/alternatives/
    {
        "coordinates": [[-9.1393, 38.7223], [-9.1607, 38.7492]],
        "alternatives": 3
    }
    
    Returns:
    [
        {
            "alternative": 0,
            "description": "Recommended wheelchair-accessible route",
            "geometry": {...},
            "summary": {...},
            "accessibility": {...}
        },
        {
            "alternative": 1,
            "description": "Fastest route (may have accessibility challenges)",
            "geometry": {...},
            "summary": {...},
            "accessibility": {...}
        }
    ]
    """
    try:
        # Validate request data
        validate_routing_request(request.data)
        
        coordinates = request.data.get('coordinates')
        alternatives = request.data.get('alternatives', 2)
        
        # Validate alternatives parameter
        try:
            alternatives = int(alternatives)
            if alternatives < 1:
                alternatives = 1
            elif alternatives > 3:
                alternatives = 3
        except (ValueError, TypeError):
            alternatives = 2
        
        # Initialize routing service
        routing_service = RoutingService()
        
        # Get multiple routes
        routes = routing_service.get_multiple_routes(
            coordinates=coordinates,
            alternatives=alternatives
        )
        
        if routes:
            logger.info(f"Multiple routes calculated: {len(routes)} alternatives")
            return Response(routes, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'No alternative routes found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except RoutingError as e:
        logger.warning(f"Alternative routing validation error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Alternative routing service error: {e}")
        return Response(
            {'error': 'Alternative routing service temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([RoutingThrottle])
def calculate_route_accessibility(request):
    """
    Calculate accessibility score for a given route.
    
    POST /api/routing/accessibility/
    {
        "coordinates": [[-9.1393, 38.7223], [-9.1607, 38.7492]]
    }
    
    Returns:
    {
        "accessibility": {
            "score": 85.0,
            "max_incline": 4.2,
            "surface_warnings": ["Cobblestone section detected"],
            "accessible_distance_km": 2.3,
            "total_distance_km": 2.5,
            "recommendations": [
                "Route is suitable for manual wheelchairs",
                "Consider electric wheelchair for incline sections"
            ]
        },
        "summary": {
            "distance": 2.5,
            "duration": 15.0
        }
    }
    """
    try:
        # Validate request data
        validate_routing_request(request.data)
        
        coordinates = request.data.get('coordinates')
        
        # Initialize routing service
        routing_service = RoutingService()
        
        # Get wheelchair route with accessibility focus
        route = routing_service.get_wheelchair_route(
            coordinates=coordinates,
            avoid_obstacles=True,
            preference='recommended'
        )
        
        if route and 'accessibility' in route:
            accessibility = route['accessibility']
            
            # Add recommendations based on score
            recommendations = []
            score = accessibility.get('score', 0)
            max_incline = accessibility.get('max_incline', 0)
            
            if score >= 90:
                recommendations.append("Route is excellent for all wheelchair types")
            elif score >= 80:
                recommendations.append("Route is suitable for manual wheelchairs")
                if max_incline > 5:
                    recommendations.append("Consider electric wheelchair for steep sections")
            elif score >= 60:
                recommendations.append("Route has moderate accessibility challenges")
                recommendations.append("Electric wheelchair recommended")
            else:
                recommendations.append("Route has significant accessibility challenges")
                recommendations.append("Consider alternative transportation")
            
            accessibility['recommendations'] = recommendations
            
            result = {
                'accessibility': accessibility,
                'summary': route.get('summary', {}),
                'warnings': route.get('warnings', [])
            }
            
            logger.info(f"Route accessibility calculated: score {score}%")
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Unable to calculate route accessibility'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except RoutingError as e:
        logger.warning(f"Route accessibility validation error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Route accessibility service error: {e}")
        return Response(
            {'error': 'Route accessibility service temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 30)  # Cache for 30 minutes
def get_routing_capabilities(request):
    """
    Get routing service capabilities and configuration.
    
    GET /api/routing/capabilities/
    
    Returns:
    {
        "profiles": {
            "wheelchair": {
                "available": true,
                "features": ["accessibility_scoring", "incline_avoidance", "surface_analysis"]
            },
            "driving": {
                "available": true,
                "features": ["toll_avoidance", "highway_avoidance", "traffic_aware"]
            }
        },
        "service_area": {
            "bounds": {...},
            "center": {...}
        },
        "limits": {
            "max_coordinates": 10,
            "max_alternatives": 3
        }
    }
    """
    try:
        # Initialize routing service
        routing_service = RoutingService()
        
        capabilities = {
            'profiles': {
                'wheelchair': {
                    'available': True,
                    'features': [
                        'accessibility_scoring',
                        'incline_avoidance', 
                        'surface_analysis',
                        'obstacle_avoidance',
                        'preference_optimization'
                    ],
                    'preferences': ['shortest', 'fastest', 'recommended'],
                    'max_incline': routing_service.route_preferences.get('incline_maximum', 6)
                },
                'driving': {
                    'available': True,
                    'features': [
                        'toll_avoidance',
                        'highway_avoidance',
                        'efficient_routing'
                    ],
                    'avoidance_options': ['tolls', 'highways']
                }
            },
            'service_area': {
                'bounds': routing_service.service_area,
                'center': {
                    'lat': (routing_service.service_area.get('north', 38.85) + 
                           routing_service.service_area.get('south', 38.6)) / 2,
                    'lng': (routing_service.service_area.get('east', -9.0) + 
                           routing_service.service_area.get('west', -9.5)) / 2
                }
            },
            'limits': {
                'max_coordinates': 10,
                'max_alternatives': 3,
                'rate_limit': '100/minute'
            },
            'api_status': {
                'openrouteservice': 'configured' if routing_service.api_key else 'not_configured',
                'fallback': 'available'
            }
        }
        
        return Response(capabilities, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Routing capabilities error: {e}")
        return Response(
            {'error': 'Routing capabilities temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


# Health check endpoint
@api_view(['GET'])
@permission_classes([])  # Allow anonymous access for health checks
@throttle_classes([AnonRateThrottle])
def routing_health_check(request):
    """
    Health check endpoint for routing service.
    
    GET /api/routing/health/
    
    Returns service status and basic metrics.
    """
    try:
        # Initialize service
        routing_service = RoutingService()
        
        # Test basic functionality
        test_coords = [[-9.1393, 38.7223], [-9.1607, 38.7492]]
        
        try:
            validated_coords = routing_service._validate_coordinates(test_coords)
            validation_ok = len(validated_coords) == 2
        except:
            validation_ok = False
        
        health_status = {
            'status': 'healthy' if validation_ok else 'degraded',
            'service': 'routing',
            'version': '1.0.0',
            'timestamp': timezone.now().isoformat(),
            'checks': {
                'coordinate_validation': 'pass' if validation_ok else 'fail',
                'openrouteservice_api': 'configured' if routing_service.api_key else 'not_configured',
                'service_area': 'configured' if routing_service.service_area else 'not_configured',
                'fallback_routing': 'available'
            }
        }
        
        status_code = status.HTTP_200_OK if validation_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return Response(health_status, status=status_code)
        
    except Exception as e:
        logger.error(f"Routing health check error: {e}")
        return Response({
            'status': 'unhealthy',
            'service': 'routing',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)