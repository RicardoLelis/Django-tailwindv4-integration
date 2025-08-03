# Phase 1 Core Infrastructure - Manual Intervention TODO

This document lists all manual interventions required to complete the Phase 1 Core Infrastructure implementation for the wheelchair ride-sharing application.

## Environment Configuration

### 1. Create Environment File (.env)

Create a `.env` file in the project root with the following variables:

```bash
# Django Configuration
SECRET_KEY=your-secure-secret-key-here
DEBUG=True
DJANGO_ENVIRONMENT=development
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (if using PostgreSQL in production)
# DATABASE_URL=postgresql://username:password@localhost:5432/wheelchair_rides

# External API Keys
NOMINATIM_API_URL=https://nominatim.openstreetmap.org
NOMINATIM_USER_AGENT=WheelchairRideShare/1.0

# TODO: REQUIRED - Register at https://openrouteservice.org/ and get API key
OPENROUTESERVICE_API_KEY=your-openrouteservice-api-key

# TODO: REQUIRED - Set up Cloudflare R2 bucket for map tiles
R2_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=your-r2-access-key
R2_SECRET_ACCESS_KEY=your-r2-secret-key
R2_BUCKET_NAME=ridewheel-maps
R2_PUBLIC_URL=https://your-bucket.r2.cloudflarestorage.com

# TODO: REQUIRED - Set up Redis server
REDIS_URL=redis://localhost:6379/0

# Rate Limiting Configuration
GEOCODING_RATE_LIMIT=60/m
ROUTING_RATE_LIMIT=100/m

# Email Configuration (for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### 2. Production Environment File (.env.production)

For production deployment, create `.env.production` with:

```bash
# Django Configuration
SECRET_KEY=your-production-secret-key
DEBUG=False
DJANGO_ENVIRONMENT=production
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://username:password@host:5432/wheelchair_rides_prod

# External APIs (same as development but with production keys if different)
OPENROUTESERVICE_API_KEY=your-production-api-key
R2_PUBLIC_URL=https://your-production-bucket.r2.cloudflarestorage.com

# Email Configuration (Amazon SES for production)
EMAIL_BACKEND=django_ses.SESBackend
AWS_ACCESS_KEY_ID=your-ses-access-key
AWS_SECRET_ACCESS_KEY=your-ses-secret-key
AWS_SES_REGION_NAME=eu-west-1
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Rate Limiting (more restrictive for production)
GEOCODING_RATE_LIMIT=60/m
ROUTING_RATE_LIMIT=100/m
```

## External Service Setup

### 3. OpenRouteService API Key

**Priority: HIGH - Required for routing functionality**

1. Visit https://openrouteservice.org/
2. Create a free account
3. Generate an API key
4. Add to your `.env` file: `OPENROUTESERVICE_API_KEY=your-key`
5. Free tier limits: 2,000 requests/day

### 4. Cloudflare R2 Setup for Map Tiles

**Priority: HIGH - Required for map display**

1. Create Cloudflare account at https://cloudflare.com/
2. Go to R2 Object Storage
3. Create a new bucket named `ridewheel-maps`
4. Generate R2 API tokens with read/write permissions
5. Update `.env` file with R2 credentials
6. Download and prepare map tiles for Lisbon:
   - Option 1: Use Protomaps CLI to generate PMTiles
   - Option 2: Use OpenStreetMap extract for Portugal
   - Upload tiles to R2 bucket

### 5. Redis Server Setup

**Priority: HIGH - Required for caching and sessions**

#### Development (Local)
```bash
# macOS with Homebrew
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# Verify installation
redis-cli ping
# Should return "PONG"
```

#### Production Options
- **Redis Cloud**: https://redis.com/cloud/
- **AWS ElastiCache**: For AWS deployments
- **Digital Ocean Managed Redis**: For DO deployments
- **Self-hosted**: On your server with proper security

### 6. Map Tiles Preparation

**Priority: HIGH - Required for map functionality**

#### Option 1: Protomaps Setup
```bash
# Install Protomaps CLI
npm install -g protomaps

# Download Portugal OSM extract
wget https://download.geofabrik.de/europe/portugal-latest.osm.pbf

# Generate PMTiles
protomaps extract portugal-latest.osm.pbf \
  --bbox="-9.5,38.6,-9.0,38.85" \
  --output=lisbon.pmtiles

# Upload to Cloudflare R2
aws s3 cp lisbon.pmtiles s3://ridewheel-maps/lisbon.pmtiles \
  --endpoint-url=https://your-account-id.r2.cloudflarestorage.com
```

#### Option 2: Alternative Map Providers
- Consider Mapbox (paid) or MapTiler (freemium) as alternatives
- Update map-component.js accordingly

## Database Setup

### 7. Install Dependencies

**Priority: HIGH - Required for application to run**

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install additional Phase 1 dependencies
pip install requests>=2.31.0 django-ratelimit>=4.1.0 redis>=4.6.0 django-redis>=5.3.0
```

### 8. Database Migrations

