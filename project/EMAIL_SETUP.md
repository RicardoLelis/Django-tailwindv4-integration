# Email Configuration Guide

This guide explains how to set up email sending for RideConnect.

## Quick Setup

Run the interactive setup script:

```bash
python setup_email.py
```

## Manual Setup

### Option 1: Gmail (Development/Testing)

1. **Get a Gmail App Password:**
   - Go to https://myaccount.google.com/apppasswords
   - Sign in to your Google Account
   - Select "Mail" as the app
   - Select your device
   - Click "Generate"
   - Copy the 16-character password

2. **Create a `.env` file:**
   ```env
   # Email Configuration - Gmail
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=dev.rlelis@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password-here
   DEFAULT_FROM_EMAIL=dev.rlelis@gmail.com
   ```

### Option 2: Amazon SES (Production)

1. **Set up AWS SES:**
   - Create an AWS account
   - Verify your domain in SES
   - Create IAM credentials with SES permissions

2. **Create a `.env` file:**
   ```env
   # Email Configuration - Amazon SES
   EMAIL_BACKEND=django_ses.SESBackend
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_SES_REGION_NAME=eu-west-1
   AWS_SES_REGION_ENDPOINT=email.eu-west-1.amazonaws.com
   DEFAULT_FROM_EMAIL=noreply@rideconnect.pt
   ```

### Option 3: Console (Local Development)

For development without sending real emails:

```env
# Email Configuration - Console
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@rideconnect.pt
```

Emails will be printed to the console instead of being sent.

## Testing Email Configuration

After setup, test your email configuration:

```python
python manage.py shell
```

```python
from django.core.mail import send_mail
send_mail(
    'Test Subject',
    'Test message body',
    'from@example.com',
    ['to@example.com'],
    fail_silently=False,
)
```

## Security Notes

- **Never commit `.env` files** to version control
- Use strong, unique passwords
- Rotate credentials regularly
- For production, use dedicated email services like Amazon SES
- Set appropriate file permissions: `chmod 600 .env`

## Troubleshooting

### Gmail Issues
- Enable 2-factor authentication on your Google account
- Use App Passwords, not your regular password
- Check if "Less secure app access" is needed (not recommended)

### Amazon SES Issues
- Verify your sending domain
- Check if you're in sandbox mode
- Ensure IAM permissions include `ses:SendEmail`

### General Issues
- Check firewall settings for SMTP ports
- Verify credentials are correct
- Check spam folders for test emails