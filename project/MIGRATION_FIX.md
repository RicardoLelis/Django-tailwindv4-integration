# Migration Error Fix Guide

The migration error you're encountering is due to missing dependencies and environment configuration. Here's how to fix it:

## Quick Fix (Immediate Solution)

### Step 1: Install Missing Dependencies
```bash
# Install python-decouple which is required for settings
pip install python-decouple

# Also install these if not already installed
pip install django-ratelimit>=4.1.0 redis>=4.6.0 django-redis>=5.3.0
```

### Step 2: Create Proper .env File
```bash
# Create .env file with required variables
cat > .env << 'EOF'
SECRET_KEY=django-insecure-dev-key-$(openssl rand -hex 32)
DEBUG=True
DJANGO_ENVIRONMENT=development
ALLOWED_HOSTS=localhost,127.0.0.1
REDIS_URL=redis://localhost:6379/0
NOMINATIM_API_URL=https://nominatim.openstreetmap.org
NOMINATIM_USER_AGENT=WheelchairRideShare-Dev/1.0
GEOCODING_RATE_LIMIT=1000/m
ROUTING_RATE_LIMIT=1000/m
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EOF
```

### Step 3: Test Settings Import
```bash
# Test if settings can be imported
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
import django
django.setup()
print('✅ Settings imported successfully')
"
```

### Step 4: Run Migrations
```bash
# Now try migrations again
python manage.py migrate
```

## Alternative Fix (Fallback Settings)

If you still have issues, temporarily use the original settings file:

### Option A: Use Original Settings Temporarily
```bash
# Backup the new settings file
mv project/settings.py project/settings_new.py

# Create a simple working settings file
cat > project/settings.py << 'EOF'
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-temp-key-for-development-only'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'landing_page'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Basic cache (fallback if Redis not available)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/hour',
        'user': '1000/hour',
        'geocoding': '1000/minute',
        'routing': '1000/minute',
    },
}

# Service area bounds (for fallback mode)
SERVICE_AREA_BOUNDS = {
    'north': 38.8500,
    'south': 38.6000,
    'east': -9.0000,
    'west': -9.5000,
}

# Cache TTLs
CACHE_TTL = {
    'geocoding': 86400,
    'routing': 3600,
}

# Rate limiting settings
GEOCODING_RATE_LIMIT = '1000/m'
ROUTING_RATE_LIMIT = '1000/m'

# API settings (fallback values)
NOMINATIM_API_URL = 'https://nominatim.openstreetmap.org'
NOMINATIM_USER_AGENT = 'WheelchairRideShare-Dev/1.0'

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EOF
```

### Option B: Fix Import Path
If you want to keep the new settings structure, update the settings.py file:

```bash
# Edit the main settings.py file
cat > project/settings.py << 'EOF'
"""
Django settings for wheelchair ride-sharing project.
Imports from environment-specific settings modules.
"""

import os
from decouple import config

# Determine which settings to use based on environment
ENVIRONMENT = config('DJANGO_ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    try:
        from .settings.production import *
    except ImportError:
        from .settings.base import *
elif ENVIRONMENT == 'staging':
    try:
        from .settings.staging import *
    except ImportError:
        from .settings.base import *
else:
    try:
        from .settings.development import *
    except ImportError:
        from .settings.base import *
EOF
```

## Step-by-Step Troubleshooting

### 1. Check Python Environment
```bash
# Verify you're in the right directory
pwd
# Should show: /Users/lelisra/Documents/code/tailwind4-django-how/project

# Check if virtual environment is activated
which python
# Should show path with 'venv' if virtual environment is active

# Check Django installation
python -c "import django; print(django.get_version())"
```

### 2. Install All Dependencies
```bash
# Install from requirements.txt
pip install -r requirements.txt

# Install additional dependencies manually if needed
pip install python-decouple django-ratelimit redis django-redis requests
```

### 3. Verify File Structure
```bash
# Check if all files exist
ls -la project/settings/
# Should show: __init__.py, base.py, development.py

# Check if .env file exists
ls -la .env
```

### 4. Test Environment Loading
```bash
# Test .env file loading
python -c "
from decouple import config
print('SECRET_KEY loaded:', bool(config('SECRET_KEY', default=None)))
print('DEBUG:', config('DEBUG', default=False))
"
```

### 5. Test Settings Import
```bash
# Test settings import step by step
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# Test base settings
try:
    from project.settings.base import *
    print('✅ Base settings imported')
except Exception as e:
    print('❌ Base settings error:', e)

# Test development settings
try:
    from project.settings.development import *
    print('✅ Development settings imported')
except Exception as e:
    print('❌ Development settings error:', e)
"
```

## Complete Working Commands

After applying the fix, run these commands in order:

```bash
# 1. Install dependencies
pip install python-decouple django-ratelimit redis django-redis requests

# 2. Create .env file (if not exists)
echo "SECRET_KEY=django-insecure-dev-$(openssl rand -hex 16)" > .env
echo "DEBUG=True" >> .env
echo "DJANGO_ENVIRONMENT=development" >> .env

# 3. Test settings
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings'); import django; django.setup(); print('Settings OK')"

# 4. Run migrations
python manage.py migrate

# 5. Start server
python manage.py runserver
```

## If All Else Fails

Use this minimal working settings.py:

```bash
# Backup existing files
mv project/settings.py project/settings_backup.py
mv project/settings project/settings_backup

# Use the existing original settings with our additions
# (The settings.py that was working before)
# Just add the necessary configurations for Phase 1 services
```

Let me know which approach works for you, and I can help you proceed to the next steps!