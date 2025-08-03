# Docker Setup Guide for Django + Tailwind CSS v4

This guide explains how to deploy this Django + Tailwind CSS v4 application using Docker on a remote Linux machine.

## Prerequisites

On your remote Linux machine, you need:
- Docker Engine (20.10+)
- Docker Compose (2.0+)
- Git (to clone the repository)

## Project Structure

```
.
├── Dockerfile                 # Multi-stage build for production
├── docker-compose.yml        # Development configuration
├── docker-compose.prod.yml   # Production configuration
├── docker-entrypoint.sh      # Django initialization script
├── .dockerignore            # Files to exclude from Docker build
├── .env.example             # Development environment template
├── .env.prod.example        # Production environment template
├── requirements.txt         # Python dependencies
├── nginx/                   # Nginx configuration
│   ├── nginx.conf          # Main Nginx config
│   └── conf.d/
│       └── django.conf     # Django-specific config
└── project/                 # Django project files

```

## Quick Start - Development

1. **Clone the repository on your remote machine:**
   ```bash
   git clone <your-repo-url>
   cd tailwind4-django-how
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Build and run the development environment:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - Django app: http://your-server-ip:8000
   - Admin panel: http://your-server-ip:8000/admin (user: admin, pass: admin)

## Production Deployment

1. **Set up production environment variables:**
   ```bash
   cp .env.prod.example .env.prod
   # Edit .env.prod with secure production values
   ```

2. **Build and run the production environment:**
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```

3. **Access the application:**
   - Nginx serves the app on port 80
   - Static files are served directly by Nginx
   - Gunicorn runs the Django application

## Docker Architecture

### Multi-Stage Dockerfile

The Dockerfile uses a multi-stage build for optimization:

1. **Stage 1 - Tailwind Builder:**
   - Uses Node.js Alpine image
   - Builds and minifies Tailwind CSS
   - Outputs compiled CSS to `static/dist/`

2. **Stage 2 - Python Builder:**
   - Creates virtual environment
   - Installs Python dependencies
   - Compiles Python packages

3. **Stage 3 - Runtime:**
   - Minimal Python image
   - Copies only necessary files
   - Runs as non-root user (django)
   - Includes health checks

### Development vs Production

**Development (`docker-compose.yml`):**
- Hot-reloading for Django and Tailwind
- Debug mode enabled
- Volumes for live code updates
- Runs Django development server
- Tailwind watch mode for CSS changes

**Production (`docker-compose.prod.yml`):**
- Nginx reverse proxy
- Gunicorn WSGI server
- Redis for caching
- Optimized for performance
- Security headers configured
- SSL/TLS ready (configure certificates)

## Best Practices Implemented

### 1. **Security**
- Non-root user in containers
- Environment variables for secrets
- Security headers in Nginx
- No sensitive data in images
- Minimal base images

### 2. **Performance**
- Multi-stage builds (smaller images)
- Layer caching optimization
- Static file serving via Nginx
- Gzip compression enabled
- Connection pooling for database

### 3. **Reliability**
- Health checks for all services
- Automatic container restarts
- Graceful shutdown handling
- Database connection retry logic
- Proper logging configuration

### 4. **Maintainability**
- Clear service separation
- Environment-specific configs
- Volumes for persistent data
- Documented configuration
- Consistent naming conventions

## Common Commands

### Development

```bash
# Start services
docker-compose up

# Rebuild after changes
docker-compose up --build

# Run Django commands
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# View logs
docker-compose logs -f web
docker-compose logs -f tailwind

# Stop services
docker-compose down
```

### Production

```bash
# Start services in background
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale web service
docker-compose -f docker-compose.prod.yml up -d --scale web=3

# Update application
git pull
docker-compose -f docker-compose.prod.yml up --build -d

# Backup database
docker-compose -f docker-compose.prod.yml exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql
```

## Environment Variables

### Required Variables

- `SECRET_KEY`: Django secret key (generate a secure one for production)
- `POSTGRES_USER`: Database username
- `POSTGRES_PASSWORD`: Database password (use strong password in production)
- `POSTGRES_DB`: Database name
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts

### Optional Variables

- `DEBUG`: Set to False in production
- `SENTRY_DSN`: For error tracking
- `EMAIL_*`: Email configuration
- `REDIS_URL`: Redis connection string

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs web

# Verify environment variables
docker-compose config

# Check if ports are available
sudo netstat -tlnp | grep :8000
```

### Database connection issues
```bash
# Check if database is ready
docker-compose exec db pg_isready

# Manually connect to database
docker-compose exec db psql -U $POSTGRES_USER $POSTGRES_DB
```

### Static files not loading
```bash
# Collect static files manually
docker-compose exec web python manage.py collectstatic --noinput

# Check nginx logs
docker-compose logs nginx
```

### Permission issues
```bash
# Fix ownership
docker-compose exec web chown -R django:django /app

# Check file permissions
docker-compose exec web ls -la /app/staticfiles
```

## Monitoring and Logs

### Application Logs
- Django logs: `docker-compose logs web`
- Nginx logs: `docker-compose logs nginx`
- Database logs: `docker-compose logs db`

### Performance Monitoring
- Use `docker stats` to monitor resource usage
- Configure Prometheus/Grafana for advanced monitoring
- Set up alerts for critical metrics

## Backup Strategy

1. **Database Backups:**
   ```bash
   # Create backup script
   #!/bin/bash
   BACKUP_DIR="/backups"
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)
   docker-compose exec -T db pg_dump -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_DIR/db_$TIMESTAMP.sql
   ```

2. **Media Files:**
   ```bash
   # Backup media files
   docker run --rm -v media_volume:/data -v /backups:/backup alpine tar czf /backup/media_$TIMESTAMP.tar.gz -C /data .
   ```

## Security Checklist

- [ ] Change default passwords
- [ ] Generate new SECRET_KEY
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Enable CSRF protection
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up regular backups
- [ ] Monitor logs for suspicious activity
- [ ] Keep Docker images updated
- [ ] Use secrets management for sensitive data

## Next Steps

1. **SSL/TLS Setup:**
   - Use Let's Encrypt with certbot
   - Or configure custom certificates

2. **CI/CD Pipeline:**
   - Automate builds with GitHub Actions
   - Or use GitLab CI/CD

3. **Scaling:**
   - Add load balancer
   - Configure horizontal scaling
   - Set up database replication

4. **Monitoring:**
   - Add application performance monitoring
   - Set up error tracking (Sentry)
   - Configure uptime monitoring