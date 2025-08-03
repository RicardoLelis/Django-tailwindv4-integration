# Local Development Setup Guide

This guide walks you through setting up and running the wheelchair ride-sharing application locally for development and testing.

## Prerequisites

- Python 3.8+ installed
- Node.js 16+ installed (for map tile generation)
- Git installed
- Basic familiarity with Django and command line

## Quick Start (TL;DR)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create basic .env file
echo "SECRET_KEY=django-insecure-dev-key-$(openssl rand -hex 32)" > .env
echo "DEBUG=True" >> .env
echo "REDIS_URL=redis://localhost:6379/0" >> .env

# 3. Install and start Redis (macOS)
brew install redis && brew services start redis

# 4. Run migrations
python manage.py migrate

# 5. Start development server
python manage.py runserver

# 6. Visit http://localhost:8000/map-demo/
```

For detailed setup, continue reading below.

## Step 1: Clone and Setup Project

### 1.1 Navigate to Project Directory
```bash
# You should already be in the project directory
cd /Users/lelisra/Documents/code/tailwind4-django-how/project
pwd
# Should show: /Users/lelisra/Documents/code/tailwind4-django-how/project
```

### 1.2 Check Project Structure
```bash
# Verify key files exist
ls -la
# Should see: manage.py, requirements.txt, project/, app/, etc.

# Check Python version
python --version
# Should be Python 3.8+
```

## Step 2: Install Python Dependencies

### 2.1 Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate

# Windows:
# venv\Scripts\activate

# Verify activation (should show (venv) in prompt)
which python
```

### 2.2 Install Dependencies
```bash
# Install all required packages
pip install -r requirements.txt

# Verify key packages are installed
pip list | grep -E "(Django|redis|requests)"
# Should show Django, redis, requests, etc.
```

### 2.3 Install Additional Dependencies (if needed)
```bash
# If requirements.txt is missing Phase 1 dependencies
pip install requests>=2.31.0 django-ratelimit>=4.1.0 redis>=4.6.0 django-redis>=5.3.0
```

## Step 3: Environment Configuration

### 3.1 Create .env File
```bash
# Create environment file
cat > .env << 'EOF'
# Django Configuration
SECRET_KEY=django-insecure-dev-key-change-this-in-production
DEBUG=True
DJANGO_ENVIRONMENT=development
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite for development)
# DATABASE_URL=sqlite:///db.sqlite3

# Redis Configuration (install Redis first - see Step 4)
REDIS_URL=redis://localhost:6379/0

# External API Configuration (for testing without external APIs)
NOMINATIM_API_URL=https://nominatim.openstreetmap.org
NOMINATIM_USER_AGENT=WheelchairRideShare-Dev/1.0

# OpenRouteService (optional for basic testing)
# Get free API key from https://openrouteservice.org/
# OPENROUTESERVICE_API_KEY=your-api-key-here

# Cloudflare R2 (optional for basic testing)
# R2_ACCOUNT_ID=your-account-id
# R2_ACCESS_KEY_ID=your-access-key
# R2_SECRET_ACCESS_KEY=your-secret-key
# R2_BUCKET_NAME=ridewheel-maps
# R2_PUBLIC_URL=https://your-bucket.r2.dev

# Rate Limiting (lenient for development)
GEOCODING_RATE_LIMIT=1000/m
ROUTING_RATE_LIMIT=1000/m

# Email Configuration (console output for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=dev@wheelchairrideshare.local
EOF
```

### 3.2 Secure the Secret Key
```bash
# Generate a secure secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Update .env file with the generated key
# Replace the SECRET_KEY line in .env with the generated key
```

## Step 4: Install and Configure Redis

### 4.1 Install Redis (Choose your platform)

#### macOS (Homebrew)
```bash
# Install Redis
brew install redis

# Start Redis service
brew services start redis

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

#### Ubuntu/Debian
```bash
# Install Redis
sudo apt update
sudo apt install redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping
```

#### Windows (WSL recommended)
```bash
# Use Windows Subsystem for Linux
wsl --install -d Ubuntu
# Then follow Ubuntu instructions above
```

### 4.2 Test Redis Connection
```bash
# Test Redis with Python
python -c "
import redis
try:
    r = redis.from_url('redis://localhost:6379/0')
    r.ping()
    print('✅ Redis connection successful')
except:
    print('❌ Redis connection failed')
"
```

## Step 5: Database Setup

### 5.1 Run Database Migrations
```bash
# Apply all migrations
python manage.py migrate

