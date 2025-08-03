# Using This Template for Your New Project

This guide walks you through using this Django + Tailwind CSS v4 + Docker template as the foundation for your new project.

## Quick Start (3 minutes)

```bash
# 1. Create new project from template
git clone https://github.com/original-repo/tailwind4-django-how.git my-new-project
cd my-new-project

# 2. Remove template's git history
rm -rf .git

# 3. Initialize your own repository
git init
git add .
git commit -m "Initial commit from Django+Tailwind+Docker template"

# 4. Create and push to your repository
# Create a new repo on GitHub/GitLab first, then:
git remote add origin https://github.com/yourusername/my-new-project.git
git branch -M main
git push -u origin main
```

## Detailed Setup Process

### Step 1: Clone and Prepare Template

```bash
# Clone the template
git clone https://github.com/original-repo/tailwind4-django-how.git my-awesome-app
cd my-awesome-app

# Remove template's git history and remote
rm -rf .git

# Optional: Remove template-specific files
rm TEMPLATE_USAGE_GUIDE.md  # This file
rm TAILWIND_DJANGO_INTEGRATION.md  # Keep if you need reference
```

### Step 2: Customize Project Settings

#### 2.1 Rename Django Project
```bash
# Rename the main project directory (if desired)
mv project myapp

# Update all references in files
# On macOS/Linux:
find . -type f -name "*.py" -o -name "*.yml" -o -name "*.yaml" -o -name "*.sh" -o -name "*.conf" | xargs sed -i '' 's/project/myapp/g'

# On Linux (GNU sed):
find . -type f -name "*.py" -o -name "*.yml" -o -name "*.yaml" -o -name "*.sh" -o -name "*.conf" | xargs sed -i 's/project/myapp/g'
```

#### 2.2 Update Project Metadata
```bash
# Edit package.json
nano package.json
# Update: name, description, author, repository

# Edit Django settings
nano myapp/myapp/settings.py
# Update: ALLOWED_HOSTS, site name, etc.

# Update Docker configs
nano docker-compose.yml
nano docker-compose.prod.yml
# Update: service names if desired
```

### Step 3: Set Up Your Repository

```bash
# Initialize new git repository
git init

# Create initial .gitignore (already exists, but verify)
cat .gitignore

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Django + Tailwind CSS v4 + Docker template

- Django 5.2.1 with production-ready settings
- Tailwind CSS v4 (configuration-free)
- Docker multi-stage builds
- Development and production Docker Compose setups
- Nginx configuration for production
- PostgreSQL database
- Redis caching ready
- Security best practices implemented"
```

### Step 4: Create Remote Repository

#### GitHub
```bash
# Using GitHub CLI
gh repo create my-awesome-app --public --source=. --remote=origin --push

# Or manually:
# 1. Go to https://github.com/new
# 2. Create repository (don't initialize with README)
# 3. Run:
git remote add origin https://github.com/yourusername/my-awesome-app.git
git branch -M main
git push -u origin main
```

#### GitLab
```bash
# 1. Go to https://gitlab.com/projects/new
# 2. Create blank project
# 3. Run:
git remote add origin https://gitlab.com/yourusername/my-awesome-app.git
git branch -M main
git push -u origin main
```

### Step 5: Set Up Development Environment

```bash
# Copy environment file
cp .env.example .env

# Generate new Django secret key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
# Add the generated key to .env

# Start development environment
docker-compose up --build

# In another terminal, run migrations
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### Step 6: Customize for Your Project

#### 6.1 Update README
```bash
# Create your project's README
cat > README.md << 'EOF'
# My Awesome App

Description of your project here.

## Quick Start

```bash
git clone https://github.com/yourusername/my-awesome-app.git
cd my-awesome-app
cp .env.example .env
docker-compose up --build
```

## Tech Stack

- Django 5.2.1
- Tailwind CSS v4
- PostgreSQL
- Docker & Docker Compose
- Nginx (production)

## Development

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed setup instructions.

## License

Your license here
EOF

git add README.md
git commit -m "Add project README"
```

#### 6.2 Create Your First App
```bash
# Create Django app
docker-compose exec web python manage.py startapp core

# Update settings.py to include your app
# Add 'core' to INSTALLED_APPS

# Create your models, views, templates
# The template is ready for your code!
```

### Step 7: Configure CI/CD (Optional)

#### GitHub Actions
```bash
mkdir -p .github/workflows

cat > .github/workflows/django.yml << 'EOF'
name: Django CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    - name: Build Docker images
      run: docker-compose -f docker-compose.yml build
    - name: Run Tests
      run: |
        docker-compose run web python manage.py test
EOF

