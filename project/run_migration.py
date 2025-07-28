import os
import sys
import django

# Add project to path
sys.path.insert(0, '/Users/lelisra/Documents/code/tailwind4-django-how/project')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.core.management import execute_from_command_line

try:
    print("Running migration...")
    execute_from_command_line(['manage.py', 'migrate'])
    print("Migration completed successfully!")
except Exception as e:
    print(f"Migration failed: {e}")