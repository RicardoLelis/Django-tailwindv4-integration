from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
from .forms import RiderRegistrationForm, EmailAuthenticationForm
from .models import Rider, Ride

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, "landing.html")

def rider_registration(request):
    if request.user.is_authenticated:
        return redirect('home')
        
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
    try:
        rider = request.user.rider
    except Rider.DoesNotExist:
        # If user doesn't have a rider profile, create one
        rider = Rider.objects.create(user=request.user)
    
    # Get upcoming rides
    upcoming_rides = rider.rides.filter(
        pickup_datetime__gte=timezone.now(),
        status__in=['pending', 'confirmed']
    ).order_by('pickup_datetime')[:5]
    
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
            
            # Create the ride
            ride = Ride.objects.create(
                rider=rider,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                pickup_datetime=pickup_datetime,
                special_requirements=special_requirements
            )
            
            messages.success(request, 'Your ride has been booked successfully!')
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'Error booking ride: {str(e)}')
            return redirect('home')
    
    return redirect('home')