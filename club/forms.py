from django import forms
from .models import Profile

class PhoneForm(forms.Form):
    phone = forms.CharField(
        max_length=24,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your phone number'})
    )

class OTPForm(forms.Form):
    phone = forms.CharField(widget=forms.HiddenInput())
    code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit code'})
    )

class ProfileCompletionForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['first_name', 'second_name', 'county', 'buyer_type']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'second_name': forms.TextInput(attrs={'placeholder': 'Second Name'}),
            'county': forms.Select(attrs={'class': 'form-select'}),
            'buyer_type': forms.RadioSelect(),
        }
        labels = {
            'first_name': 'First Name',
            'second_name': 'Second Name',
            'county': 'County',
            'buyer_type': 'I am buying for:',
        }
