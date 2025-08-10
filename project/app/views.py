from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from datetime import datetime, timedelta
import json
import logging
import os
import secrets

logger = logging.getLogger(__name__)
from .forms import (
    RiderRegistrationForm, EmailAuthenticationForm, DriverBasicInfoForm,
    DriverEligibilityForm, DriverProfessionalInfoForm, DriverDocumentUploadForm,
    BackgroundCheckConsentForm, VehicleBasicInfoForm, VehicleAccessibilityForm,
    VehicleSafetyEquipmentForm, VehicleDocumentUploadForm, VehiclePhotoUploadForm,
    DriverInitialRegistrationForm, DriverCompleteProfileForm
)
from .models import (
    Rider, Ride, Driver, Vehicle, DriverDocument, VehicleDocument, 
    VehiclePhoto, TrainingModule, DriverTraining, RecurringRideTemplate
)

def get_user_home_url(user):
    """Helper function to determine the correct home page for a user"""
    try:
        driver = user.driver
        return 'driver_dashboard'
    except Driver.DoesNotExist:
        return 'home'

def landing_page(request):
    if request.user.is_authenticated:
        return redirect(get_user_home_url(request.user))
    return render(request, "landing.html")

def rider_registration(request):
    if request.user.is_authenticated:
        return redirect(get_user_home_url(request.user))
        
    if request.method == 'POST':
        form = RiderRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('login')
    else:
        form = RiderRegistrationForm()
    
    return render(request, 'rider_registration.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        # Check if user is a driver and redirect accordingly
        try:
            driver = request.user.driver
            return redirect('driver_dashboard')
        except Driver.DoesNotExist:
            return redirect('home')
        
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')  # The form field is named 'username' but contains email
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                
                # Check if user is a driver and redirect accordingly
                try:
                    driver = user.driver
                    return redirect('driver_dashboard')
                except Driver.DoesNotExist:
                    # User is a rider or needs to create rider profile
                    return redirect('home')
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Invalid email or password.")
    else:
        form = EmailAuthenticationForm()
    
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('landing_page')

@login_required
def home(request):
    # Check if user is actually a driver - if so, redirect them
    try:
        driver = request.user.driver
        return redirect('driver_dashboard')
    except Driver.DoesNotExist:
        pass
    
    # User is a rider
    try:
        rider = request.user.rider
    except Rider.DoesNotExist:
        # If user doesn't have a rider profile, create one
        rider = Rider.objects.create(user=request.user)
    
    # Get upcoming rides with fare estimates
    upcoming_rides_queryset = rider.rides.filter(
        pickup_datetime__gte=timezone.now(),
        status__in=['pending', 'confirmed']
    ).order_by('pickup_datetime')[:5]
    
    # Calculate fare estimates for upcoming rides
    upcoming_rides = []
    for ride in upcoming_rides_queryset:
        ride_data = {
            'ride': ride,
            'distance_km': 0.0,
            'estimated_fare': None,
        }
        
        try:
            from .services.geocoding_service import GeocodingService
            from .services.pricing_service import PricingService
            
            geocoding_service = GeocodingService()
            pricing_service = PricingService()
            
            # Calculate distance and fare
            pickup_coords = geocoding_service.geocode(ride.pickup_location)
            dropoff_coords = geocoding_service.geocode(ride.dropoff_location)
            
            if pickup_coords and dropoff_coords:
                distance_km = geocoding_service._calculate_distance(
                    pickup_coords['lat'], pickup_coords['lng'],
                    dropoff_coords['lat'], dropoff_coords['lng']
                )
                
                # Check if wheelchair is required
                wheelchair_required = any('wheelchair' in disability.lower() 
                                        for disability in rider.disabilities) if rider.disabilities else False
                
                # Calculate fare
                estimated_fare = pricing_service.calculate_immediate_fare(
                    distance_km=distance_km,
                    wheelchair_required=wheelchair_required
                )
                
                ride_data['distance_km'] = round(distance_km, 1)
                ride_data['estimated_fare'] = estimated_fare
                
        except Exception as e:
            logger.warning(f"Error calculating fare for ride {ride.id}: {e}")
        
        upcoming_rides.append(ride_data)
    
    # Get ride history
    past_rides = rider.rides.filter(
        pickup_datetime__lt=timezone.now()
    ).order_by('-pickup_datetime')[:5]
    
    # Generate date options for the next 7 days
    date_options = []
    today = datetime.now().date()
    for i in range(7):
        date = today + timedelta(days=i)
        date_options.append({
            'value': date.strftime('%Y-%m-%d'),
            'display': date.strftime('%A, %B %d')
        })
    
    context = {
        'rider': rider,
        'upcoming_rides': upcoming_rides,
        'past_rides': past_rides,
        'date_options': date_options,
    }
    
    return render(request, 'home.html', context)

@login_required
def book_ride(request):
    if request.method == 'POST':
        try:
            rider = request.user.rider
            
            # Get form data
            pickup_location = request.POST.get('pickup_location')
            dropoff_location = request.POST.get('dropoff_location')
            pickup_date = request.POST.get('pickup_date')
            pickup_time = request.POST.get('pickup_time')
            special_requirements = request.POST.get('special_requirements', '')
            
            # Combine date and time
            pickup_datetime = datetime.strptime(f"{pickup_date} {pickup_time}", '%Y-%m-%d %H:%M')
            pickup_datetime = timezone.make_aware(pickup_datetime)
            
            # Calculate estimated fare and distance
            estimated_fare = None
            distance_km = 0.0
            
            try:
                from .services.geocoding_service import GeocodingService
                from .services.pricing_service import PricingService
                
                geocoding_service = GeocodingService()
                pricing_service = PricingService()
                
                # Geocode locations
                pickup_coords = geocoding_service.geocode(pickup_location)
                dropoff_coords = geocoding_service.geocode(dropoff_location)
                
                if pickup_coords and dropoff_coords:
                    # Calculate distance
                    distance_km = geocoding_service._calculate_distance(
                        pickup_coords['lat'], pickup_coords['lng'],
                        dropoff_coords['lat'], dropoff_coords['lng']
                    )
                    
                    # Check if wheelchair is required
                    wheelchair_required = any('wheelchair' in disability.lower() 
                                            for disability in rider.disabilities) if rider.disabilities else False
                    
                    # Calculate fare
                    estimated_fare = pricing_service.calculate_immediate_fare(
                        distance_km=distance_km,
                        wheelchair_required=wheelchair_required
                    )
                    
            except Exception as e:
                logger.warning(f"Error calculating fare for new ride: {e}")
            
            # Create the ride
            ride = Ride.objects.create(
                rider=rider,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                pickup_datetime=pickup_datetime,
                special_requirements=special_requirements
            )
            
            # Broadcast the new ride to available drivers
            try:
                from .services.notification_service import NotificationService
                notification_service = NotificationService()
                notification_service.broadcast_immediate_ride_to_drivers(ride)
                logger.info(f"Broadcasted immediate ride {ride.id} to available drivers")
            except Exception as e:
                logger.error(f"Error broadcasting ride {ride.id} to drivers: {e}")
            
            # Add fare info to success message if calculated
            success_message = 'Your ride has been booked successfully!'
            if estimated_fare and distance_km:
                success_message += f' Estimated fare: €{estimated_fare} for {distance_km:.1f}km.'
            
            messages.success(request, success_message)
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'Error booking ride: {str(e)}')
            return redirect('home')
    
    return redirect('home')


