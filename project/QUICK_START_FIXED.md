# Quick Start Guide - CORRECTED VERSION

This guide provides the working steps to get your wheelchair ride-sharing application running locally.

## ✅ Working Quick Start Commands

Run these commands in order from the project directory:

```bash
# 1. Activate virtual environment
source /Users/lelisra/Documents/code/tailwind4-django-how/venv/bin/activate

# 2. Install missing dependencies
pip install django-ratelimit

# 3. Verify .env file exists and has required variables
# (The .env file should already be configured with the previous fixes)

# 4. Run migrations with the working settings
DJANGO_SETTINGS_MODULE=project.settings_simple python manage.py migrate

# 5. Start the development server
DJANGO_SETTINGS_MODULE=project.settings_simple python manage.py runserver
```

## ✅ What You Can Test Now

1. **Main Landing Page**: http://localhost:8000/
2. **Map Demo**: http://localhost:8000/map-demo/
3. **API Health Checks**:
   - http://localhost:8000/api/geocoding/health/
   - http://localhost:8000/api/routing/health/
4. **Django Admin**: http://localhost:8000/admin/ (if you create a superuser)

## ✅ Create a Superuser (Optional)

```bash
# Create admin user for testing
DJANGO_SETTINGS_MODULE=project.settings_simple python manage.py createsuperuser
# Username: admin
# Email: admin@example.com  
# Password: (choose a secure password)
```

## ✅ Test the Phase 1 Features

### Map Demo Testing
1. Visit http://localhost:8000/map-demo/
2. Try typing "Hospital" in the pickup field - should show autocomplete suggestions
3. Select a pickup and dropoff location
4. The map should display a route with accessibility information

### API Testing (Optional)
```bash
# Test geocoding health
curl http://localhost:8000/api/geocoding/health/

# Test routing health  
curl http://localhost:8000/api/routing/health/
```

## Why This Works

**Root Cause of Original Error**: The complex settings structure was trying to import and configure Redis/external services before Django was fully initialized, causing a cascade of import errors.

**Solution**: Using `project.settings_simple` which:
- ✅ Has all necessary configurations
- ✅ Uses fallback cache (no Redis required)
- ✅ Includes all Phase 1 service configurations
- ✅ Works without external API keys

## Next Steps

### To Use Full Phase 1 Features:
1. **Install Redis** (optional, app works with fallback cache):
   ```bash
   brew install redis && brew services start redis
   ```

2. **Get OpenRouteService API Key** (optional, app has fallback routing):
   - Visit https://openrouteservice.org/
   - Add to .env: `OPENROUTESERVICE_API_KEY=your-key`

3. **Set up Cloudflare R2** (optional, app works with basic map styling):
   - Follow CLOUDFLARE_R2_SETUP_GUIDE.md

### To Fix the Original Settings Structure:
The issue was in `project/settings/development.py` trying to access variables before they were properly loaded. The temporary fix is using `settings_simple.py`.

## Environment Variables

Your `.env` file should contain:
```bash
SECRET_KEY=django-insecure-qw0=8ln_@0ag*=4jsi_96&uxvjap-au@6r*odl(srf-op@1uzq
DEBUG=True
DJANGO_ENVIRONMENT=development
ALLOWED_HOSTS=localhost,127.0.0.1
REDIS_URL=redis://localhost:6379/0
NOMINATIM_API_URL=https://nominatim.openstreetmap.org
NOMINATIM_USER_AGENT=WheelchairRideShare-Dev/1.0
GEOCODING_RATE_LIMIT=1000/m
ROUTING_RATE_LIMIT=1000/m
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

## ✅ Verification Checklist

After running the commands above, you should be able to:

- [ ] Start Django server without errors
- [ ] Visit http://localhost:8000/ and see the landing page
- [ ] Visit http://localhost:8000/map-demo/ and see the map interface
- [ ] Type in address fields and see autocomplete suggestions
- [ ] Select pickup/dropoff locations and see route calculation
- [ ] View http://localhost:8000/admin/ (after creating superuser)

## Troubleshooting

If you encounter issues:

1. **"ModuleNotFoundError"**: Install missing packages:
   ```bash
   pip install django-ratelimit requests python-decouple
   ```

2. **Settings errors**: Always use the simple settings:
   ```bash
   DJANGO_SETTINGS_MODULE=project.settings_simple python manage.py [command]
   ```

3. **Permission errors**: Make sure you're in the correct directory:
   ```bash
   cd /Users/lelisra/Documents/code/tailwind4-django-how/project
   ```

4. **Virtual environment**: Always activate it first:
   ```bash
   source /Users/lelisra/Documents/code/tailwind4-django-how/venv/bin/activate
   ```

Your wheelchair ride-sharing application is now running and ready for testing! 🎉