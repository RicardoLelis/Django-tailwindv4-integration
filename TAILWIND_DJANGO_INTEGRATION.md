# How to Integrate Tailwind CSS v4 with Django

This guide provides step-by-step instructions for integrating Tailwind CSS v4 (configuration-free) with a Django project.

## Prerequisites

- Python 3.x installed
- Node.js and npm installed
- Basic Django project set up

## Step 1: Initialize npm and Install Tailwind CSS

In your Django project root directory, initialize npm and install Tailwind CSS v4:

```bash
npm init -y
npm install --save-dev tailwindcss@next @tailwindcss/cli@next
```

**Note**: Tailwind v4 uses `@next` tag for the latest v4 versions. Check for the latest stable v4 release.

## Step 2: Create Directory Structure for Static Files

Create the following directory structure in your Django project:

```
project/
├── static/
│   ├── src/
│   │   └── styles.css
│   └── dist/
│       └── (compiled CSS will go here)
```

## Step 3: Create Source CSS File

Create `/static/src/styles.css` with the following content:

```css
@import "tailwindcss";
```

That's it! Tailwind v4 doesn't require `@tailwind` directives or a configuration file.

## Step 4: Configure npm Scripts

Update your `package.json` to include build and watch scripts:

```json
{
  "scripts": {
    "build:css": "tailwindcss -i ./project/static/src/styles.css -o ./project/static/dist/styles.css",
    "watch:css": "tailwindcss -i ./project/static/src/styles.css -o ./project/static/dist/styles.css --watch"
  }
}
```

Adjust paths according to your project structure.

## Step 5: Configure Django Settings

In your Django `settings.py`, ensure static files are properly configured:

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

# Additional directories for static files
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# For production (when running collectstatic)
STATIC_ROOT = BASE_DIR / "staticfiles"
```

## Step 6: Create Base Template

Create a base template (e.g., `templates/base.html`) that includes the compiled Tailwind CSS:

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}My Django App{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'dist/styles.css' %}">
</head>
<body>
    {% block content %}
    {% endblock %}
</body>
</html>
```

## Step 7: Configure Template Settings

Ensure Django knows where to find your templates in `settings.py`:

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Add this line
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
```

## Step 8: Build and Watch CSS

For development, run the watch command in a separate terminal:

```bash
npm run watch:css
```

This will automatically recompile your CSS whenever you make changes to your templates or styles.

For production builds:

```bash
npm run build:css
```

## Step 9: Use Tailwind Classes in Templates

Create templates that extend your base template and use Tailwind classes:

```html
{% extends 'base.html' %}

{% block title %}Home{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1 class="text-4xl font-bold text-gray-900 mb-4">
        Welcome to Django with Tailwind v4
    </h1>
    <p class="text-lg text-gray-600">
        This is using Tailwind CSS v4 with no configuration file!
    </p>
</div>
{% endblock %}
```

## Key Differences from Tailwind v3

1. **No Configuration File**: Tailwind v4 doesn't require `tailwind.config.js`
2. **Simplified CSS Import**: Just use `@import "tailwindcss";` instead of multiple directives
3. **Built-in Defaults**: v4 comes with sensible defaults out of the box
4. **Performance**: Faster builds due to the new architecture

## Development Workflow

1. Start your Django development server: `python manage.py runserver`
2. In another terminal, start Tailwind CSS watcher: `npm run watch:css`
3. Edit your templates and see changes reflected immediately

## Production Considerations

1. **Build CSS**: Run `npm run build:css` before deployment
2. **Minification**: Add `--minify` flag to your build command for production:
   ```json
   "build:css": "tailwindcss -i ./project/static/src/styles.css -o ./project/static/dist/styles.css --minify"
   ```
3. **Static Files**: Run Django's `collectstatic` command:
   ```bash
   python manage.py collectstatic
   ```

## Troubleshooting

### CSS Not Loading
- Check that `STATICFILES_DIRS` includes your static directory
- Ensure the compiled CSS file exists in `static/dist/`
- Verify the path in your template's `{% static %}` tag

### Tailwind Classes Not Working
- Make sure the watch/build command is running
- Check that you're using valid Tailwind v4 class names
- Clear your browser cache

### Build Errors
- Ensure you're using compatible versions of Node.js (14.x or higher)
- Check that all paths in npm scripts are correct
- Try deleting `node_modules` and running `npm install` again

## Additional Configuration (Optional)

### Custom Styles
Add custom CSS after the Tailwind import in `styles.css`:

```css
@import "tailwindcss";

/* Your custom styles here */
.custom-class {
    /* Custom CSS */
}
```

### Using with Django Apps
For app-specific templates, create a templates directory within your app:

```
myapp/
├── templates/
│   └── myapp/
│       └── page.html
```

And ensure `APP_DIRS` is set to `True` in your template configuration.

## Summary

This setup provides a minimal, configuration-free integration of Tailwind CSS v4 with Django. The key is understanding the new v4 approach where configuration is optional and the framework provides sensible defaults out of the box.