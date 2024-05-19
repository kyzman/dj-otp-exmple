from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models

from accounts.utils import generate_code, phone_regex


class PhoneUserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    def _create_user(self, phone, password=None, **extra_fields):
        """Create and save a User with the given phone and password."""
        if not phone:
            raise ValueError('Введите номер телефона!')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        """Create and save a SuperUser with the given phone and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(phone, password, **extra_fields)


class MobilePhoneOnlyUser(AbstractUser):
    username = None
    phone = models.CharField(max_length=10, validators=[phone_regex], unique=True)

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    objects = PhoneUserManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(check=models.Q(phone__regex=r"^9\d{9}$"), name="CK_phone"),
        ]


class Profile(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='Profile')
    otp = models.IntegerField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/')
    otptime = models.DateTimeField(null=True, blank=True)
    otpattempts = models.IntegerField(null=True, blank=True)
    invite = models.CharField(max_length=6, unique=True, default=generate_code)
    invited = models.CharField(max_length=6, null=True, blank=True)

    def __str__(self):
        return f"{self.user}"
