from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Rider, Driver, Vehicle, DriverDocument, VehicleDocument, VehiclePhoto
import re


class DriverInitialRegistrationForm(forms.Form):
    """Simplified initial registration form for drivers"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'your@email.com'
        })
    )
    
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': '+351 XXX XXX XXX'
        })
    )
    
    fleet_size = forms.ChoiceField(
        choices=Driver.FLEET_SIZE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all'
        })
    )
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        # Portuguese phone number validation
        phone_pattern = r'^(\+351\s?)?[0-9]{9}$'
        if not re.match(phone_pattern, phone.replace(' ', '')):
            raise ValidationError("Please enter a valid Portuguese phone number.")
        return phone
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if an active user exists with this email
        if User.objects.filter(email=email, is_active=True).exists():
            raise ValidationError("An account with this email already exists. Please sign in instead.")
        return email

class EmailAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form that uses email instead of username
    """
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Enter your email address',
            'autofocus': True,
        })
    )
    
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Enter your password',
        })
    )
    
    error_messages = {
        'invalid_login': "Please enter a correct email and password. Note that both fields may be case-sensitive.",
        'inactive': "This account is inactive.",
    }

class RiderRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'your@email.com'
        })
    )
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Choose a username'
        })
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Create a strong password'
        })
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Confirm your password'
        })
    )
    
    disabilities = forms.MultipleChoiceField(
        choices=Rider.DISABILITY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select applicable disabilities (check all that apply):"
    )
    
    other_disability = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Please specify other disabilities',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
        }),
        label="Other disability:"
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email.lower()
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
            Rider.objects.create(
                user=user,
                disabilities=self.cleaned_data.get('disabilities', []),
                other_disability=self.cleaned_data.get('other_disability', '')
            )
        return user


# Driver Registration Forms

class DriverCompleteProfileForm(forms.ModelForm):
    """Form for completing driver profile after email verification"""
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'First Name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Last Name'
        })
    )
    
    password = forms.CharField(
        label='Create Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Create a strong password'
        })
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Confirm your password'
        })
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
    
    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise ValidationError('Passwords do not match.')
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class DriverBasicInfoForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'First Name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Last Name'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'your@email.com'
        })
    )
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Choose a username'
        })
    )
    
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': '+351 912 345 678'
        })
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Create a strong password'
        })
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all',
            'placeholder': 'Confirm your password'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email.lower()
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        # Basic Portuguese phone number validation
        phone_pattern = r'^(\+351\s?)?[0-9]{9}$'
        if not re.match(phone_pattern, phone.replace(' ', '')):
            raise ValidationError("Please enter a valid Portuguese phone number.")
        return phone


class DriverEligibilityForm(forms.Form):
    has_portuguese_license = forms.BooleanField(
        required=True,
        label="Do you have a valid Portuguese driving license?",
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-purple-600 rounded focus:ring-purple-500'
        })
    )
    
    has_accessible_vehicle = forms.BooleanField(
        required=True,
        label="Do you own or have access to a wheelchair-accessible vehicle?",
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-purple-600 rounded focus:ring-purple-500'
        })
    )
    
    authorized_to_work = forms.BooleanField(
        required=True,
        label="Are you legally authorized to provide services in Portugal?",
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-purple-600 rounded focus:ring-purple-500'
        })
    )


class DriverProfessionalInfoForm(forms.ModelForm):
    PLATFORM_CHOICES = [
        ('uber', 'Uber'),
        ('bolt', 'Bolt'),
        ('taxi', 'Traditional Taxi'),
        ('medical_transport', 'Medical Transport'),
        ('other', 'Other'),
    ]
    
    LANGUAGE_CHOICES = [
        ('portuguese', 'Portuguese'),
        ('english', 'English'),
        ('spanish', 'Spanish'),
        ('french', 'French'),
        ('german', 'German'),
    ]
    
    HOURS_CHOICES = [
        ('morning', 'Morning (6AM-12PM)'),
        ('afternoon', 'Afternoon (12PM-6PM)'),
        ('evening', 'Evening (6PM-12AM)'),
        ('night', 'Night (12AM-6AM)'),
        ('flexible', 'Flexible'),
    ]
    
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    years_driving = forms.IntegerField(
        min_value=0,
        max_value=50,
        widget=forms.Select(choices=[(i, f"{i} years") for i in range(51)], attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500'
        })
    )
    
    previous_platforms = forms.MultipleChoiceField(
        choices=PLATFORM_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'text-purple-600'
        }),
        required=False
    )
    
    languages = forms.MultipleChoiceField(
        choices=LANGUAGE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'text-purple-600'
        }),
        required=False
    )
    
    working_hours = forms.MultipleChoiceField(
        choices=HOURS_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'text-purple-600'
        }),
        required=False
    )
    
    working_days = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'text-purple-600'
        }),
        required=False
    )
    
    expected_trips_per_week = forms.IntegerField(
        min_value=1,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500',
            'placeholder': '20'
        })
    )
    
    class Meta:
        model = Driver
        fields = ['years_driving', 'previous_platforms', 'disability_experience', 'languages', 
                 'working_hours', 'working_days', 'expected_trips_per_week']
        widgets = {
            'disability_experience': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500'
            })
        }


class DriverDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = DriverDocument
        fields = ['document_type', 'file']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500'
            }),
            'file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500',
                'accept': 'image/*,.pdf'
            })
        }


class BackgroundCheckConsentForm(forms.Form):
    consent_criminal_record = forms.BooleanField(
        required=True,
        label="I consent to a criminal record check for the last 5 years",
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-purple-600 rounded focus:ring-purple-500'
        })
    )
    
    consent_driving_record = forms.BooleanField(
        required=True,
        label="I consent to a driving record check (violations, accidents)",
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-purple-600 rounded focus:ring-purple-500'
        })
    )
    
    consent_identity_verification = forms.BooleanField(
        required=True,
        label="I consent to identity verification",
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-purple-600 rounded focus:ring-purple-500'
        })
    )
    
    digital_signature = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500',
            'placeholder': 'Type your full name as digital signature'
        })
    )


class VehicleBasicInfoForm(forms.ModelForm):
    license_plate = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500',
            'placeholder': 'XX-XX-XX',
            'style': 'text-transform: uppercase;'
        })
    )
    
    make = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500',
            'placeholder': 'Volkswagen'
        })
    )
    
    model = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500',
            'placeholder': 'Caddy'
        })
    )
    
    year = forms.IntegerField(
        widget=forms.Select(choices=[(i, i) for i in range(2030, 1989, -1)], attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500'
        })
    )
    
    insurance_expiry = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500'
        })
    )
    
    inspection_expiry = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500'
        })
    )
    
    class Meta:
        model = Vehicle
        fields = ['license_plate', 'make', 'model', 'year', 'color', 'vehicle_type', 
                 'insurance_expiry', 'inspection_expiry']
        widgets = {
            'color': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500'
            }),
            'vehicle_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500'
            })
        }
    
    def clean_license_plate(self):
        plate = self.cleaned_data.get('license_plate')
        if plate:
            plate = plate.upper().replace(' ', '').replace('-', '')
            # Portuguese license plate format: XX-XX-XX or XX-11-XX
            if not re.match(r'^[A-Z0-9]{6}$', plate):
                raise ValidationError("Please enter a valid Portuguese license plate.")
            return f"{plate[:2]}-{plate[2:4]}-{plate[4:6]}"
        return plate


class VehicleAccessibilityForm(forms.ModelForm):
    EXTRA_FEATURES = [
        ('oxygen_support', 'Oxygen tank support'),
        ('service_animal_friendly', 'Service animal friendly'),
        ('extra_headroom', 'Extra headroom'),
        ('air_conditioning', 'Air conditioning'),
        ('gps_navigation', 'GPS navigation'),
        ('non_slip_surfaces', 'Non-slip surfaces'),
        ('grab_handles', 'Grab handles'),
        ('wide_door', 'Wide doors'),
    ]
    
    wheelchair_capacity = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500',
            'placeholder': '1'
        })
    )
    
    door_width_cm = forms.IntegerField(
        required=False,
        min_value=50,
        max_value=200,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500',
            'placeholder': '80'
        })
    )
    
    extra_features = forms.MultipleChoiceField(
        choices=EXTRA_FEATURES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'text-purple-600'
        }),
        required=False
    )
    
    class Meta:
        model = Vehicle
        fields = ['wheelchair_capacity', 'has_ramp', 'has_lift', 'has_lowered_floor', 
                 'has_swivel_seats', 'has_hand_controls', 'door_width_cm', 'extra_features']
        widgets = {
            'has_ramp': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-purple-600 rounded focus:ring-purple-500'
            }),
            'has_lift': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-purple-600 rounded focus:ring-purple-500'
            }),
            'has_lowered_floor': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-purple-600 rounded focus:ring-purple-500'
            }),
            'has_swivel_seats': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-purple-600 rounded focus:ring-purple-500'
            }),
            'has_hand_controls': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-purple-600 rounded focus:ring-purple-500'
            })
        }


class VehicleSafetyEquipmentForm(forms.Form):
    SAFETY_EQUIPMENT = [
        ('first_aid_kit', 'First aid kit'),
        ('fire_extinguisher', 'Fire extinguisher'),
        ('emergency_contacts', 'Emergency contact numbers displayed'),
        ('wheelchair_manual', 'Wheelchair ramp/lift manual'),
        ('extra_straps', 'Extra wheelchair straps'),
        ('non_slip_surfaces', 'Non-slip surfaces'),
        ('grab_handles', 'Grab handles'),
        ('emergency_alarm', 'Emergency alarm/button'),
    ]
    
    safety_equipment = forms.MultipleChoiceField(
        choices=SAFETY_EQUIPMENT,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'text-purple-600'
        }),
        required=True,
        label="Confirm presence of the following safety equipment:"
    )


class VehicleDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = VehicleDocument
        fields = ['document_type', 'file', 'expiry_date']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500'
            }),
            'file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500',
                'accept': 'image/*,.pdf'
            }),
            'expiry_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500'
            })
        }


class VehiclePhotoUploadForm(forms.ModelForm):
    class Meta:
        model = VehiclePhoto
        fields = ['photo_type', 'image', 'description']
        widgets = {
            'photo_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500'
            }),
            'image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500',
                'accept': 'image/*'
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Optional description'
            })
        }