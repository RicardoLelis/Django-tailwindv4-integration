from .models import Driver

def user_role(request):
    """Add user role information to template context"""
    context = {
        'is_driver': False,
        'is_rider': False,
        'user_role': 'anonymous'
    }
    
    if request.user.is_authenticated:
        try:
            driver = request.user.driver
            context.update({
                'is_driver': True,
                'user_role': 'driver',
                'driver': driver
            })
        except Driver.DoesNotExist:
            # Check if user has rider profile or could be a rider
            context.update({
                'is_rider': True,
                'user_role': 'rider'
            })
    
    return context