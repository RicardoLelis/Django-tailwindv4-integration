from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from .forms import RiderRegistrationForm

def landing_page(request):
    return render(request, "landing.html")

def rider_registration(request):
    if request.method == 'POST':
        form = RiderRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome aboard.')
            return redirect('landing_page')
    else:
        form = RiderRegistrationForm()
    
    return render(request, 'rider_registration.html', {'form': form})