# Driver Registration Views

def driver_landing(request):
    """Driver registration landing page"""
    if request.user.is_authenticated:
        try:
            driver = request.user.driver
            return redirect('driver_dashboard')
        except Driver.DoesNotExist:
            pass
    
    return render(request, 'driver/landing.html')


def driver_initial_registration(request):
    """Simplified initial registration - just email, phone, and fleet size"""
    if request.method == 'POST':
        form = DriverInitialRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Check if user already exists but is inactive (pending verification)
            existing_user = User.objects.filter(email=email, is_active=False).first()
            if existing_user:
                # Resend verification email
                try:
                    driver = existing_user.driver
                    # Update phone and fleet size in case they changed
                    driver.phone_number = form.cleaned_data['phone_number']
                    driver.fleet_size = form.cleaned_data['fleet_size']
                    driver.email_verification_sent = timezone.now()
                    driver.save()
                    
                    # Resend verification email
                    verification_url = request.build_absolute_uri(
                        reverse('driver_verify_email', args=[driver.email_verification_token])
                    )
                    
                    send_mail(
                        'Verify your email - RideConnect Driver',
                        f'''
                        Welcome back to RideConnect!
                        
                        Please click the link below to verify your email address:
                        {verification_url}
                        
                        This link will expire in 24 hours.
                        
                        Best regards,
                        The RideConnect Team
                        ''',
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    
                    messages.info(request, 'A new verification email has been sent. Please check your inbox.')
                    return redirect('driver_landing')
                except Driver.DoesNotExist:
                    # User exists but no driver profile - delete and recreate
                    existing_user.delete()
            
            # Generate a unique username from email
            username = email.split('@')[0] + '_' + secrets.token_hex(4)
            
            # Create user without password (they'll set it after email verification)
            user = User.objects.create(
                username=username,
                email=email,
                is_active=False  # Inactive until email verified
            )
            
            # Generate verification token
            verification_token = secrets.token_urlsafe(32)
            
            # Create driver profile
            driver = Driver.objects.create(
                user=user,
                phone_number=form.cleaned_data['phone_number'],
                fleet_size=form.cleaned_data['fleet_size'],
                email_verification_token=verification_token,
                email_verification_sent=timezone.now(),
                application_status='started'
            )
            
            # Send verification email
            verification_url = request.build_absolute_uri(
                reverse('driver_verify_email', args=[verification_token])
            )
            
            send_mail(
                'Verify your email - RideConnect Driver',
                f'''
                Welcome to RideConnect!
                
                Please click the link below to verify your email address:
                {verification_url}
                
                This link will expire in 24 hours.
                
                Best regards,
                The RideConnect Team
                ''',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            messages.success(request, 'Thank you for registering! Please check your email to verify your account.')
            return redirect('driver_landing')
    else:
        form = DriverInitialRegistrationForm()
    
    return render(request, 'driver/initial_registration.html', {'form': form})


def driver_verify_email(request, token):
    """Verify email and activate account"""
    try:
        driver = Driver.objects.get(email_verification_token=token)
        
        # Check if token is expired (24 hours)
        if driver.email_verification_sent < timezone.now() - timedelta(hours=24):
            messages.error(request, 'This verification link has expired. Please register again.')
            return redirect('driver_initial_registration')
        
        # Activate user
        driver.user.is_active = True
        driver.user.save()
        
        # Update driver status
        driver.email_verified = True
        driver.application_status = 'email_verified'
        
        # Generate registration completion token
        registration_token = secrets.token_urlsafe(32)
        driver.registration_token = registration_token
        driver.registration_token_created = timezone.now()
        driver.save()
        
        # Send registration completion email
        registration_url = request.build_absolute_uri(
            reverse('driver_complete_registration', args=[registration_token])
        )
        
        send_mail(
            'Complete your registration - RideConnect Driver',
            f'''
            Your email has been verified successfully!
            
            Click the link below to complete your driver registration:
            {registration_url}
            
            You'll need to provide:
            - Vehicle information and photos
            - Driver's license
            - Operating licenses
            - Insurance documentation
            
            This link will expire in 7 days.
            
            Best regards,
            The RideConnect Team
            ''',
            settings.DEFAULT_FROM_EMAIL,
            [driver.user.email],
            fail_silently=False,
        )
        
        messages.success(request, 'Email verified! Check your inbox for the link to complete your registration.')
        return redirect('driver_landing')
        
    except Driver.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('driver_landing')


def driver_complete_registration(request, token):
    """Complete registration after email verification"""
    try:
        driver = Driver.objects.get(registration_token=token)
        
        # Check if token is expired (7 days)
        if driver.registration_token_created < timezone.now() - timedelta(days=7):
            messages.error(request, 'This registration link has expired.')
            return redirect('driver_landing')
        
        # Log the user in with explicit backend
        backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, driver.user, backend=backend)
        
        # Redirect to the full registration flow
        return redirect('driver_register_basic')
        
    except Driver.DoesNotExist:
        messages.error(request, 'Invalid registration link.')
        return redirect('driver_landing')


@ensure_csrf_cookie
def driver_register_basic(request):
    """Phase 1: Basic account creation - now used after email verification"""
    if not request.user.is_authenticated:
        messages.error(request, 'Please access this page through the link in your email.')
        return redirect('driver_landing')
    
    try:
        driver = request.user.driver
        # Allow access if coming from email verification or if already started
        if driver.application_status not in ['email_verified', 'started']:
            return redirect('driver_dashboard')
    except Driver.DoesNotExist:
        messages.error(request, 'Driver profile not found.')
        return redirect('driver_landing')
    
    # Ensure CSRF token is available
    get_token(request)
    
    if request.method == 'POST':
        basic_form = DriverCompleteProfileForm(request.POST, instance=request.user)
        eligibility_form = DriverEligibilityForm(request.POST)
        
        if basic_form.is_valid() and eligibility_form.is_valid():
            # Check eligibility requirements
            if not all([
                eligibility_form.cleaned_data['has_portuguese_license'],
                eligibility_form.cleaned_data['has_accessible_vehicle'],
                eligibility_form.cleaned_data['authorized_to_work']
            ]):
                messages.error(request, 'You must meet all eligibility requirements to continue.')
                return render(request, 'driver/register_basic.html', {
                    'basic_form': basic_form,
                    'eligibility_form': eligibility_form
                })
            
            # Update user info (including password)
            user = basic_form.save()
            
            # Update driver profile
            driver.has_portuguese_license = True
            driver.has_accessible_vehicle = True
            driver.authorized_to_work = True
            driver.application_status = 'started'
            driver.save()
            
            # Re-authenticate user with new password
            backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user, backend=backend)
            
            messages.success(request, 'Account created! Now please upload your documents.')
            return redirect('driver_upload_documents')
    else:
        basic_form = DriverCompleteProfileForm(instance=request.user)
        eligibility_form = DriverEligibilityForm()
    
    return render(request, 'driver/register_basic.html', {
        'basic_form': basic_form,
        'eligibility_form': eligibility_form
    })


