from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.models import Profile


class ProfileUserForm(forms.ModelForm):
    phone = forms.CharField(disabled=True, label="Телефон(логин) +7",
                            widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(label="Email",
                             widget=forms.EmailInput(attrs={'class': 'form-input'}), required=False)
    invited = forms.CharField(disabled=True, label="Код приглашения",
                              widget=forms.TextInput(attrs={'class': 'form-input'}), required=False)

    def __init__(self, *args, **kwargs):
        super(ProfileUserForm, self).__init__(*args, **kwargs)
        if not self.initial.get('invited'):
            self.fields['invited'].disabled = False

    def clean(self):
        cleaned_data = super().clean()
        invited = cleaned_data.get('invited')
        if invited:
            current_invite = Profile.objects.get(
                user=get_user_model().objects.filter(phone=cleaned_data.get('phone')).first()).invite
            if current_invite == invited:
                raise ValidationError('Нельзя приглашать самого себя!')
            valid_invite = Profile.objects.filter(invite=invited)
            if not valid_invite:
                raise ValidationError('Такого пригласительного не существует!')

    class Meta:
        model = get_user_model()
        fields = ['phone', 'email', 'first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
        }
