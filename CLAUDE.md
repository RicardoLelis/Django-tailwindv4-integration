# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Django Development
- **Start development server**: `cd project && python manage.py runserver` (runs on http://localhost:8000)
- **Run migrations**: `cd project && python manage.py migrate`
- **Create migrations**: `cd project && python manage.py makemigrations`
- **Run tests**: `cd project && python run_tests.py` (custom test runner with mocked Django dependencies)
- **Create superuser**: `cd project && python manage.py createsuperuser`

### CSS/Frontend Development
- **Build CSS**: `./build-css.sh` (builds Tailwind CSS from `project/static/src/styles.css` to `project/static/dist/styles.css`)
- **Watch CSS**: `npm run watch:css` (watches for changes and rebuilds automatically)

### Environment Setup
- **Dependencies**: `pip install -r project/requirements.txt` and `npm install` (for Tailwind CSS)
- **Redis**: Required for caching and sessions - install via `brew install redis && brew services start redis`
- **Environment file**: Create `.env` in project directory with `SECRET_KEY`, `DEBUG`, and `REDIS_URL`

## Project Architecture

### High-Level Structure
This is a Django-based wheelchair-accessible ride-sharing platform with the following key components:

**Core Application**: Located in `project/app/` - main Django application containing all business logic
**Settings Architecture**: Multi-environment settings in `project/project/settings/` (base.py, development.py)
**Service Layer**: Business logic encapsulated in `project/app/services/` modules
**API Layer**: RESTful APIs in `project/app/api/` using Django REST Framework

### Key Models (project/app/models.py)
- **Rider**: Users needing wheelchair-accessible transportation with disability specifications
- **Driver**: Service providers with multi-stage approval workflow (email verification → documents → background check → training → approval)
- **Vehicle**: Driver vehicles with accessibility features and safety equipment
- **Ride/PreBookedRide**: Trip requests with real-time and pre-booking capabilities
- **TrainingModule**: Driver education and certification system

### Service Architecture
Located in `project/app/services/`:
- **GeocodingService**: Address validation and coordinate conversion with service area bounds
- **RoutingService**: Wheelchair-accessible route calculation with fallback mechanisms
- **BookingService**: Ride matching and scheduling logic
- **NotificationService**: Email and system notifications
- **PricingService**: Dynamic fare calculation

### API Structure
RESTful endpoints in `project/app/api/`:
- **Geocoding APIs**: `/api/geocoding/` - address validation, reverse geocoding, service area validation
- **Routing APIs**: `/api/routing/` - wheelchair routes, driving routes, accessibility calculations
- **Booking APIs**: `/api/bookings/` - pre-booked ride management
- **Calendar APIs**: `/api/calendar/` - driver availability management

### Frontend Integration
- **Tailwind CSS 4.x**: Modern utility-first CSS framework
- **Template Architecture**: Django templates in `project/app/templates/` with driver/rider separation
- **JavaScript Components**: Map integration and address autocomplete in `project/static/js/`

### Development Environment Features
- **Multi-environment settings**: Automatic environment detection (development/staging/production)
- **Redis fallback**: Graceful degradation to in-memory cache if Redis unavailable
- **Rate limiting**: Configurable API throttling for external services
- **Email backends**: Console backend for development, configurable for production

### Key Configuration
- **Service Area**: Currently configured for Lisbon, Portugal region
- **External APIs**: Nominatim (geocoding) and OpenRouteService (routing) integration
- **Security**: CORS headers, rate limiting, and input validation throughout
- **Accessibility Focus**: All routes and features designed with wheelchair accessibility as primary consideration

### Testing Strategy
Custom test runner (`run_tests.py`) that mocks Django dependencies for service-level testing without full Django setup. Tests focus on:
- Service layer business logic validation
- API endpoint input/output validation
- Geocoding and routing service integration
- Rate limiting and caching behavior

### File Upload Handling
Driver documents and vehicle photos are uploaded to `project/media/` with UUID-based filenames for security.