@login_required
def driver_register_professional(request):
    """Phase 2: Professional information"""
    try:
        driver = request.user.driver
        if driver.application_status not in ['started', 'documents_uploaded']:
            return redirect('driver_dashboard')
    except Driver.DoesNotExist:
        return redirect('driver_register_basic')
    
    if request.method == 'POST':
        form = DriverProfessionalInfoForm(request.POST, instance=driver)
        if form.is_valid():
            form.save()
            messages.success(request, 'Professional information saved! Next, please upload your documents.')
            return redirect('driver_upload_documents')
    else:
        form = DriverProfessionalInfoForm(instance=driver)
    
    return render(request, 'driver/register_professional.html', {'form': form})


@login_required 
def driver_upload_documents(request):
    """Phase 2: Document upload"""
    try:
        driver = request.user.driver
        if driver.application_status not in ['started', 'documents_uploaded']:
            return redirect('driver_dashboard')
    except Driver.DoesNotExist:
        return redirect('driver_register_basic')
    
    # Get existing documents
    existing_docs = {doc.document_type: doc for doc in driver.documents.all()}
    required_docs = ['driving_license_front', 'driving_license_back', 'citizen_card', 'proof_of_address']
    
    if request.method == 'POST':
        # Check if this is a bulk upload
        if request.POST.get('bulk_upload') == 'true':
            uploaded_count = 0
            
            # Process each document type
            for doc_type in required_docs:
                file_key = f"{doc_type}_file"
                if file_key in request.FILES:
                    # Delete existing document of same type
                    if doc_type in existing_docs:
                        existing_docs[doc_type].delete()
                    
                    # Create new document
                    DriverDocument.objects.create(
                        driver=driver,
                        document_type=doc_type,
                        file=request.FILES[file_key]
                    )
                    uploaded_count += 1
            
            # Check if all required documents are now uploaded
            current_docs = set(driver.documents.values_list('document_type', flat=True))
            if all(doc in current_docs for doc in required_docs):
                driver.application_status = 'documents_uploaded'
                driver.save()
                messages.success(request, 'All documents uploaded successfully! Please provide background check consent.')
                return redirect('driver_background_consent')
            else:
                if uploaded_count > 0:
                    messages.success(request, f'{uploaded_count} document(s) uploaded successfully!')
                else:
                    messages.warning(request, 'No documents were selected for upload.')
                return redirect('driver_upload_documents')
        else:
            # Legacy single document upload (kept for backward compatibility)
            doc_type = request.POST.get('document_type')
            if doc_type and 'file' in request.FILES:
                # Delete existing document of same type
                if doc_type in existing_docs:
                    existing_docs[doc_type].delete()
                
                # Create new document
                DriverDocument.objects.create(
                    driver=driver,
                    document_type=doc_type,
                    file=request.FILES['file']
                )
                
                # Check if all required documents are uploaded
                current_docs = set(driver.documents.values_list('document_type', flat=True))
                if all(doc in current_docs for doc in required_docs):
                    driver.application_status = 'documents_uploaded'
                    driver.save()
                    messages.success(request, 'All documents uploaded! Please provide background check consent.')
                    return redirect('driver_background_consent')
                else:
                    messages.success(request, f'Document uploaded successfully!')
                    return redirect('driver_upload_documents')
    
    # Prepare document status
    doc_status = {}
    for doc_type, display_name in DriverDocument.DOCUMENT_TYPES:
        doc_status[doc_type] = {
            'name': display_name,
            'uploaded': doc_type in existing_docs,
            'required': doc_type in required_docs
        }
    
    return render(request, 'driver/upload_documents.html', {
        'doc_status': doc_status,
        'progress': len(existing_docs) / len(required_docs) * 100
    })