**Priority: HIGH - Required for database schema**

```bash
# Apply existing migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

## Frontend Dependencies

### 9. Include External JavaScript Libraries

**Priority: HIGH - Required for map functionality**

Add these to your base template or the specific pages that use maps:

```html
<!-- MapLibre GL JS -->
<script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />

<!-- Protomaps -->
<script src="https://unpkg.com/protomaps@2.0.0/dist/protomaps.js"></script>
```

### 10. Update Static Files Configuration

**Priority: MEDIUM - For production deployment**

```python
# In production settings
STATIC_ROOT = '/path/to/static/files/'

# Collect static files
python manage.py collectstatic
```

## Security Configuration

### 11. CSRF and Security Headers

**Priority: HIGH - Required for production**

Update your production settings:

```python
# In production settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### 12. API Rate Limiting

**Priority: MEDIUM - Already configured, monitor usage**

Current settings:
- Geocoding: 60 requests/minute per user
- Routing: 100 requests/minute per user
- Address suggestions: 120 requests/minute per user

Monitor usage and adjust in production.

## Testing and Validation

### 13. Test the Implementation

**Priority: HIGH - Verify everything works**

```bash
# Run the custom test suite
python run_tests.py

# Test API endpoints
curl -X POST http://localhost:8000/api/geocoding/ \
  -H "Content-Type: application/json" \
  -d '{"address": "Hospital São José, Lisboa"}'

# Test map demo
# Visit: http://localhost:8000/map-demo/
```

### 14. Check Health Endpoints

**Priority: MEDIUM - For monitoring**

- Geocoding health: `GET /api/geocoding/health/`
- Routing health: `GET /api/routing/health/`

## Production Deployment

### 15. Web Server Configuration

**Priority: HIGH - For production deployment**

#### Nginx Configuration Example
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location /static/ {
        alias /path/to/static/files/;
    }
    
    location /media/ {
        alias /path/to/media/files/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 16. Process Management

**Priority: HIGH - For production deployment**

#### Using Gunicorn
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn project.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

#### Using systemd (recommended)
Create `/etc/systemd/system/wheelchair-rides.service`:

```ini
[Unit]
Description=Wheelchair Ride-Sharing Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/project
Environment="DJANGO_ENVIRONMENT=production"
ExecStart=/path/to/venv/bin/gunicorn project.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

### 17. SSL Certificate

**Priority: HIGH - For production security**

```bash
# Using Let's Encrypt with Certbot
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## Monitoring and Logging

### 18. Log Directory Setup

**Priority: MEDIUM - For debugging and monitoring**

```bash
# Create logs directory
mkdir -p /path/to/project/logs
chmod 755 /path/to/project/logs

# Ensure Django can write to logs
chown www-data:www-data /path/to/project/logs
```

### 19. Monitoring Setup (Optional)

**Priority: LOW - For advanced monitoring**

Consider setting up:
- **Sentry** for error tracking
- **New Relic** or **DataDog** for performance monitoring
- **Grafana + Prometheus** for custom metrics

## Backup and Maintenance

### 20. Database Backups

**Priority: HIGH - For data protection**

```bash
# PostgreSQL backup script
pg_dump wheelchair_rides > backup_$(date +%Y%m%d).sql

# Set up cron job for automated backups
0 2 * * * /path/to/backup-script.sh
```

### 21. Media Files Backup

**Priority: MEDIUM - For uploaded files**

```bash
# Backup uploaded files (driver documents, etc.)
rsync -av /path/to/media/ backup-server:/backups/media/
```

## Summary of Critical TODOs

### Immediate Actions Required (HIGH Priority)
1. ✅ Get OpenRouteService API key
2. ✅ Set up Cloudflare R2 bucket and upload map tiles
3. ✅ Install and configure Redis
4. ✅ Create .env file with all required variables
5. ✅ Install Python dependencies
6. ✅ Test the implementation with /map-demo/

### Production Deployment (HIGH Priority)
1. ✅ Configure production environment variables
2. ✅ Set up SSL certificates
3. ✅ Configure web server (Nginx/Apache)
4. ✅ Set up process management (systemd/supervisor)
5. ✅ Configure database backups

### Optional Enhancements (MEDIUM/LOW Priority)
1. Set up monitoring and error tracking
2. Implement automated backups
3. Fine-tune rate limiting based on usage
4. Add additional map tile sources for redundancy

## Contact and Support

For technical issues during implementation:
1. Check the health endpoints first
2. Review Django logs in `/path/to/project/logs/`
3. Verify all environment variables are set correctly
4. Test external API connectivity (OpenRouteService, Redis)

## Estimated Time Investment

- **Development Setup**: 2-4 hours
- **External Services Setup**: 4-6 hours
- **Production Deployment**: 6-8 hours
- **Testing and Validation**: 2-3 hours

**Total Estimated Time**: 14-21 hours for complete Phase 1 implementation.

---

*This document was generated as part of the Phase 1 Core Infrastructure implementation. Keep it updated as you complete each task.*