import random

from django.contrib.auth import get_user_model, login, logout
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import render, redirect

from accounts.mixins import OtpSender
from accounts.models import Profile


def login_view(request: WSGIRequest):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        user = get_user_model().objects.filter(phone=phone).first()
        profile = Profile.objects.filter(user=user).first()
        if not profile:  # если профиля с таким номером нет, то создаём его.
            user = get_user_model().objects.create(phone=phone)
            profile = Profile.objects.create(user=user)

        profile.otp = random.randint(999, 9999)
        profile.save()
        sender = OtpSender(user.phone, profile.otp).send_otp_on_phone()

        return redirect(f'/otp/{user.phone}')

    return render(request, 'accounts/login.html')


def profile_view(request: WSGIRequest):
    return render(request, 'accounts/profile.html')


def otp(request: WSGIRequest, phone):
    if request.method == 'POST':
        otp = int(request.POST.get('otp'))
        profile = Profile.objects.get(user=get_user_model().objects.get(phone=phone))
        if otp == profile.otp:
            login(request, profile.user)
            return redirect('/profile/')

        return redirect(f'/otp/{phone}')

    return render(request, 'accounts/otp.html')


def logout_view(request: WSGIRequest):
    logout(request)
    return redirect('/')
