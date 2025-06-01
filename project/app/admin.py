from django.contrib import admin
from .models import Rider, Ride

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
