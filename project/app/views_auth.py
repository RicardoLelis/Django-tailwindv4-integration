from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView, 
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib import messages
from django.shortcuts import render, redirect
from django import forms


class CustomPasswordResetForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Enter your registered email'
        })
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        # Check if user exists with this email
        if not User.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError("No active account found with this email address.")
        return email

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """Send password reset email"""
        subject = render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())  # Remove newlines
        
        # Get the user
        user = User.objects.get(email=to_email, is_active=True)
        context['user'] = user
        
        # Render HTML email
        html_message = render_to_string(html_email_template_name or email_template_name, context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

    def save(self, domain_override=None, subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html', use_https=False,
             token_generator=default_token_generator, from_email=None, request=None,
             html_email_template_name=None, extra_email_context=None):
        """Generate a one-use only link for resetting password and send it to the user."""
        email = self.cleaned_data["email"]
        
        for user in User.objects.filter(email=email, is_active=True):
            context = {
                'email': user.email,
                'domain': domain_override or (request.get_host() if request else 'localhost:8000'),
                'site_name': 'RideConnect',
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
            }
            if extra_email_context is not None:
                context.update(extra_email_context)
                
            self.send_mail(
                subject_template_name, email_template_name, context, from_email,
                user.email, html_email_template_name=html_email_template_name,
            )


class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    html_email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    
    def form_valid(self, form):
        messages.success(self.request, 'Password reset email sent successfully!')
        return super().form_valid(form)


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')
    
    def form_valid(self, form):
        messages.success(self.request, 'Your password has been successfully reset!')
        return super().form_valid(form)


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'