# You should see output like:
# Operations to perform:
#   Apply all migrations: admin, auth, contenttypes, sessions, app
# Running migrations:
#   Applying contenttypes.0001_initial... OK
#   ... (more migrations)
```

### 5.2 Create Superuser (Optional)
```bash
# Create admin user for Django admin
python manage.py createsuperuser

# Enter username, email, and password when prompted
# Username: admin
# Email: admin@example.com
# Password: (choose a secure password)
```

### 5.3 Load Sample Data (Optional)
```bash
# If you want to test with sample data
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
from app.models import Rider, Driver

# Create sample rider
if not User.objects.filter(username='rider1').exists():
    user = User.objects.create_user('rider1', 'rider1@example.com', 'password123')
    Rider.objects.create(
        user=user,
        phone_number='+351910000001',
        uses_wheelchair=True,
        wheelchair_type='manual'
    )
    print('✅ Sample rider created')
EOF
```

## Step 6: Test the Application

### 6.1 Start Development Server
```bash
# Start Django development server
python manage.py runserver

# You should see:
# System check identified no issues (0 silenced).
# Django version X.X.X, using settings 'project.settings'
# Starting development server at http://127.0.0.1:8000/
# Quit the server with CONTROL-C.
```

### 6.2 Test Basic Functionality
Open your browser and test these URLs:

```bash
# 1. Main landing page
http://localhost:8000/

# 2. Map demo (Phase 1 functionality)
http://localhost:8000/map-demo/

# 3. Django admin (if you created superuser)
http://localhost:8000/admin/

# 4. API health checks
http://localhost:8000/api/geocoding/health/
http://localhost:8000/api/routing/health/
```

### 6.3 Test Phase 1 Services
```bash
# Open a new terminal (keep server running)
# Test geocoding service
curl -X POST http://localhost:8000/api/geocoding/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{"address": "Lisboa, Portugal"}'

# Note: You'll need to be logged in or use session authentication
# For testing, you can use the Django admin session
```

## Step 7: Frontend Setup (Map Demo)

### 7.1 Test Map Demo Page
1. Visit `http://localhost:8000/map-demo/`
2. You should see:
   - Map component loading area
   - Address input fields with autocomplete
   - Route calculation buttons

### 7.2 Test Map Functionality (Without External APIs)
The map will work in fallback mode without external APIs:
1. Try typing "Hospital" in pickup field
2. Select from fallback suggestions
3. Repeat for dropoff field
4. Map should show fallback route calculation

### 7.3 Add External APIs for Full Functionality

#### Get OpenRouteService API Key (Optional)
1. Visit https://openrouteservice.org/
2. Sign up for free account
3. Create API key
4. Add to `.env`: `OPENROUTESERVICE_API_KEY=your-key`
5. Restart Django server

#### Test With Real APIs
```bash
# Restart server after adding API keys
python manage.py runserver

# Visit map demo again - should now use real routing
http://localhost:8000/map-demo/
```

## Step 8: Run Tests

### 8.1 Run Custom Test Suite
```bash
# Run the Phase 1 test suite
python run_tests.py

# You should see:
# Phase 1 Core Infrastructure - Service Tests
# ==========================================
# 1. Testing Geocoding Service...
#    ✓ Address validation - valid input
#    ✓ Coordinate validation - valid coordinates
#    ...
```

### 8.2 Run Django Tests
```bash
# Run Django's built-in tests
python manage.py test

# Run specific app tests
python manage.py test app

# Run with verbose output
python manage.py test --verbosity=2
```

### 8.3 Test Individual Components
```bash
# Test geocoding service
python manage.py shell << 'EOF'
from app.services.geocoding_service import GeocodingService
service = GeocodingService()
result = service.geocode("Lisboa, Portugal")
print(f"Geocoding test: {result}")
EOF

# Test routing service
python manage.py shell << 'EOF'
from app.services.routing_service import RoutingService
service = RoutingService()
coords = [[-9.1393, 38.7223], [-9.1607, 38.7492]]
route = service.get_wheelchair_route(coords)
print(f"Routing test: {route['summary'] if route else 'No route'}")
EOF
```

## Step 9: Development Workflow

### 9.1 Daily Development Commands
```bash
# Start development session
source venv/bin/activate  # If using virtual environment
redis-cli ping  # Verify Redis is running
python manage.py runserver  # Start Django server

# Common development tasks
python manage.py makemigrations  # After model changes
python manage.py migrate  # Apply new migrations
python manage.py collectstatic  # Update static files
python manage.py shell  # Django shell for testing
```

