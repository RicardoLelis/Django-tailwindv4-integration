"""
REST API views for pre-booked rides.
Provides endpoints for mobile apps and external integrations.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
import logging

from ..models import (
    PreBookedRide, DriverCalendar, RideMatchOffer,
    Driver, RecurringRideTemplate
)
from .serializers import (
    PreBookedRideSerializer, DriverCalendarSerializer,
    RideMatchOfferSerializer, RecurringRideTemplateSerializer
)
from ..services.booking_service import BookingService
from ..services.matching_service import MatchingService
from ..services.calendar_service import CalendarService

logger = logging.getLogger(__name__)


class PreBookedRideViewSet(viewsets.ModelViewSet):
    """
    API endpoint for pre-booked rides.
    
    Endpoints:
    - GET /api/bookings/ - List user's bookings
    - POST /api/bookings/ - Create new booking
    - GET /api/bookings/{id}/ - Get booking details
    - PUT /api/bookings/{id}/ - Update booking
    - DELETE /api/bookings/{id}/ - Cancel booking
    - POST /api/bookings/{id}/cancel/ - Cancel with reason
    - GET /api/bookings/{id}/matches/ - Get available drivers
    """
    
    serializer_class = PreBookedRideSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter bookings based on user type"""
        user = self.request.user
        
        # Check if user is a rider
        if hasattr(user, 'rider'):
            return PreBookedRide.objects.filter(
                rider=user.rider
            ).select_related(
                'matched_driver', 'matched_vehicle', 'recurring_template'
            ).order_by('-pickup_datetime')
        
        # Check if user is a driver
        if hasattr(user, 'driver'):
            return PreBookedRide.objects.filter(
                matched_driver=user.driver
            ).select_related(
                'rider', 'matched_vehicle', 'recurring_template'
            ).order_by('-pickup_datetime')
        
        return PreBookedRide.objects.none()
    
    def create(self, request):
        """Create a new pre-booked ride"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Use booking service
            booking_service = BookingService()
            booking = booking_service.create_booking(
                rider=request.user.rider,
                **serializer.validated_data
            )
            
            # Serialize and return
            response_serializer = self.get_serializer(booking)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking with reason"""
        booking = self.get_object()
        reason = request.data.get('reason', 'User requested cancellation')
        
        try:
            booking_service = BookingService()
            success, fee = booking_service.cancel_booking(
                booking, reason, 'rider'
            )
            
            return Response({
                'success': success,
                'cancellation_fee': str(fee) if fee else '0',
                'message': 'Booking cancelled successfully'
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def matches(self, request, pk=None):
        """Get available driver matches for a booking"""
        booking = self.get_object()
        
        if booking.status != 'pending':
            return Response({
                'error': 'Booking already matched'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            matching_service = MatchingService()
            matches = matching_service.find_best_matches(booking)
            
            # Format response
            match_data = []
            for driver, scores in matches:
                match_data.append({
                    'driver_id': driver.id,
                    'driver_name': driver.user.get_full_name(),
                    'rating': float(driver.rating),
                    'total_rides': driver.total_rides,
                    'scores': scores,
                    'vehicle': {
                        'type': driver.vehicles.first().get_vehicle_type_display()
                        if driver.vehicles.exists() else 'Unknown'
                    }
                })
            
            return Response({
                'matches': match_data,
                'count': len(match_data)
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriverCalendarViewSet(viewsets.ModelViewSet):
    """
    API endpoint for driver calendar management.
    
    Endpoints:
    - GET /api/calendar/ - Get driver's calendar
    - POST /api/calendar/ - Create/update availability
    - GET /api/calendar/schedule/ - Get detailed schedule
    - POST /api/calendar/bulk_update/ - Update multiple dates
    """
    
    serializer_class = DriverCalendarSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get calendar entries for authenticated driver"""
        if hasattr(self.request.user, 'driver'):
            return DriverCalendar.objects.filter(
                driver=self.request.user.driver
            ).order_by('date')
        return DriverCalendar.objects.none()
    
    @action(detail=False, methods=['get'])
    def schedule(self, request):
        """Get detailed schedule with bookings"""
        if not hasattr(request.user, 'driver'):
            return Response(
                {'error': 'Not a driver'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get date range from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            calendar_service = CalendarService()
            schedule = calendar_service.get_driver_schedule(
                request.user.driver,
                timezone.datetime.fromisoformat(start_date).date(),
                timezone.datetime.fromisoformat(end_date).date()
            )
            
            return Response(schedule)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Update multiple calendar dates at once"""
        if not hasattr(request.user, 'driver'):
            return Response(
                {'error': 'Not a driver'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        dates = request.data.get('dates', [])
        settings = request.data.get('settings', {})
        
        if not dates:
            return Response(
                {'error': 'No dates provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            calendar_service = CalendarService()
            updated = []
            
            for date_str in dates:
                date = timezone.datetime.fromisoformat(date_str).date()
                calendar = calendar_service.update_driver_availability(
                    driver=request.user.driver,
                    date=date,
                    **settings
                )
                updated.append(calendar)
            
            serializer = self.get_serializer(updated, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RideMatchOfferViewSet(viewsets.ModelViewSet):
    """
    API endpoint for ride match offers.
    
    Endpoints:
    - GET /api/offers/ - List driver's offers
    - GET /api/offers/{id}/ - Get offer details
    - POST /api/offers/{id}/accept/ - Accept offer
    - POST /api/offers/{id}/decline/ - Decline offer
    """
    
    serializer_class = RideMatchOfferSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get offers for authenticated driver"""
        if hasattr(self.request.user, 'driver'):
            return RideMatchOffer.objects.filter(
                driver=self.request.user.driver
            ).select_related(
                'pre_booked_ride',
                'pre_booked_ride__rider'
            ).order_by('-offered_at')
        return RideMatchOffer.objects.none()
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept a ride offer"""
        offer = self.get_object()
        
        if offer.status != 'pending':
            return Response(
                {'error': 'Offer no longer available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            matching_service = MatchingService()
            success = matching_service.handle_offer_response(
                offer, accepted=True
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Offer accepted successfully',
                    'booking_id': offer.pre_booked_ride.id
                })
            else:
                return Response({
                    'error': 'Ride already assigned'
                }, status=status.HTTP_409_CONFLICT)
                
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline a ride offer"""
        offer = self.get_object()
        reason = request.data.get('reason', 'Not available')
        
        try:
            matching_service = MatchingService()
            success = matching_service.handle_offer_response(
                offer,
                accepted=False,
                decline_reason=reason
            )
            
            return Response({
                'success': success,
                'message': 'Offer declined'
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )