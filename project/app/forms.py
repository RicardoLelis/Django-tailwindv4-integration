from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Rider

class RiderRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
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
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Rider.objects.create(
                user=user,
                disabilities=self.cleaned_data.get('disabilities', []),
                other_disability=self.cleaned_data.get('other_disability', '')
            )
        return user