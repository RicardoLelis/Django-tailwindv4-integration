# Gmail Setup Instructions for dev.rlelis@gmail.com

## Step 1: Enable 2-Factor Authentication (if not already enabled)

1. Go to https://myaccount.google.com/security
2. Under "Signing in to Google" find "2-Step Verification"
3. Follow the steps to enable it

## Step 2: Generate App Password

1. Go to https://myaccount.google.com/apppasswords
2. Sign in with dev.rlelis@gmail.com
3. Select app: Choose "Mail"
4. Select device: Choose "Other" and type "RideConnect Dev"
5. Click "Generate"
6. Copy the 16-character password shown (it looks like: xxxx xxxx xxxx xxxx)

## Step 3: Update .env file

Edit the `.env` file and update these lines:

```env
# Comment out the console backend
# EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Uncomment and update Gmail settings
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=dev.rlelis@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx  # <- Paste your app password here (spaces are OK)
DEFAULT_FROM_EMAIL=dev.rlelis@gmail.com
```

## Step 4: Test Email Sending

```bash
python manage.py shell
```

Then in the shell:

```python
from django.core.mail import send_mail
send_mail(
    'Test Email from RideConnect',
    'This is a test email to verify Gmail configuration is working.',
    'dev.rlelis@gmail.com',
    ['dev.rlelis@gmail.com'],  # Send to yourself
    fail_silently=False,
)
```

You should see "1" printed (meaning 1 email sent) and receive the email.

## Security Notes

- The app password is specific to this application
- Never share your app password
- You can revoke it anytime from https://myaccount.google.com/apppasswords
- The .env file is gitignored and won't be committed

## Alternative: Using Console Backend for Testing

If you don't want to set up Gmail right now, the emails will be printed to the console where you run `python manage.py runserver`. This is perfect for development without actually sending emails.