@login_required
def driver_background_consent(request):
    """Phase 2: Background check consent"""
    try:
        driver = request.user.driver
        if driver.application_status != 'documents_uploaded':
            return redirect('driver_dashboard')
    except Driver.DoesNotExist:
        return redirect('driver_register_basic')
    
    if request.method == 'POST':
        form = BackgroundCheckConsentForm(request.POST)
        if form.is_valid():
            driver.background_check_consent = True
            driver.application_status = 'background_check_pending'
            driver.save()
            messages.success(request, 'Consent recorded! Now let\'s register your vehicle.')
            return redirect('driver_register_vehicle')
    else:
        form = BackgroundCheckConsentForm()
    
    return render(request, 'driver/background_consent.html', {'form': form})


@login_required
def driver_register_vehicle(request):
    """Phase 3: Vehicle registration"""
    try:
        driver = request.user.driver
        # Only allow vehicle registration if background check is approved
        if driver.application_status == 'background_check_pending' and driver.background_check_status != 'approved':
            messages.warning(request, 'Please wait for your background check to be approved before registering a vehicle.')
            return redirect('driver_dashboard')
        if driver.application_status not in ['background_check_pending', 'training_in_progress']:
            return redirect('driver_dashboard')
    except Driver.DoesNotExist:
        return redirect('driver_register_basic')
    
    # Check if driver already has a vehicle
    if driver.vehicles.exists():
        return redirect('driver_vehicle_accessibility')
    
    if request.method == 'POST':
        form = VehicleBasicInfoForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.driver = driver
            vehicle.save()
            messages.success(request, 'Vehicle information saved! Please specify accessibility features.')
            return redirect('driver_vehicle_accessibility')
    else:
        form = VehicleBasicInfoForm()
    
    return render(request, 'driver/register_vehicle.html', {'form': form})


