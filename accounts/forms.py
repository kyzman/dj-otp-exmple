from django import forms
from django.contrib.auth import get_user_model


class ProfileUserForm(forms.ModelForm):
    phone = forms.CharField(disabled=True, label="Телефон(логин) +7",  widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'class': 'form-input'}))

    class Meta:
        model = get_user_model()
        fields = ['phone', 'email', 'first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
        }
