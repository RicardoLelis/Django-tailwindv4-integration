"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

from app.views import (
    landing_page, 
    rider_registration, 
    login_view, 
    logout_view, 
    home,
    book_ride,
    # Driver views
    driver_landing,
    driver_initial_registration,
    driver_verify_email,
    driver_complete_registration,
    driver_register_basic,
    driver_register_professional,
    driver_upload_documents,
    driver_background_consent,
    driver_register_vehicle,
    driver_vehicle_accessibility,
    driver_vehicle_safety,
    driver_vehicle_documents,
    driver_vehicle_photos,
    driver_training,
    driver_training_module,
    driver_dashboard,
    driver_documents,
    ajax_upload_document,
    ajax_upload_vehicle_photo
)
from app.views_auth import (
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_page, name='landing_page'),
    path('register/', rider_registration, name='rider_registration'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('home/', home, name='home'),
    path('book-ride/', book_ride, name='book_ride'),
    
    # Password reset URLs
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Driver registration URLs
    path('driver/', driver_landing, name='driver_landing'),
    path('driver/register/', driver_initial_registration, name='driver_initial_registration'),
    path('driver/verify/<str:token>/', driver_verify_email, name='driver_verify_email'),
    path('driver/complete/<str:token>/', driver_complete_registration, name='driver_complete_registration'),
    path('driver/join/', driver_register_basic, name='driver_register_basic'),
    path('driver/professional/', driver_register_professional, name='driver_register_professional'),
    path('driver/documents/', driver_upload_documents, name='driver_upload_documents'),
    path('driver/background-consent/', driver_background_consent, name='driver_background_consent'),
    path('driver/vehicle/', driver_register_vehicle, name='driver_register_vehicle'),
    path('driver/vehicle/accessibility/', driver_vehicle_accessibility, name='driver_vehicle_accessibility'),
    path('driver/vehicle/safety/', driver_vehicle_safety, name='driver_vehicle_safety'),
    path('driver/vehicle/documents/', driver_vehicle_documents, name='driver_vehicle_documents'),
    path('driver/vehicle/photos/', driver_vehicle_photos, name='driver_vehicle_photos'),
    path('driver/training/', driver_training, name='driver_training'),
    path('driver/training/<int:module_id>/', driver_training_module, name='driver_training_module'),
    path('driver/dashboard/', driver_dashboard, name='driver_dashboard'),
    path('driver/my-documents/', driver_documents, name='driver_documents'),
    
    # AJAX endpoints
    path('ajax/upload-document/', ajax_upload_document, name='ajax_upload_document'),
    path('ajax/upload-vehicle-photo/', ajax_upload_vehicle_photo, name='ajax_upload_vehicle_photo'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