@login_required
def driver_vehicle_accessibility(request):
    """Phase 3: Vehicle accessibility features"""
    try:
        driver = request.user.driver
        vehicle = driver.vehicles.first()
        if not vehicle:
            return redirect('driver_register_vehicle')
    except (Driver.DoesNotExist, Vehicle.DoesNotExist):
        return redirect('driver_register_basic')
    
    if request.method == 'POST':
        form = VehicleAccessibilityForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            # Update driver status to training phase
            driver.application_status = 'training_in_progress'
            driver.save()
            
            messages.success(request, 'Vehicle registration complete! Now you can proceed with training modules.')
            return redirect('driver_training')
    else:
        form = VehicleAccessibilityForm(instance=vehicle)
    
    return render(request, 'driver/vehicle_accessibility.html', {'form': form, 'vehicle': vehicle})


@login_required
def driver_vehicle_safety(request):
    """Phase 3: Vehicle safety equipment checklist"""
    try:
        driver = request.user.driver
        vehicle = driver.vehicles.first()
        if not vehicle:
            return redirect('driver_register_vehicle')
    except (Driver.DoesNotExist, Vehicle.DoesNotExist):
        return redirect('driver_register_basic')
    
    if request.method == 'POST':
        form = VehicleSafetyEquipmentForm(request.POST)
        if form.is_valid():
            vehicle.safety_equipment = form.cleaned_data['safety_equipment']
            vehicle.save()
            messages.success(request, 'Safety equipment confirmed! Please upload vehicle documents.')
            return redirect('driver_vehicle_documents')
    else:
        form = VehicleSafetyEquipmentForm(initial={'safety_equipment': vehicle.safety_equipment})
    
    return render(request, 'driver/vehicle_safety.html', {'form': form, 'vehicle': vehicle})


@login_required
def driver_vehicle_documents(request):
    """Phase 3: Vehicle document upload"""
    try:
        driver = request.user.driver
        vehicle = driver.vehicles.first()
        if not vehicle:
            return redirect('driver_register_vehicle')
    except (Driver.DoesNotExist, Vehicle.DoesNotExist):
        return redirect('driver_register_basic')
    
    # Get existing documents
    existing_docs = {doc.document_type: doc for doc in vehicle.documents.all()}
    required_docs = ['registration', 'insurance', 'inspection']
    
    if request.method == 'POST':
        doc_type = request.POST.get('document_type')
        if doc_type and 'file' in request.FILES:
            # Delete existing document of same type
            if doc_type in existing_docs:
                existing_docs[doc_type].delete()
            
            # Create new document
            VehicleDocument.objects.create(
                vehicle=vehicle,
                document_type=doc_type,
                file=request.FILES['file'],
                expiry_date=request.POST.get('expiry_date') or None
            )
            
            # Check if all required documents are uploaded
            current_docs = set(vehicle.documents.values_list('document_type', flat=True))
            if all(doc in current_docs for doc in required_docs):
                messages.success(request, 'All documents uploaded! Please upload vehicle photos.')
                return redirect('driver_vehicle_photos')
            else:
                messages.success(request, 'Document uploaded successfully!')
    
    # Prepare document status
    doc_status = {}
    for doc_type, display_name in VehicleDocument.DOCUMENT_TYPES:
        doc_status[doc_type] = {
            'name': display_name,
            'uploaded': doc_type in existing_docs,
            'required': doc_type in required_docs
        }
    
    return render(request, 'driver/vehicle_documents.html', {
        'doc_status': doc_status,
        'vehicle': vehicle,
        'progress': len(existing_docs) / len(required_docs) * 100
    })


@login_required
def driver_vehicle_photos(request):
    """Phase 3: Vehicle photo upload"""
    try:
        driver = request.user.driver
        vehicle = driver.vehicles.first()
        if not vehicle:
            return redirect('driver_register_vehicle')
    except (Driver.DoesNotExist, Vehicle.DoesNotExist):
        return redirect('driver_register_basic')
    
    # Get existing photos
    existing_photos = {photo.photo_type: photo for photo in vehicle.photos.all()}
    required_photos = ['exterior_front', 'exterior_back', 'accessibility_ramp', 'wheelchair_area']
    
    if request.method == 'POST':
        photo_type = request.POST.get('photo_type')
        if photo_type and 'image' in request.FILES:
            # Delete existing photo of same type
            if photo_type in existing_photos:
                existing_photos[photo_type].delete()
            
            # Create new photo
            VehiclePhoto.objects.create(
                vehicle=vehicle,
                photo_type=photo_type,
                image=request.FILES['image'],
                description=request.POST.get('description', '')
            )
            
            # Check if all required photos are uploaded
            current_photos = set(vehicle.photos.values_list('photo_type', flat=True))
            if all(photo in current_photos for photo in required_photos):
                driver.application_status = 'training_in_progress'
                driver.save()
                messages.success(request, 'All photos uploaded! Ready for training modules.')
                return redirect('driver_training')
            else:
                messages.success(request, 'Photo uploaded successfully!')
    
    # Prepare photo status
    photo_status = {}
    for photo_type, display_name in VehiclePhoto.PHOTO_TYPES:
        photo_status[photo_type] = {
            'name': display_name,
            'uploaded': photo_type in existing_photos,
            'required': photo_type in required_photos
        }
    
    return render(request, 'driver/vehicle_photos.html', {
        'photo_status': photo_status,
        'vehicle': vehicle,
        'progress': len(existing_photos) / len(required_photos) * 100
    })


