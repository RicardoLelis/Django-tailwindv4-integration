#!/usr/bin/env python3
"""
Script to securely set up email configuration for development
"""
import os
import getpass
from pathlib import Path

def setup_email_config():
    """Interactive setup for email configuration"""
    env_path = Path('.env')
    
    print("=== RideConnect Email Configuration Setup ===\n")
    
    # Check if .env exists
    if env_path.exists():
        overwrite = input(".env file already exists. Overwrite? (y/N): ").lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    print("\nChoose email configuration:")
    print("1. Gmail (for development/testing)")
    print("2. Amazon SES (for production)")
    print("3. Console (print to terminal only)")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    env_content = []
    
    # Add Django settings
    env_content.append("# Django Settings")
    env_content.append("SECRET_KEY=django-insecure-qw0=8ln_@0ag*=4jsi_96&uxvjap-au@6r*odl(srf-op@1uzq")
    env_content.append("DEBUG=True")
    env_content.append("ALLOWED_HOSTS=localhost,127.0.0.1")
    env_content.append("")
    
    if choice == '1':
        # Gmail configuration
        print("\n=== Gmail Configuration ===")
        print("You need an App Password from Google:")
        print("1. Go to https://myaccount.google.com/apppasswords")
        print("2. Sign in to your Google Account")
        print("3. Create a new app password for 'Mail'")
        print("4. Copy the 16-character password\n")
        
        email = input("Gmail address (default: dev.rlelis@gmail.com): ").strip()
        if not email:
            email = "dev.rlelis@gmail.com"
        
        password = getpass.getpass("Gmail App Password (hidden): ").strip()
        
        env_content.append("# Email Configuration - Gmail")
        env_content.append("EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend")
        env_content.append("EMAIL_HOST=smtp.gmail.com")
        env_content.append("EMAIL_PORT=587")
        env_content.append("EMAIL_USE_TLS=True")
        env_content.append(f"EMAIL_HOST_USER={email}")
        env_content.append(f"EMAIL_HOST_PASSWORD={password}")
        env_content.append(f"DEFAULT_FROM_EMAIL={email}")
        
    elif choice == '2':
        # Amazon SES configuration
        print("\n=== Amazon SES Configuration ===")
        print("You need AWS credentials with SES permissions.")
        
        aws_key = input("AWS Access Key ID: ").strip()
        aws_secret = getpass.getpass("AWS Secret Access Key (hidden): ").strip()
        region = input("AWS SES Region (default: eu-west-1): ").strip() or "eu-west-1"
        from_email = input("From Email (default: noreply@rideconnect.pt): ").strip() or "noreply@rideconnect.pt"
        
        env_content.append("# Email Configuration - Amazon SES")
        env_content.append("EMAIL_BACKEND=django_ses.SESBackend")
        env_content.append(f"AWS_ACCESS_KEY_ID={aws_key}")
        env_content.append(f"AWS_SECRET_ACCESS_KEY={aws_secret}")
        env_content.append(f"AWS_SES_REGION_NAME={region}")
        env_content.append(f"AWS_SES_REGION_ENDPOINT=email.{region}.amazonaws.com")
        env_content.append(f"DEFAULT_FROM_EMAIL={from_email}")
        
    else:
        # Console backend
        env_content.append("# Email Configuration - Console")
        env_content.append("EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend")
        env_content.append("DEFAULT_FROM_EMAIL=noreply@rideconnect.pt")
    
    # Write to .env file
    with open(env_path, 'w') as f:
        f.write('\n'.join(env_content))
    
    # Set appropriate permissions (readable only by owner)
    os.chmod(env_path, 0o600)
    
    print(f"\n✅ Configuration saved to .env")
    print("⚠️  Remember to add .env to your .gitignore file!")
    
    # Check if .gitignore exists and add .env if needed
    gitignore_path = Path('.gitignore')
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            content = f.read()
        if '.env' not in content:
            with open(gitignore_path, 'a') as f:
                f.write('\n# Environment variables\n.env\n')
            print("✅ Added .env to .gitignore")

if __name__ == "__main__":
    setup_email_config()