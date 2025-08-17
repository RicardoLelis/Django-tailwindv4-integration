"""
Settings package for wheelchair ride-sharing project.
"""

import os
from decouple import config

# Determine which settings to use based on environment
ENVIRONMENT = config('DJANGO_ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'staging':
    from .staging import *
else:
    from .development import *