@login_required
def driver_training(request):
    """Phase 4: Training modules"""
    try:
        driver = request.user.driver
        if driver.application_status != 'training_in_progress':
            return redirect('driver_dashboard')
    except Driver.DoesNotExist:
        return redirect('driver_register_basic')
    
    # Get all training modules with progress
    modules = TrainingModule.objects.all().order_by('order')
    
    # Annotate modules with progress information
    for module in modules:
        try:
            training = DriverTraining.objects.get(driver=driver, module=module)
            module.training_progress = training
        except DriverTraining.DoesNotExist:
            module.training_progress = None
    
    # Check if all mandatory modules are completed
    mandatory_modules = [module for module in modules if module.is_mandatory]
    completed_mandatory = sum(1 for module in mandatory_modules 
                            if module.training_progress and module.training_progress.is_completed)
    
    if completed_mandatory == len(mandatory_modules):
        driver.training_completed = True
        driver.application_status = 'assessment_scheduled'
        driver.save()
    
    # Calculate remaining modules
    remaining_mandatory = len(mandatory_modules) - completed_mandatory
    
    return render(request, 'driver/training.html', {
        'modules': modules,
        'completed_mandatory': completed_mandatory,
        'total_mandatory': len(mandatory_modules),
        'remaining_mandatory': remaining_mandatory
    })


@login_required
def driver_training_module(request, module_id):
    """Individual training module"""
    try:
        driver = request.user.driver
        module = get_object_or_404(TrainingModule, id=module_id)
    except Driver.DoesNotExist:
        return redirect('driver_register_basic')
    
    # Get or create training progress
    training, created = DriverTraining.objects.get_or_create(
        driver=driver,
        module=module,
        defaults={'attempts': 0}
    )
    
    if request.method == 'POST':
        # Handle quiz submission
        score = int(request.POST.get('score', 0))
        training.quiz_score = score
        training.attempts += 1
        
        if score >= 80:  # Passing score
            training.completed_at = timezone.now()
            messages.success(request, f'Congratulations! You passed {module.title}.')
        else:
            messages.warning(request, f'Score: {score}/100. You need 80% to pass. Please try again.')
        
        training.save()
        return redirect('driver_training')
    
    return render(request, 'driver/training_module.html', {
        'module': module,
        'training': training
    })


@login_required
def driver_dashboard(request):
    """Driver dashboard"""
    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        return redirect('driver_register_basic')
    
    # Calculate progress
    progress_steps = {
        'started': 10,
        'documents_uploaded': 40, 
        'background_check_pending': 60,
        'training_in_progress': 80,
        'assessment_scheduled': 90,
        'approved': 100
    }
    
    progress = progress_steps.get(driver.application_status, 0)
    
    # Get next step
    next_steps = {
        'started': 'Upload required documents',
        'documents_uploaded': 'Provide background check consent',
        'background_check_pending': 'Waiting for background check approval' if driver.background_check_status != 'approved' else 'Register your vehicle',
        'training_in_progress': 'Complete training modules',
        'assessment_scheduled': 'Schedule practical assessment',
        'approved': 'Start accepting rides!'
    }
    
    next_step = next_steps.get(driver.application_status, 'Application under review')
    
    # Initialize analytics variables
    recent_rides = []
    today_stats = None
    week_stats = None
    month_stats = None
    current_session = None
    
    # If driver is approved, get ride history and analytics
    if driver.application_status == 'approved':
        # Get recent rides
        recent_rides = driver.driver_rides.select_related('ride', 'vehicle').order_by('-created_at')[:10]
        
        # Get today's stats
        today = timezone.now().date()
        today_rides = driver.driver_rides.filter(
            created_at__date=today,
            ride__status='completed'
        )
        
        today_stats = {
            'rides': today_rides.count(),
            'earnings': sum(ride.driver_earnings for ride in today_rides),
            'distance': sum(ride.distance_km or 0 for ride in today_rides),
            'online_hours': 0  # Will be calculated from sessions
        }
        
        # Get this week's performance
        try:
            week_start = today - timedelta(days=today.weekday())
            week_stats = driver.performance_metrics.filter(
                period_type='weekly',
                period_start=week_start
            ).first()
        except:
            week_stats = None
        
        # Get this month's performance
        try:
            month_start = today.replace(day=1)
            month_stats = driver.performance_metrics.filter(
                period_type='monthly',
                period_start=month_start
            ).first()
        except:
            month_stats = None
        
        # Get current session if online
        if driver.is_available:
            current_session = driver.sessions.filter(ended_at__isnull=True).first()
    
    context = {
        'driver': driver,
        'progress': progress,
        'next_step': next_step,
        'vehicle': driver.vehicles.first() if driver.vehicles.exists() else None,
        'recent_rides': recent_rides,
        'today_stats': today_stats,
        'week_stats': week_stats,
        'month_stats': month_stats,
        'current_session': current_session
    }
    
    return render(request, 'driver/dashboard.html', context)

