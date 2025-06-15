from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from .models import (
    Rider, Ride, Driver, Vehicle, DriverDocument, VehicleDocument, 
    VehiclePhoto, TrainingModule, DriverTraining, DriverRide, 
    RideAnalytics, DriverPerformance, DriverSession
)

@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at']

@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ['rider', 'pickup_location', 'dropoff_location', 'pickup_datetime', 'status']
    list_filter = ['status', 'pickup_datetime', 'created_at']
    search_fields = ['rider__user__username', 'pickup_location', 'dropoff_location']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-pickup_datetime']


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'application_status', 'background_check_status_display', 'training_progress_display', 'is_active', 'created_at']
    list_filter = ['application_status', 'background_check_status', 'is_active', 'background_check_consent', 'training_completed', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone_number']
    readonly_fields = ['created_at', 'updated_at', 'total_rides', 'rating']
    ordering = ['-created_at']
    
    def background_check_status_display(self, obj):
        if obj.background_check_status == 'pending':
            return '⏳ Pending'
        elif obj.background_check_status == 'approved':
            return '✅ Approved'
        elif obj.background_check_status == 'rejected':
            return '❌ Rejected'
        return obj.background_check_status
    background_check_status_display.short_description = 'Background Check'
    
    def training_progress_display(self, obj):
        from .models import TrainingModule
        mandatory_modules = TrainingModule.objects.filter(is_mandatory=True)
        completed_training = obj.training_progress.filter(
            module__is_mandatory=True,
            completed_at__isnull=False,
            quiz_score__gte=80
        )
        
        total_mandatory = mandatory_modules.count()
        completed_count = completed_training.count()
        
        if total_mandatory == 0:
            return 'No modules'
        
        percentage = (completed_count / total_mandatory) * 100
        
        if obj.training_completed:
            return f'✅ Complete ({completed_count}/{total_mandatory})'
        elif completed_count == 0:
            return f'⭕ Not started (0/{total_mandatory})'
        else:
            return f'⏳ {completed_count}/{total_mandatory} ({percentage:.0f}%)'
    
    training_progress_display.short_description = 'Training Progress'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'phone_number', 'fleet_size', 'application_status')
        }),
        ('Background Check', {
            'fields': ('background_check_consent', 'background_check_status', 'background_check_date'),
            'description': '⚠️ Important: Set background check status to "approved" to allow driver to register their vehicle.'
        }),
        ('Eligibility', {
            'fields': ('has_portuguese_license', 'has_accessible_vehicle', 'authorized_to_work')
        }),
        ('Professional Info', {
            'fields': ('years_driving', 'previous_platforms', 'disability_experience', 'languages'),
            'classes': ('collapse',)
        }),
        ('Availability', {
            'fields': ('working_hours', 'working_days', 'expected_trips_per_week'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_available', 'rating', 'total_rides')
        }),
        ('Training', {
            'fields': ('training_completed', 'assessment_passed', 'accessibility_training')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_background_check', 'reject_background_check', 'reset_background_check']
    
    def approve_background_check(self, request, queryset):
        approved_count = 0
        for driver in queryset:
            if driver.application_status == 'background_check_pending' and driver.background_check_consent:
                driver.background_check_status = 'approved'
                driver.background_check_date = timezone.now().date()
                driver.save()
                approved_count += 1
                messages.success(request, f'Background check approved for {driver.user.get_full_name() or driver.user.username}')
            else:
                messages.warning(request, f'Cannot approve background check for {driver.user.get_full_name() or driver.user.username} - not in correct status')
        
        if approved_count > 0:
            messages.info(request, f'Total {approved_count} background check(s) approved.')
    
    approve_background_check.short_description = "✅ Approve background check"
    
    def reject_background_check(self, request, queryset):
        rejected_count = 0
        for driver in queryset:
            if driver.application_status == 'background_check_pending':
                driver.background_check_status = 'rejected'
                driver.background_check_date = timezone.now().date()
                driver.application_status = 'rejected'
                driver.save()
                rejected_count += 1
                messages.error(request, f'Background check rejected for {driver.user.get_full_name() or driver.user.username}')
        
        if rejected_count > 0:
            messages.info(request, f'Total {rejected_count} background check(s) rejected.')
    
    reject_background_check.short_description = "❌ Reject background check"
    
    def reset_background_check(self, request, queryset):
        reset_count = 0
        for driver in queryset:
            driver.background_check_status = 'pending'
            driver.background_check_date = None
            driver.save()
            reset_count += 1
        
        messages.info(request, f'{reset_count} background check(s) reset to pending.')
    
    reset_background_check.short_description = "🔄 Reset background check to pending"


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['driver', 'make', 'model', 'year', 'license_plate', 'vehicle_type', 'is_active']
    list_filter = ['vehicle_type', 'is_active', 'has_ramp', 'has_lift', 'year']
    search_fields = ['driver__user__username', 'make', 'model', 'license_plate']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('driver', 'make', 'model', 'year', 'color', 'license_plate', 'vehicle_type')
        }),
        ('Accessibility Features', {
            'fields': ('wheelchair_capacity', 'has_ramp', 'has_lift', 'has_lowered_floor', 
                      'has_swivel_seats', 'has_hand_controls', 'door_width_cm', 'extra_features')
        }),
        ('Documentation', {
            'fields': ('insurance_expiry', 'inspection_expiry')
        }),
        ('Safety & Status', {
            'fields': ('safety_equipment', 'is_active', 'verification_status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DriverDocument)
class DriverDocumentAdmin(admin.ModelAdmin):
    list_display = ['driver', 'document_type', 'verified', 'uploaded_at']
    list_filter = ['document_type', 'verified', 'uploaded_at']
    search_fields = ['driver__user__username', 'driver__user__email']
    readonly_fields = ['uploaded_at']
    ordering = ['-uploaded_at']


@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'document_type', 'expiry_date', 'verified', 'uploaded_at']
    list_filter = ['document_type', 'verified', 'uploaded_at']
    search_fields = ['vehicle__driver__user__username', 'vehicle__license_plate']
    readonly_fields = ['uploaded_at']
    ordering = ['-uploaded_at']


@admin.register(VehiclePhoto)
class VehiclePhotoAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'photo_type', 'uploaded_at']
    list_filter = ['photo_type', 'uploaded_at']
    search_fields = ['vehicle__driver__user__username', 'vehicle__license_plate']
    readonly_fields = ['uploaded_at']
    ordering = ['-uploaded_at']


@admin.register(TrainingModule)
class TrainingModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'duration_minutes', 'is_mandatory', 'order']
    list_filter = ['is_mandatory']
    search_fields = ['title']
    ordering = ['order']


@admin.register(DriverTraining)
class DriverTrainingAdmin(admin.ModelAdmin):
    list_display = ['driver', 'module', 'status_display', 'quiz_score', 'attempts', 'started_at']
    list_filter = ['completed_at', 'module__is_mandatory', 'module__title', 'driver__application_status']
    search_fields = ['driver__user__username', 'driver__user__email', 'module__title']
    readonly_fields = ['started_at']
    ordering = ['-started_at']
    
    def status_display(self, obj):
        if obj.is_completed:
            return f'✅ Completed ({obj.quiz_score}%)'
        elif obj.quiz_score:
            return f'❌ Failed ({obj.quiz_score}%)'
        else:
            return '⏳ In Progress'
    status_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('driver__user', 'module')
    
    actions = ['reset_training_progress']
    
    def reset_training_progress(self, request, queryset):
        reset_count = 0
        for training in queryset:
            training.completed_at = None
            training.quiz_score = None
            training.attempts = 0
            training.save()
            reset_count += 1
        
        messages.info(request, f'{reset_count} training progress(es) reset.')
    
    reset_training_progress.short_description = "🔄 Reset training progress"


@admin.register(DriverRide)
class DriverRideAdmin(admin.ModelAdmin):
    list_display = ['id', 'driver', 'ride_datetime', 'status', 'total_fare', 'driver_rating', 'payment_method']
    list_filter = ['ride__status', 'payment_method', 'wheelchair_used', 'created_at']
    search_fields = ['driver__user__username', 'driver__user__email', 'ride__pickup_location', 'ride__dropoff_location']
    readonly_fields = ['created_at', 'updated_at', 'response_time_seconds', 'total_duration_minutes']
    ordering = ['-created_at']
    
    def ride_datetime(self, obj):
        return obj.ride.pickup_datetime
    ride_datetime.short_description = 'Pickup Time'
    
    def status(self, obj):
        return obj.ride.get_status_display()
    status.short_description = 'Status'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('ride', 'driver', 'vehicle')
        }),
        ('Timing', {
            'fields': ('accepted_at', 'arrived_at', 'started_at', 'completed_at', 'response_time_seconds', 'total_duration_minutes')
        }),
        ('Route & Distance', {
            'fields': ('distance_km', 'duration_minutes', 'route_polyline')
        }),
        ('Financial', {
            'fields': ('base_fare', 'distance_fare', 'time_fare', 'accessibility_fee', 'total_fare', 
                      'driver_earnings', 'platform_fee', 'payment_method')
        }),
        ('Ratings & Feedback', {
            'fields': ('driver_rating', 'rider_rating', 'driver_comment', 'rider_comment')
        }),
        ('Accessibility', {
            'fields': ('wheelchair_used', 'assistance_provided', 'equipment_used')
        }),
        ('Performance', {
            'fields': ('pickup_delay_minutes', 'route_efficiency')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RideAnalytics)
class RideAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['driver_ride', 'pickup_zone', 'day_of_week', 'hour_of_day', 'is_peak_hour', 'revenue_per_km']
    list_filter = ['is_peak_hour', 'is_weekend', 'is_holiday', 'day_of_week', 'pickup_zone']
    search_fields = ['driver_ride__driver__user__username', 'pickup_zone', 'dropoff_zone']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Ride Reference', {
            'fields': ('driver_ride',)
        }),
        ('Location Analytics', {
            'fields': ('pickup_zone', 'dropoff_zone', 'pickup_lat', 'pickup_lng', 'dropoff_lat', 'dropoff_lng')
        }),
        ('Time Analytics', {
            'fields': ('day_of_week', 'hour_of_day', 'is_peak_hour', 'is_weekend', 'is_holiday')
        }),
        ('Weather', {
            'fields': ('weather_condition', 'temperature_celsius')
        }),
        ('Efficiency Metrics', {
            'fields': ('idle_time_minutes', 'fuel_efficiency_score', 'revenue_per_km', 'revenue_per_minute')
        }),
    )


