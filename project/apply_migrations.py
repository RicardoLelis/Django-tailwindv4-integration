#!/usr/bin/env python3
import os
import sys
import subprocess

def run_command(command, description):
    print(f"🔄 {description}...")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ {description} completed successfully!")
        if result.stdout.strip():
            print(result.stdout)
    else:
        print(f"❌ {description} failed!")
        print(f"Error: {result.stderr}")
        return False
    return True

def main():
    # Change to project directory
    os.chdir('/Users/lelisra/Documents/code/tailwind4-django-how/project')
    
    # Activate virtual environment and run migrations
    commands = [
        ("source ../venv/bin/activate && python manage.py showmigrations app", "Checking migration status"),
        ("source ../venv/bin/activate && python manage.py migrate", "Applying migrations"),
        ("source ../venv/bin/activate && python -c \"import django; django.setup(); from django.db import connection; cursor = connection.cursor(); cursor.execute('PRAGMA table_info(app_drivercalendar)'); print('Table structure:'); [print(row) for row in cursor.fetchall()]\"", "Checking table structure")
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            sys.exit(1)

if __name__ == '__main__':
    main()