### 9.2 Debug Mode Features
With `DEBUG=True` in your `.env`, you get:
- Detailed error pages
- Django Debug Toolbar (if installed)
- Static file serving
- Verbose logging
- Development-friendly error handling

### 9.3 Monitoring During Development
```bash
# Monitor Redis activity
redis-cli monitor

# Check Django logs (if file logging is enabled)
tail -f logs/django.log

# Monitor network requests (browser dev tools)
# Press F12 in browser, go to Network tab
```

## Troubleshooting

### Common Issues and Solutions

#### 1. "ModuleNotFoundError: No module named 'X'"
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt

# Check if specific package is installed
pip list | grep package-name
```

#### 2. Redis Connection Errors
```bash
# Check if Redis is running
redis-cli ping

# If not running:
# macOS: brew services start redis
# Ubuntu: sudo systemctl start redis-server

# Check Redis logs
tail -f /var/log/redis/redis-server.log
```

#### 3. Database Migration Errors
```bash
# Reset migrations (development only!)
rm app/migrations/0*.py
python manage.py makemigrations
python manage.py migrate

# Or delete database and start fresh
rm db.sqlite3
python manage.py migrate
```

#### 4. Static Files Not Loading
```bash
# Collect static files
python manage.py collectstatic --noinput

# Check STATIC_URL in settings
python manage.py shell -c "
from django.conf import settings
print('STATIC_URL:', settings.STATIC_URL)
print('STATICFILES_DIRS:', settings.STATICFILES_DIRS)
"
```

#### 5. Map Not Loading
1. Check browser console for JavaScript errors
2. Verify MapLibre GL JS and Protomaps libraries are loaded
3. Check if external CDN links are accessible
4. Test with fallback data (should work without external APIs)

#### 6. API Endpoints Return 403/401 Errors  
```bash
# For development testing, you can temporarily disable authentication
# In api views, comment out @permission_classes([IsAuthenticated])

# Or create a test user and login via Django admin
http://localhost:8000/admin/
```

### Getting Help

#### Check Application Health
```bash
# Check service health endpoints
curl http://localhost:8000/api/geocoding/health/
curl http://localhost:8000/api/routing/health/

# Check Django system status
python manage.py check
```

#### Debug with Django Shell
```bash
python manage.py shell
```

```python
# Test configuration
from django.conf import settings
print("DEBUG:", settings.DEBUG)
print("DATABASES:", settings.DATABASES)
print("CACHES:", settings.CACHES)

# Test Redis
from django.core.cache import cache
cache.set('test', 'OK')
print("Redis test:", cache.get('test'))

# Test services
from app.services.geocoding_service import GeocodingService
service = GeocodingService()
print("Service area bounds:", service.service_area)
```

## Development Tips

### 1. Use Debug Tools
```bash
# Install Django Debug Toolbar (optional)
pip install django-debug-toolbar

# Add to INSTALLED_APPS in development settings
```

### 2. API Testing with curl
```bash
# Test geocoding (you'll need authentication)
curl -X POST http://localhost:8000/api/geocoding/ \
  -H "Content-Type: application/json" \
  -d '{"address": "Rossio, Lisboa"}'

# Test with session authentication (login via browser first)
curl -X POST http://localhost:8000/api/geocoding/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your-csrf-token" \
  -b "sessionid=your-session-id" \
  -d '{"address": "Rossio, Lisboa"}'
```

### 3. Database Inspection
```bash
# Access database directly
python manage.py dbshell

# Or use Django shell
python manage.py shell
```

```python
# Check models
from app.models import Rider, Driver, PreBookedRide
print("Riders:", Rider.objects.count())
print("Drivers:", Driver.objects.count())
```

## Next Steps

After successful setup:

1. **Explore the application**: Visit all the demo pages
2. **Add external API keys**: For full functionality
3. **Set up map tiles**: Follow the Cloudflare R2 guide
4. **Create test data**: Add sample riders and drivers
5. **Start development**: Begin customizing for your needs

## Production Preparation

When ready for production:

1. **Change DEBUG to False** in production environment
2. **Use PostgreSQL** instead of SQLite
3. **Set up proper Redis** with password protection
4. **Configure web server** (Nginx/Apache)
5. **Set up SSL certificates**
6. **Configure monitoring** and logging

Your local development environment is now ready for the wheelchair ride-sharing application! 🎉