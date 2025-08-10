"""
URL configuration for RideConnect app including pre-booked rides.
"""

from django.urls import path, include
from django.shortcuts import render
from rest_framework.routers import DefaultRouter
from . import views
from .views_package import *  # Import all views including pre-booking views
from .api import views as api_views

# API router for REST endpoints
router = DefaultRouter()
router.register(r'bookings', api_views.PreBookedRideViewSet, basename='booking')
router.register(r'calendar', api_views.DriverCalendarViewSet, basename='calendar')
router.register(r'offers', api_views.RideMatchOfferViewSet, basename='offer')

urlpatterns = [
    # Landing pages
    path('', views.landing_page, name='landing_page'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Rider routes
    path('rider/register/', views.rider_registration, name='rider_registration'),
    path('home/', views.home, name='home'),
    path('book-ride/', views.book_ride, name='book_ride'),
    
    # Pre-booked rides (Rider)
    path('pre-book/', pre_book_ride, name='pre_book_ride'),
    path('pre-book/search-drivers/', search_drivers, name='search_drivers'),
    path('pre-book/confirm/<int:booking_id>/', confirm_booking, name='confirm_booking'),
    path('pre-book/<int:booking_id>/', booking_details, name='booking_details'),
    path('pre-book/<int:booking_id>/cancel/', cancel_booking, name='cancel_booking'),
    path('my-bookings/', my_bookings, name='my_bookings'),
    
    # Recurring rides
    path('recurring/', recurring_rides, name='recurring_rides'),
    path('recurring/create/', create_recurring_ride, name='create_recurring_ride'),
    path('recurring/<int:template_id>/edit/', views.edit_recurring_ride, name='edit_recurring_ride'),
    path('recurring/<int:template_id>/pause/', pause_recurring_ride, name='pause_recurring_ride'),
    
    # Driver registration flow
    path('driver/', views.driver_landing, name='driver_landing'),
    path('driver/register/', views.driver_initial_registration, name='driver_initial_registration'),
    path('driver/verify/<str:token>/', views.driver_verify_email, name='driver_verify_email'),
    path('driver/complete/<str:token>/', views.driver_complete_registration, name='driver_complete_registration'),
    path('driver/register-basic/', views.driver_register_basic, name='driver_register_basic'),
    path('driver/register-professional/', views.driver_register_professional, name='driver_register_professional'),
    path('driver/upload-documents/', views.driver_upload_documents, name='driver_upload_documents'),
    path('driver/background-consent/', views.driver_background_consent, name='driver_background_consent'),
    path('driver/register-vehicle/', views.driver_register_vehicle, name='driver_register_vehicle'),
    path('driver/vehicle-accessibility/', views.driver_vehicle_accessibility, name='driver_vehicle_accessibility'),
    path('driver/vehicle-safety/', views.driver_vehicle_safety, name='driver_vehicle_safety'),
    path('driver/vehicle-documents/', views.driver_vehicle_documents, name='driver_vehicle_documents'),
    path('driver/vehicle-photos/', views.driver_vehicle_photos, name='driver_vehicle_photos'),
    path('driver/training/', views.driver_training, name='driver_training'),
    path('driver/training/<int:module_id>/', views.driver_training_module, name='driver_training_module'),
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('driver/documents/', views.driver_documents, name='driver_documents'),
    
    # Driver calendar management
    path('driver/calendar/', driver_calendar, name='driver_calendar'),
    path('driver/calendar/update/', update_calendar, name='update_calendar'),
    path('driver/calendar/week/', calendar_week_view, name='calendar_week_view'),
    
    # Driver pre-booked rides management
    path('driver/offers/', driver_offers, name='driver_offers'),
    path('driver/offers/<int:offer_id>/accept/', accept_offer, name='accept_offer'),
    path('driver/offers/<int:offer_id>/decline/', decline_offer, name='decline_offer'),
    path('driver/bookings/', driver_bookings, name='driver_bookings'),
    path('driver/bookings/<int:booking_id>/', driver_booking_detail, name='driver_booking_detail'),
    
    # Waiting time optimization
    path('driver/waiting/<int:optimization_id>/', waiting_opportunities, name='waiting_opportunities'),
    
    # Driver status management
    path('driver/toggle-status/', toggle_driver_status, name='toggle_driver_status'),
    path('driver/update-location/', update_driver_location, name='update_driver_location'),
    path('driver/live-offers/', driver_live_offers, name='driver_live_offers'),
    path('driver/accept-immediate-ride/<int:ride_id>/', accept_immediate_ride, name='accept_immediate_ride'),
    
    # AJAX endpoints
    path('ajax/upload-document/', views.ajax_upload_document, name='ajax_upload_document'),
    path('ajax/upload-vehicle-photo/', views.ajax_upload_vehicle_photo, name='ajax_upload_vehicle_photo'),
    path('ajax/geocode/', views.ajax_geocode, name='ajax_geocode'),
    path('ajax/calculate-fare/', ajax_calculate_fare, name='ajax_calculate_fare'),
    path('ajax/check-availability/', ajax_check_availability, name='ajax_check_availability'),
    
    # API endpoints
    path('api/', include('app.api.urls')),
    
]