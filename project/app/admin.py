from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from .models import (
    Rider, Ride, Driver, Vehicle, DriverDocument, VehicleDocument, 
    VehiclePhoto, TrainingModule, DriverTraining, DriverRide, 
    RideAnalytics, DriverPerformance, DriverSession,
    PreBookedRide, DriverCalendar, RideMatchOffer, WaitingTimeOptimization,
    RecurringRideTemplate
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


@admin.register(PreBookedRide)
class PreBookedRideAdmin(admin.ModelAdmin):
    list_display = ['id', 'rider', 'pickup_location_short', 'scheduled_pickup_time', 'status', 'assigned_driver', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'scheduled_pickup_time', 'is_flexible', 'created_at']
    search_fields = ['rider__user__username', 'rider__user__email', 'pickup_location', 'dropoff_location', 'assigned_driver__user__username']
    readonly_fields = ['created_at', 'updated_at', 'cancelled_at', 'assignment_confirmed_at', 'rider_notified_at', 'driver_notified_at', 'reminder_sent_at', 'pickup_window_start', 'pickup_window_end', 'is_within_assignment_window', 'can_be_cancelled']
    date_hierarchy = 'scheduled_pickup_time'
    ordering = ['scheduled_pickup_time']
    
    def pickup_location_short(self, obj):
        return obj.pickup_location[:30] + '...' if len(obj.pickup_location) > 30 else obj.pickup_location
    pickup_location_short.short_description = 'Pickup'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('rider', 'status', 'priority')
        }),
        ('Location Details', {
            'fields': ('pickup_location', 'dropoff_location', 'pickup_latitude', 'pickup_longitude', 'dropoff_latitude', 'dropoff_longitude')
        }),
        ('Scheduling', {
            'fields': ('scheduled_pickup_time', 'estimated_duration_minutes', 'pickup_window_minutes', 'is_flexible', 'pickup_window_start', 'pickup_window_end')
        }),
        ('Assignment', {
            'fields': ('assigned_driver', 'assigned_vehicle', 'assignment_confirmed_at', 'is_within_assignment_window')
        }),
        ('Requirements & Notes', {
            'fields': ('special_requirements', 'internal_notes'),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('estimated_fare', 'surge_multiplier')
        }),
        ('Recurring Ride', {
            'fields': ('recurring_template',),
            'classes': ('collapse',)
        }),
        ('Notifications', {
            'fields': ('rider_notified_at', 'driver_notified_at', 'reminder_sent_at'),
            'classes': ('collapse',)
        }),
        ('Cancellation', {
            'fields': ('can_be_cancelled', 'cancelled_at', 'cancelled_by', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['assign_drivers', 'send_reminders', 'cancel_rides']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('rider__user', 'assigned_driver__user', 'assigned_vehicle', 'recurring_template')
    
    def assign_drivers(self, request, queryset):
        pending_rides = queryset.filter(status='pending', scheduled_pickup_time__lte=timezone.now() + timezone.timedelta(hours=24))
        assigned_count = 0
        
        for ride in pending_rides:
            # This would need actual driver matching logic
            messages.info(request, f'Driver assignment needed for ride {ride.id}')
            assigned_count += 1
        
        messages.success(request, f'{assigned_count} rides need driver assignment.')
    assign_drivers.short_description = "Assign drivers to selected rides"
    
    def send_reminders(self, request, queryset):
        upcoming_rides = queryset.filter(
            status__in=['confirmed', 'driver_assigned'],
            scheduled_pickup_time__lte=timezone.now() + timezone.timedelta(hours=2),
            reminder_sent_at__isnull=True
        )
        reminder_count = 0
        
        for ride in upcoming_rides:
            ride.reminder_sent_at = timezone.now()
            ride.save()
            reminder_count += 1
        
        messages.success(request, f'Sent reminders for {reminder_count} rides.')
    send_reminders.short_description = "Send reminders for upcoming rides"
    
    def cancel_rides(self, request, queryset):
        cancellable_rides = queryset.filter(status__in=['pending', 'confirmed'])
        cancelled_count = 0
        
        for ride in cancellable_rides:
            if ride.can_be_cancelled:
                ride.cancel(request.user, 'Admin cancellation')
                cancelled_count += 1
            else:
                messages.warning(request, f'Cannot cancel ride {ride.id} - too close to pickup time')
        
        messages.success(request, f'Cancelled {cancelled_count} rides.')
    cancel_rides.short_description = "Cancel selected rides"


@admin.register(DriverCalendar)
class DriverCalendarAdmin(admin.ModelAdmin):
    list_display = ['driver', 'date', 'start_time', 'end_time', 'status', 'current_bookings', 'max_rides', 'utilization_display', 'accepts_wheelchair']
    list_filter = ['date', 'status', 'accepts_wheelchair', 'accepts_long_distance']
    search_fields = ['driver__user__username', 'driver__user__email', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'available_slots', 'is_fully_booked', 'utilization_percentage']
    date_hierarchy = 'date'
    ordering = ['date', 'start_time']
    
    def utilization_display(self, obj):
        percentage = obj.utilization_percentage
        if percentage >= 80:
            return f'{percentage:.0f}%'
        elif percentage >= 50:
            return f'{percentage:.0f}%'
        else:
            return f'{percentage:.0f}%'
    utilization_display.short_description = 'Utilization'
    
    fieldsets = (
        ('Driver & Date', {
            'fields': ('driver', 'date', 'status')
        }),
        ('Working Hours', {
            'fields': ('start_time', 'end_time', 'break_start', 'break_duration_minutes')
        }),
        ('Capacity', {
            'fields': ('max_rides', 'current_bookings', 'available_slots', 'is_fully_booked', 'utilization_percentage')
        }),
        ('Preferences', {
            'fields': ('accepts_wheelchair', 'accepts_long_distance', 'preferred_zones', 'avoided_zones'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_available', 'mark_as_busy', 'reset_bookings']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('driver__user')
    
    def mark_as_available(self, request, queryset):
        updated = queryset.update(status='available')
        messages.success(request, f'{updated} calendar entries marked as available.')
    mark_as_available.short_description = "Mark as available"
    
    def mark_as_busy(self, request, queryset):
        updated = queryset.update(status='busy')
        messages.success(request, f'{updated} calendar entries marked as busy.')
    mark_as_busy.short_description = "Mark as busy"
    
    def reset_bookings(self, request, queryset):
        updated = queryset.update(current_bookings=0)
        messages.success(request, f'{updated} calendar entries reset.')
    reset_bookings.short_description = "Reset booking counts"


@admin.register(RideMatchOffer)
class RideMatchOfferAdmin(admin.ModelAdmin):
    list_display = ['id', 'pre_booked_ride_info', 'driver', 'status', 'total_earnings', 'compatibility_score', 'distance_to_pickup_km', 'offered_at', 'expires_at']
    list_filter = ['status', 'decline_reason', 'push_notification_sent', 'sms_sent', 'email_sent', 'offered_at']
    search_fields = ['driver__user__username', 'driver__user__email', 'pre_booked_ride__pickup_location', 'decline_notes']
    readonly_fields = ['created_at', 'updated_at', 'offered_at', 'responded_at', 'is_expired', 'time_to_respond', 'response_time_seconds']
    ordering = ['priority_rank', '-offered_at']
    
    def pre_booked_ride_info(self, obj):
        return f"Ride #{obj.pre_booked_ride.id} - {obj.pre_booked_ride.scheduled_pickup_time.strftime('%m/%d %H:%M')}"
    pre_booked_ride_info.short_description = 'Pre-booked Ride'
    
    fieldsets = (
        ('Ride & Driver', {
            'fields': ('pre_booked_ride', 'driver', 'status', 'priority_rank')
        }),
        ('Offer Details', {
            'fields': ('offered_at', 'expires_at', 'responded_at', 'is_expired', 'time_to_respond', 'response_time_seconds')
        }),
        ('Financial', {
            'fields': ('base_fare', 'bonus_amount', 'total_earnings')
        }),
        ('Match Quality', {
            'fields': ('distance_to_pickup_km', 'estimated_arrival_time', 'compatibility_score')
        }),
        ('Response', {
            'fields': ('decline_reason', 'decline_notes'),
            'classes': ('collapse',)
        }),
        ('Notifications', {
            'fields': ('push_notification_sent', 'sms_sent', 'email_sent'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['resend_notifications', 'extend_expiry', 'withdraw_offers']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'pre_booked_ride__rider__user',
            'driver__user'
        ).prefetch_related('pre_booked_ride')
    
    def resend_notifications(self, request, queryset):
        pending_offers = queryset.filter(status='pending', expires_at__gt=timezone.now())
        notified_count = 0
        
        for offer in pending_offers:
            # This would trigger actual notification logic
            offer.push_notification_sent = True
            offer.save()
            notified_count += 1
        
        messages.success(request, f'Resent notifications for {notified_count} offers.')
    resend_notifications.short_description = "Resend notifications"
    
    def extend_expiry(self, request, queryset):
        pending_offers = queryset.filter(status='pending')
        extended_count = 0
        
        for offer in pending_offers:
            offer.expires_at = offer.expires_at + timezone.timedelta(minutes=30)
            offer.save()
            extended_count += 1
        
        messages.success(request, f'Extended expiry for {extended_count} offers.')
    extend_expiry.short_description = "Extend expiry by 30 minutes"
    
    def withdraw_offers(self, request, queryset):
        pending_offers = queryset.filter(status='pending')
        withdrawn_count = pending_offers.update(status='withdrawn', updated_at=timezone.now())
        messages.success(request, f'Withdrew {withdrawn_count} offers.')
    withdraw_offers.short_description = "Withdraw offers"


@admin.register(WaitingTimeOptimization)
class WaitingTimeOptimizationAdmin(admin.ModelAdmin):
    list_display = ['driver', 'date', 'total_gap_display', 'waiting_time_minutes', 'distance_between_km', 'efficiency_score', 'is_optimal', 'needs_reoptimization']
    list_filter = ['date', 'is_optimal', 'needs_reoptimization', 'efficiency_score']
    search_fields = ['driver__user__username', 'driver__user__email', 'optimization_notes']
    readonly_fields = ['created_at', 'updated_at', 'total_gap_minutes', 'is_efficient']
    date_hierarchy = 'date'
    ordering = ['date', 'first_ride_end_time']
    
    def total_gap_display(self, obj):
        hours = obj.total_gap_minutes // 60
        minutes = obj.total_gap_minutes % 60
        return f'{hours}h {minutes}m'
    total_gap_display.short_description = 'Total Gap'
    
    fieldsets = (
        ('Driver & Date', {
            'fields': ('driver', 'date')
        }),
        ('Ride Sequence', {
            'fields': ('first_ride', 'second_ride', 'first_ride_end_time', 'second_ride_start_time')
        }),
        ('Time Analysis', {
            'fields': ('buffer_time_minutes', 'travel_time_minutes', 'waiting_time_minutes', 'total_gap_minutes', 'is_efficient')
        }),
        ('Distance & Route', {
            'fields': ('distance_between_km', 'route_polyline'),
            'classes': ('collapse',)
        }),
        ('Optimization', {
            'fields': ('efficiency_score', 'fuel_cost_estimate', 'is_optimal', 'needs_reoptimization')
        }),
        ('Suggestions', {
            'fields': ('suggested_departure_time', 'suggested_route', 'optimization_notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['recalculate_efficiency', 'mark_as_optimal', 'generate_suggestions']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'driver__user',
            'first_ride__rider__user',
            'second_ride__rider__user'
        )
    
    def recalculate_efficiency(self, request, queryset):
        recalculated_count = 0
        
        for optimization in queryset:
            optimization.calculate_efficiency_score()
            optimization.save()
            recalculated_count += 1
        
        messages.success(request, f'Recalculated efficiency for {recalculated_count} optimizations.')
    recalculate_efficiency.short_description = "Recalculate efficiency scores"
    
    def mark_as_optimal(self, request, queryset):
        updated = queryset.update(is_optimal=True, needs_reoptimization=False)
        messages.success(request, f'{updated} optimizations marked as optimal.')
    mark_as_optimal.short_description = "Mark as optimal"
    
    def generate_suggestions(self, request, queryset):
        suggestion_count = 0
        
        for optimization in queryset:
            optimization.suggest_optimization()
            optimization.save()
            suggestion_count += 1
        
        messages.success(request, f'Generated suggestions for {suggestion_count} optimizations.')
    generate_suggestions.short_description = "Generate optimization suggestions"


@admin.register(RecurringRideTemplate)
class RecurringRideTemplateAdmin(admin.ModelAdmin):
    list_display = ['template_name', 'rider', 'recurrence_pattern', 'pickup_time', 'start_date', 'end_date', 'is_active', 'total_rides_generated', 'total_rides_completed']
    list_filter = ['recurrence_pattern', 'is_active', 'priority', 'start_date', 'created_at']
    search_fields = ['rider__user__username', 'rider__user__email', 'template_name', 'pickup_location', 'dropoff_location']
    readonly_fields = ['created_at', 'updated_at', 'total_rides_generated', 'total_rides_completed', 'last_generated_date']
    date_hierarchy = 'start_date'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('rider', 'template_name', 'is_active', 'priority')
        }),
        ('Route Details', {
            'fields': ('pickup_location', 'dropoff_location', 'pickup_latitude', 'pickup_longitude', 'dropoff_latitude', 'dropoff_longitude')
        }),
        ('Timing', {
            'fields': ('pickup_time', 'estimated_duration_minutes', 'pickup_window_minutes')
        }),
        ('Recurrence Pattern', {
            'fields': ('recurrence_pattern', 'custom_days', 'start_date', 'end_date')
        }),
        ('Preferences', {
            'fields': ('preferred_driver', 'special_requirements'),
            'classes': ('collapse',)
        }),
        ('Generation Settings', {
            'fields': ('generation_horizon_days', 'last_generated_date', 'excluded_dates'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_rides_generated', 'total_rides_completed'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['generate_upcoming_rides', 'activate_templates', 'deactivate_templates']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('rider__user', 'preferred_driver__user')
    
    def generate_upcoming_rides(self, request, queryset):
        active_templates = queryset.filter(is_active=True)
        generated_count = 0
        
        for template in active_templates:
            # This would need actual ride generation logic
            messages.info(request, f'Would generate rides for template: {template.template_name}')
            generated_count += 1
        
        messages.success(request, f'Processed {generated_count} templates for ride generation.')
    generate_upcoming_rides.short_description = "Generate upcoming rides"
    
    def activate_templates(self, request, queryset):
        updated = queryset.update(is_active=True)
        messages.success(request, f'{updated} templates activated.')
    activate_templates.short_description = "Activate templates"
    
    def deactivate_templates(self, request, queryset):
        updated = queryset.update(is_active=False)
        messages.success(request, f'{updated} templates deactivated.')
    deactivate_templates.short_description = "Deactivate templates"
