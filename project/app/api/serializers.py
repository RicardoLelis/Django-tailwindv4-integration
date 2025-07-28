"""
Serializers for REST API endpoints.
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from ..models import (
    PreBookedRide, DriverCalendar, RideMatchOffer,
    RecurringRideTemplate, Driver, Vehicle, Rider
)


class RiderSerializer(serializers.ModelSerializer):
    """Serializer for rider information"""
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Rider
        fields = ['id', 'username', 'full_name', 'disabilities']


class DriverSerializer(serializers.ModelSerializer):
    """Serializer for driver information"""
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Driver
        fields = [
            'id', 'username', 'full_name', 'rating',
            'total_rides', 'phone_number'
        ]


class VehicleSerializer(serializers.ModelSerializer):
    """Serializer for vehicle information"""
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'make', 'model', 'year', 'license_plate',
            'vehicle_type', 'wheelchair_capacity', 'has_ramp',
            'has_lift', 'is_accessible'
        ]


class PreBookedRideSerializer(serializers.ModelSerializer):
    """Serializer for pre-booked rides"""
    rider = RiderSerializer(read_only=True)
    matched_driver = DriverSerializer(read_only=True)
    matched_vehicle = VehicleSerializer(read_only=True)
    
    # Calculated fields
    time_until_pickup = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    cancellation_fee_estimate = serializers.SerializerMethodField()
    
    class Meta:
        model = PreBookedRide
        fields = [
            'id', 'booking_type', 'purpose', 'pickup_location',
            'dropoff_location', 'pickup_lat', 'pickup_lng',
            'dropoff_lat', 'dropoff_lng', 'pickup_datetime',
            'pickup_window_minutes', 'estimated_duration_minutes',
            'estimated_distance_km', 'special_requirements',
            'wheelchair_required', 'assistance_required',
            'status', 'priority', 'estimated_fare', 'final_fare',
            'rider', 'matched_driver', 'matched_vehicle',
            'created_at', 'updated_at', 'time_until_pickup',
            'can_cancel', 'cancellation_fee_estimate'
        ]
        read_only_fields = [
            'id', 'status', 'matched_driver', 'matched_vehicle',
            'final_fare', 'created_at', 'updated_at'
        ]
    
    def get_time_until_pickup(self, obj):
        """Calculate time remaining until pickup"""
        if obj.pickup_datetime > timezone.now():
            delta = obj.pickup_datetime - timezone.now()
            return {
                'hours': int(delta.total_seconds() // 3600),
                'minutes': int((delta.total_seconds() % 3600) // 60)
            }
        return None
    
    def get_can_cancel(self, obj):
        """Check if ride can be cancelled"""
        return obj.status not in ['completed', 'cancelled', 'in_progress']
    
    def get_cancellation_fee_estimate(self, obj):
        """Estimate cancellation fee"""
        if not self.get_can_cancel(obj):
            return None
        
        hours_until = (obj.pickup_datetime - timezone.now()).total_seconds() / 3600
        
        if hours_until >= 24:
            return "0.00"
        elif hours_until >= 2:
            return "5.00"
        else:
            return str(float(obj.estimated_fare) * 0.5)
    
    def validate_pickup_datetime(self, value):
        """Ensure pickup is at least 2 hours in future"""
        min_time = timezone.now() + timedelta(hours=2)
        if value < min_time:
            raise serializers.ValidationError(
                "Pickup time must be at least 2 hours from now"
            )
        
        max_time = timezone.now() + timedelta(days=30)
        if value > max_time:
            raise serializers.ValidationError(
                "Cannot book more than 30 days in advance"
            )
        
        return value


class DriverCalendarSerializer(serializers.ModelSerializer):
    """Serializer for driver calendar entries"""
    driver_name = serializers.CharField(
        source='driver.user.get_full_name',
        read_only=True
    )
    bookings_count = serializers.IntegerField(
        source='total_bookings',
        read_only=True
    )
    
    class Meta:
        model = DriverCalendar
        fields = [
            'id', 'driver', 'driver_name', 'date', 'start_time',
            'end_time', 'is_available', 'break_slots', 'max_bookings',
            'bookings_count', 'total_estimated_earnings',
            'utilization_percent', 'accepts_wheelchair',
            'accepts_long_distance', 'preferred_zones', 'notes'
        ]
        read_only_fields = [
            'id', 'driver', 'total_estimated_earnings',
            'utilization_percent'
        ]
    
    def validate_date(self, value):
        """Ensure date is not in the past"""
        if value < timezone.now().date():
            raise serializers.ValidationError(
                "Cannot set availability for past dates"
            )
        return value
    
    def validate(self, data):
        """Validate time ranges"""
        if 'start_time' in data and 'end_time' in data:
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError(
                    "End time must be after start time"
                )
        return data


class RideMatchOfferSerializer(serializers.ModelSerializer):
    """Serializer for ride match offers"""
    booking = PreBookedRideSerializer(
        source='pre_booked_ride',
        read_only=True
    )
    driver = DriverSerializer(read_only=True)
    total_fare = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = RideMatchOffer
        fields = [
            'id', 'pre_booked_ride', 'booking', 'driver',
            'offered_at', 'expires_at', 'fare_amount',
            'incentive_amount', 'total_fare', 'status',
            'match_score', 'distance_to_pickup_km',
            'compatibility_notes', 'time_remaining',
            'responded_at', 'decline_reason'
        ]
        read_only_fields = [
            'id', 'offered_at', 'expires_at', 'match_score',
            'distance_to_pickup_km', 'responded_at'
        ]
    
    def get_total_fare(self, obj):
        """Calculate total earnings for driver"""
        return str(obj.total_fare)
    
    def get_time_remaining(self, obj):
        """Calculate time until offer expires"""
        if obj.status == 'pending' and obj.expires_at > timezone.now():
            delta = obj.expires_at - timezone.now()
            return {
                'minutes': int(delta.total_seconds() // 60),
                'seconds': int(delta.total_seconds() % 60)
            }
        return None


class RecurringRideTemplateSerializer(serializers.ModelSerializer):
    """Serializer for recurring ride templates"""
    rider = RiderSerializer(read_only=True)
    preferred_driver = DriverSerializer(read_only=True)
    next_ride_date = serializers.SerializerMethodField()
    
    class Meta:
        model = RecurringRideTemplate
        fields = [
            'id', 'template_name', 'rider', 'recurrence_type',
            'custom_days', 'pickup_location', 'dropoff_location',
            'pickup_time', 'duration_minutes', 'round_trip',
            'purpose', 'special_requirements', 'preferred_driver',
            'is_active', 'start_date', 'end_date',
            'auto_book_days_ahead', 'last_generated_until',
            'next_ride_date', 'total_rides_generated',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'last_generated_until', 'total_rides_generated',
            'created_at', 'updated_at'
        ]
    
    def get_next_ride_date(self, obj):
        """Calculate next scheduled ride date"""
        # This would need actual implementation based on recurrence pattern
        if obj.is_active and obj.start_date >= timezone.now().date():
            return obj.start_date
        return None
    
    def validate_end_date(self, value):
        """Ensure end date is after start date"""
        if value and 'start_date' in self.initial_data:
            start_date = self.initial_data['start_date']
            if value <= start_date:
                raise serializers.ValidationError(
                    "End date must be after start date"
                )
        return value