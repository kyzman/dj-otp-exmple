from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from rest_framework import serializers

from accounts.models import Profile


class UserPhoneSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = ('phone',)


class OTPSerializer(serializers.ModelSerializer):
    user = UserPhoneSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = ('user', 'otp')


class LoginUserSerializer(serializers.Serializer):
    phone_regex = RegexValidator(regex=r'^9\d{9}$',
                                 message="Введите мобильный номер телефона в формате: '9001112233' - 9 цифр подряд, без кода страны. Только Россия!")
    phone = serializers.CharField(max_length=10, validators=[phone_regex])
    invite = serializers.CharField(read_only=True)
    login_url = serializers.CharField(read_only=True)