@admin.register(DriverPerformance)
class DriverPerformanceAdmin(admin.ModelAdmin):
    list_display = ['driver', 'period_type', 'period_start', 'total_rides', 'total_earnings', 'average_rating', 'acceptance_rate']
    list_filter = ['period_type', 'period_start']
    search_fields = ['driver__user__username', 'driver__user__email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-period_start']
    
    fieldsets = (
        ('Period Information', {
            'fields': ('driver', 'period_type', 'period_start', 'period_end')
        }),
        ('Activity Metrics', {
            'fields': ('total_rides', 'total_hours_online', 'total_distance_km', 'acceptance_rate', 'cancellation_rate')
        }),
        ('Financial Metrics', {
            'fields': ('total_earnings', 'average_fare', 'total_tips', 'fuel_costs')
        }),
        ('Quality Metrics', {
            'fields': ('average_rating', 'total_5_star_rides', 'total_complaints', 'on_time_arrival_rate')
        }),
        ('Accessibility Metrics', {
            'fields': ('total_wheelchair_rides', 'accessibility_rating', 'assistance_provided_count')
        }),
        ('Efficiency Metrics', {
            'fields': ('average_pickup_time', 'utilization_rate', 'peak_hours_coverage')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DriverSession)
class DriverSessionAdmin(admin.ModelAdmin):
    list_display = ['driver', 'started_at', 'ended_at', 'duration_hours', 'total_rides', 'total_earnings']
    list_filter = ['started_at', 'driver__is_active']
    search_fields = ['driver__user__username', 'driver__user__email']
    readonly_fields = ['created_at', 'duration_hours', 'active_time_hours']
    ordering = ['-started_at']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('driver', 'started_at', 'ended_at', 'duration_hours', 'active_time_hours')
        }),
        ('Location', {
            'fields': ('start_location', 'end_location')
        }),
        ('Metrics', {
            'fields': ('total_rides', 'total_earnings', 'total_distance_km', 'break_time_minutes')
        }),
    )
