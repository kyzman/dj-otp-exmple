from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.models import Profile
from accounts.utils import phone_regex


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
    phone = serializers.CharField(max_length=10, validators=[phone_regex])
    invite = serializers.CharField(read_only=True)
    login_url = serializers.CharField(read_only=True)


class ProfileInUserSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=10, validators=[phone_regex], required=True)
    email = serializers.EmailField(allow_blank=True, allow_null=True, required=False)
    first_name = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    last_name = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    invited = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('phone', 'email', 'first_name', 'last_name')


class ProfileOutUserSerializer(serializers.Serializer):
    user = serializers.CharField(write_only=True)
    phone = serializers.CharField(write_only=True)
    email = serializers.EmailField(allow_blank=True, allow_null=True, required=False)
    first_name = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    last_name = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    invite = serializers.CharField(write_only=True)
    invited = serializers.CharField(allow_null=True, allow_blank=True)
    followers = serializers.JSONField(write_only=True)


