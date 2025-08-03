"""
Django settings for wheelchair ride-sharing project.
Imports from environment-specific settings modules.
"""

import os
from decouple import config

# Determine which settings to use based on environment
ENVIRONMENT = config('DJANGO_ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    from .settings.production import *
elif ENVIRONMENT == 'staging':
    from .settings.staging import *
else:
    from .settings.development import *
