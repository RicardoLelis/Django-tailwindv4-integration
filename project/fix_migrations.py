#!/usr/bin/env python3
import os
import subprocess
import sys

def run_command(command, description):
    print(f"🔄 {description}...")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(f"Command: {command}")
    if result.stdout.strip():
        print(f"Output: {result.stdout}")
    if result.stderr.strip():
        print(f"Error: {result.stderr}")
    return result.returncode == 0

def main():
    os.chdir('/Users/lelisra/Documents/code/tailwind4-django-how/project')
    
    # Remove the conflicting migration I created manually
    conflicting_file = 'app/migrations/0009_add_missing_drivercalendar_fields.py'
    if os.path.exists(conflicting_file):
        print(f"🗑️  Removing conflicting migration: {conflicting_file}")
        os.remove(conflicting_file)
    
    # Activate virtual environment and merge migrations
    commands = [
        ("source ../venv/bin/activate && python manage.py makemigrations --merge", "Merging conflicting migrations"),
        ("source ../venv/bin/activate && python manage.py migrate", "Applying all migrations"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            print(f"❌ Failed at: {description}")
            return False
    
    print("✅ All migrations completed successfully!")
    return True

if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)