git add .github
git commit -m "Add GitHub Actions CI workflow"
```

### Step 8: Project-Specific Configurations

```bash
# 1. Update Tailwind CSS for your design system
nano myapp/static/src/styles.css
# Add your custom styles after @import "tailwindcss";

# 2. Configure Django apps structure
mkdir -p myapp/apps
touch myapp/apps/__init__.py
# Organize your apps in a clean structure

# 3. Set up your models
docker-compose exec web python manage.py startapp users
docker-compose exec web python manage.py startapp products
# etc.

# 4. Install additional Python packages
# Add to requirements.txt:
# - djangorestframework==3.14.0  # for APIs
# - django-cors-headers==4.3.1   # for CORS
# - pillow==10.2.0               # for images
# - stripe==7.10.0               # for payments
# etc.

# 5. Install additional npm packages
docker-compose run tailwind npm install alpinejs
# Add to your templates
```

### Step 9: Set Up Deployment

```bash
# 1. Provision your server
# See SERVER_PROVISIONING_GUIDE.md

# 2. Set up production environment
cp .env.prod.example .env.prod
# Edit with real production values

# 3. Set up secrets in your CI/CD
# GitHub: Settings > Secrets
# Add: SERVER_HOST, SERVER_USER, SSH_KEY, etc.

# 4. Configure deployment script
cat > deploy.sh << 'EOF'
#!/bin/bash
# Simple deployment script
ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /home/deploy/my-awesome-app
git pull origin main
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
ENDSSH
EOF

chmod +x deploy.sh
```

### Step 10: Clean Up Template References

```bash
# Remove or update template-specific content
# 1. Update all "tailwind4-django-how" references
grep -r "tailwind4-django-how" . --exclude-dir=.git
# Replace with your project name

# 2. Update landing page content
nano myapp/app/templates/landing.html
# Add your own content

# 3. Update Django admin branding
nano myapp/myapp/settings.py
# Add: ADMIN_SITE_HEADER = "My Awesome App Admin"

# 4. Commit your customizations
git add -A
git commit -m "Customize template for My Awesome App"
git push
```

## Template Features Checklist

Verify these features work for your project:

- [ ] Django development server runs
- [ ] Tailwind CSS hot-reloading works
- [ ] Database migrations work
- [ ] Admin panel accessible
- [ ] Static files served correctly
- [ ] Docker production build succeeds
- [ ] Environment variables load properly
- [ ] Nginx serves the app in production

## Common Customizations

### Adding Django Rest Framework
```bash
# In requirements.txt, add:
echo "djangorestframework==3.14.0" >> requirements.txt

# Rebuild containers
docker-compose up --build

# Add to settings.py:
# INSTALLED_APPS += ['rest_framework']
```

### Adding Celery for Background Tasks
```bash
# In requirements.txt, add:
echo "celery==5.3.4" >> requirements.txt

# Create celery.py in project directory
# Update docker-compose.yml to add celery worker service
```

### Adding User Authentication
```bash
# Use Django's built-in auth or:
echo "django-allauth==0.58.2" >> requirements.txt
# Configure social authentication
```

## Troubleshooting

### Docker build fails
```bash
# Clean Docker cache
docker system prune -a
docker-compose build --no-cache
```

### Port already in use
```bash
# Change ports in docker-compose.yml
# Or stop conflicting service:
sudo lsof -i :8000
sudo kill -9 <PID>
```

### Database connection issues
```bash
# Verify database is running
docker-compose ps
docker-compose logs db

# Recreate database
docker-compose down -v
docker-compose up -d db
docker-compose exec db createdb -U postgres myapp_db
```

## Next Steps

1. **Set up your domain**: Point DNS to your server
2. **Configure SSL**: Use Let's Encrypt for HTTPS
3. **Set up monitoring**: Configure error tracking
4. **Create your apps**: Start building your features
5. **Write tests**: Maintain code quality
6. **Document your API**: If building an API
7. **Set up backups**: Automate database backups

## Keeping Template Updates

To incorporate updates from the original template:

```bash
# Add template as upstream remote
git remote add template https://github.com/original-repo/tailwind4-django-how.git

# Fetch template updates
git fetch template

# Merge carefully (may have conflicts)
git merge template/main --allow-unrelated-histories

# Or cherry-pick specific commits
git cherry-pick <commit-hash>
```

## Support

- Docker issues: Check [DOCKER_SETUP.md](DOCKER_SETUP.md)
- Server setup: See [SERVER_PROVISIONING_GUIDE.md](SERVER_PROVISIONING_GUIDE.md)
- Django docs: https://docs.djangoproject.com/
- Tailwind v4 docs: https://tailwindcss.com/

Happy coding! 🚀