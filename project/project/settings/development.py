"""
Development settings for wheelchair ride-sharing project.
"""

from .base import *
import logging
from decouple import config

# Security
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Development API endpoints (with relaxed rate limiting)
NOMINATIM_API_URL = config('NOMINATIM_API_URL', default='https://nominatim.openstreetmap.org')

# Relaxed rate limits for development
GEOCODING_RATE_LIMIT = '1000/m'
ROUTING_RATE_LIMIT = '1000/m'

# Override REST Framework throttle rates for development
if 'DEFAULT_THROTTLE_RATES' in REST_FRAMEWORK:
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].update({
        'geocoding': '1000/minute',
        'routing': '1000/minute',
    })

# Cache configuration - fallback to in-memory if Redis not available
try:
    # Test Redis connection
    import redis
    r = redis.from_url(REDIS_URL)
    r.ping()
    logging.info("Redis connection successful")
except Exception as e:
    logging.warning(f"Redis connection failed: {e}, using fallback cache")
    # Fallback to local memory cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'wheelchair-rides-dev',
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Less strict security for development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Try to add development apps if available
try:
    import django_extensions
    INSTALLED_APPS += ['django_extensions']
except ImportError:
    pass

# Development logging - more verbose
if 'LOGGING' in locals() and LOGGING:
    try:
        LOGGING['handlers']['console']['level'] = 'DEBUG'
        LOGGING['loggers']['app.services']['level'] = 'DEBUG'
    except KeyError:
        pass

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'