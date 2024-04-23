from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.models import Profile


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = ('phone', 'email', 'first_name', 'last_name')


class ProfileSerializer(serializers.ModelSerializer):
    invite = serializers.CharField(read_only=True)
    user = UserSerializer()

    # def create(self, validated_data):

    class Meta:
        model = Profile
        fields = ('pk', 'user', 'invite', 'invited')
        # read_only_fields = ('pk', 'invite',)
