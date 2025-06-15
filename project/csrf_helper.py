"""
Helper function to handle CSRF failures gracefully
"""
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.contrib import messages

def handle_csrf_failure(request, template_name, context=None):
    """
    Handle CSRF token failures by refreshing the token and showing a helpful message
    """
    if context is None:
        context = {}
    
    # Get a fresh CSRF token
    get_token(request)
    
    # Add a message to inform the user
    messages.warning(request, 
        'Your session expired for security reasons. The page has been refreshed. Please try submitting the form again.')
    
    # Add CSRF error flag to context for JavaScript detection
    context['csrf_refreshed'] = True
    
    return render(request, template_name, context)