@login_required
def edit_recurring_ride(request, template_id=None):
    """View to edit recurring ride templates"""
    try:
        driver = request.user.driver
        if driver.application_status != 'approved':
            messages.error(request, 'You must be an approved driver to manage recurring rides.')
            return redirect('driver_dashboard')
    except Driver.DoesNotExist:
        messages.error(request, 'Driver profile not found.')
        return redirect('home')
    
    if template_id:
        # Edit existing template
        template = get_object_or_404(RecurringRideTemplate, id=template_id, driver=driver)
        
        if request.method == 'POST':
            # Update template logic would go here
            messages.success(request, 'Recurring ride template updated successfully!')
            return redirect('driver_dashboard')
        
        context = {
            'template': template,
            'driver': driver,
            'editing': True
        }
    else:
        # Create new template
        if request.method == 'POST':
            # Create template logic would go here
            messages.success(request, 'Recurring ride template created successfully!')
            return redirect('driver_dashboard')
        
        context = {
            'driver': driver,
            'editing': False
        }
    
    return render(request, 'driver/edit_recurring_ride.html', context)


# AJAX endpoints for file uploads
@login_required
@require_http_methods(["POST"])
def ajax_upload_document(request):
    """AJAX endpoint for document upload"""
    try:
        driver = request.user.driver
        doc_type = request.POST.get('document_type')
        
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No file provided'})
        
        # Delete existing document of same type
        DriverDocument.objects.filter(driver=driver, document_type=doc_type).delete()
        
        # Create new document
        doc = DriverDocument.objects.create(
            driver=driver,
            document_type=doc_type,
            file=request.FILES['file']
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Document uploaded successfully',
            'doc_id': doc.id
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])  
def ajax_upload_vehicle_photo(request):
    """AJAX endpoint for vehicle photo upload"""
    try:
        driver = request.user.driver
        vehicle = driver.vehicles.first()
        
        if not vehicle:
            return JsonResponse({'success': False, 'error': 'No vehicle found'})
        
        photo_type = request.POST.get('photo_type')
        
        if 'image' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No image provided'})
        
        # Delete existing photo of same type
        VehiclePhoto.objects.filter(vehicle=vehicle, photo_type=photo_type).delete()
        
        # Create new photo
        photo = VehiclePhoto.objects.create(
            vehicle=vehicle,
            photo_type=photo_type,
            image=request.FILES['image'],
            description=request.POST.get('description', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Photo uploaded successfully',
            'photo_id': photo.id
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
def ajax_geocode(request):
    """AJAX endpoint for geocoding addresses and calculating route info"""
    try:
        import math
        import random
        
        # Get request parameters
        address = request.POST.get('address', '').strip()
        pickup_location = request.POST.get('pickup_location', '').strip()
        dropoff_location = request.POST.get('dropoff_location', '').strip()
        
        # Mock Lisbon locations for demo
        lisbon_locations = {
            'airport': {'lat': 38.7813, 'lng': -9.1359, 'name': 'Lisbon Airport'},
            'downtown': {'lat': 38.7167, 'lng': -9.1395, 'name': 'Downtown Lisbon'},
            'belem': {'lat': 38.6969, 'lng': -9.2156, 'name': 'Belém'},
            'parque_nacoes': {'lat': 38.7679, 'lng': -9.0973, 'name': 'Parque das Nações'},
            'cascais': {'lat': 38.6979, 'lng': -9.4215, 'name': 'Cascais'},
            'sintra': {'lat': 38.8029, 'lng': -9.3817, 'name': 'Sintra'},
            'almada': {'lat': 38.6767, 'lng': -9.1565, 'name': 'Almada'},
            'oeiras': {'lat': 38.6908, 'lng': -9.3094, 'name': 'Oeiras'}
        }
        
        def get_location_coords(address_text):
            """Get coordinates for an address, using predefined locations or generating mock ones"""
            # Check if address matches any predefined location
            address_lower = address_text.lower()
            for key, location in lisbon_locations.items():
                if key in address_lower or location['name'].lower() in address_lower:
                    return location
            
            # Generate mock coordinates within Lisbon area
            # Base coordinates for Lisbon center
            base_lat = 38.7223
            base_lng = -9.1393
            
            # Add some variation based on address hash
            hash_val = hash(address_text) % 1000
            lat_offset = (hash_val % 100 - 50) * 0.001  # ±0.05 degrees
            lng_offset = ((hash_val // 100) % 100 - 50) * 0.001  # ±0.05 degrees
            
            return {
                'lat': base_lat + lat_offset,
                'lng': base_lng + lng_offset,
                'name': address_text
            }
        
        def calculate_distance(coord1, coord2):
            """Calculate distance between two coordinates using Haversine formula"""
            R = 6371  # Earth's radius in kilometers
            
            lat1, lon1 = math.radians(coord1['lat']), math.radians(coord1['lng'])
            lat2, lon2 = math.radians(coord2['lat']), math.radians(coord2['lng'])
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            return R * c
        
        def estimate_duration(distance_km):
            """Estimate duration based on distance and typical Lisbon traffic"""
            # Average speed in Lisbon: 25-35 km/h depending on traffic
            avg_speed = random.uniform(25, 35)
            base_duration = (distance_km / avg_speed) * 60  # Convert to minutes
            
            # Add some randomness for traffic conditions
            traffic_factor = random.uniform(0.9, 1.3)
            duration = base_duration * traffic_factor
            
            # Add minimum duration (at least 5 minutes)
            return max(5, round(duration))
        
        def calculate_fare(distance_km, duration_min):
            """Calculate estimated fare based on distance and duration"""
            # Base fare: €3.25
            base_fare = 3.25
            
            # Per kilometer: €0.47
            distance_fare = distance_km * 0.47
            
            # Per minute: €0.20 (for waiting time/slow traffic)
            time_fare = duration_min * 0.20
            
            # Total fare
            total_fare = base_fare + distance_fare + time_fare
            
            # Round to nearest 0.50
            return round(total_fare * 2) / 2
        
        # Case 1: Single address geocoding
        if address and not (pickup_location and dropoff_location):
            location = get_location_coords(address)
            
            return JsonResponse({
                'success': True,
                'results': [{
                    'formatted_address': location['name'],
                    'geometry': {
                        'location': {
                            'lat': location['lat'],
                            'lng': location['lng']
                        }
                    },
                    'place_id': f'mock_place_{hash(address) % 10000}',
                    'types': ['street_address']
                }]
            })
        
        # Case 2: Route calculation (both pickup and dropoff provided)
        elif pickup_location and dropoff_location:
            pickup_coords = get_location_coords(pickup_location)
            dropoff_coords = get_location_coords(dropoff_location)
            
            # Calculate distance and duration
            distance = calculate_distance(pickup_coords, dropoff_coords)
            duration = estimate_duration(distance)
            fare = calculate_fare(distance, duration)
            
            # Generate route polyline (simplified - just a straight line for mock)
            route_polyline = f"{pickup_coords['lat']},{pickup_coords['lng']}|{dropoff_coords['lat']},{dropoff_coords['lng']}"
            
            return JsonResponse({
                'success': True,
                'route': {
                    'pickup': {
                        'address': pickup_coords['name'],
                        'lat': pickup_coords['lat'],
                        'lng': pickup_coords['lng']
                    },
                    'dropoff': {
                        'address': dropoff_coords['name'],
                        'lat': dropoff_coords['lat'],
                        'lng': dropoff_coords['lng']
                    },
                    'distance': {
                        'value': round(distance * 1000),  # meters
                        'text': f'{distance:.1f} km'
                    },
                    'duration': {
                        'value': duration * 60,  # seconds
                        'text': f'{duration} min'
                    },
                    'fare': {
                        'value': fare,
                        'text': f'€{fare:.2f}',
                        'currency': 'EUR'
                    },
                    'polyline': route_polyline,
                    'bounds': {
                        'northeast': {
                            'lat': max(pickup_coords['lat'], dropoff_coords['lat']),
                            'lng': max(pickup_coords['lng'], dropoff_coords['lng'])
                        },
                        'southwest': {
                            'lat': min(pickup_coords['lat'], dropoff_coords['lat']),
                            'lng': min(pickup_coords['lng'], dropoff_coords['lng'])
                        }
                    }
                }
            })
        
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid request. Provide either address or both pickup_location and dropoff_location.'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def driver_documents(request):
    """View and manage driver documents"""
    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        return redirect('driver_register_basic')
    
    # Get all document types and existing documents
    document_types = dict(DriverDocument.DOCUMENT_TYPES)
    existing_docs = {doc.document_type: doc for doc in driver.documents.all()}
    
    # Prepare document list with status
    documents = []
    for doc_type, display_name in DriverDocument.DOCUMENT_TYPES:
        doc_info = {
            'type': doc_type,
            'name': display_name,
            'required': doc_type in ['driving_license_front', 'driving_license_back', 'citizen_card', 'proof_of_address'],
            'exists': doc_type in existing_docs,
            'document': existing_docs.get(doc_type),
            'can_update': driver.application_status in ['approved', 'documents_uploaded', 'background_check_pending', 'training_in_progress', 'assessment_scheduled']
        }
        documents.append(doc_info)
    
    if request.method == 'POST':
        doc_type = request.POST.get('document_type')
        
        if doc_type and 'file' in request.FILES:
            # Check if driver can update documents
            can_update = driver.application_status in ['approved', 'documents_uploaded', 'background_check_pending', 'training_in_progress', 'assessment_scheduled']
            if not can_update:
                messages.error(request, 'You cannot update documents at this stage.')
                return redirect('driver_documents')
            
            # Delete existing document of same type
            if doc_type in existing_docs:
                existing_docs[doc_type].delete()
            
            # Create new document
            DriverDocument.objects.create(
                driver=driver,
                document_type=doc_type,
                file=request.FILES['file']
            )
            
            messages.success(request, f'{document_types[doc_type]} updated successfully!')
            return redirect('driver_documents')
    
    context = {
        'driver': driver,
        'documents': documents
    }
    
    return render(request, 'driver/documents.html', context)