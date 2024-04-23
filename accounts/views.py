import datetime
import random

from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from accounts.forms import ProfileUserForm
from accounts.utils import OtpSender, generate_code
from accounts.models import Profile
from config import settings


def login_view(request: WSGIRequest):
    error = False
    message = ''
    if request.method == 'POST':
        phone = request.POST.get('phone')
        invited = request.POST.get('invited')
        user = get_user_model().objects.filter(phone=phone).first()
        profile = Profile.objects.filter(user=user).first()
        valid_invite = Profile.objects.filter(invite=invited)
        if not profile:  # если профиля с таким номером нет, то проверяем приглашение
            if valid_invite or not invited:  # если приглашение корректное или его нет
                try:
                    user = get_user_model().objects.create(phone=phone)
                    profile = Profile.objects.create(user=user, invite=generate_code(), invited=invited)
                except Exception as err:
                    error = True
                    message = f'Ошибка создания записи {err}'
            else:  # если не корректное приглашение
                error = True
                message = "Введён не корректный пригласительный код!"
        if error:
            pass
        else:
            if last_otp_time := profile.otptime:
                timedelta = datetime.datetime.utcnow() - last_otp_time.replace(tzinfo=None)
            else:
                timedelta = datetime.timedelta(seconds=settings.OTP_RETRY_TIMEOUT+1)
            if not last_otp_time or timedelta.seconds > settings.OTP_RETRY_TIMEOUT:
                if not profile.invited and valid_invite:
                    profile.invited = invited
                profile.otp = random.randint(999, 9999)
                profile.otptime = datetime.datetime.utcnow()
                profile.otpattempts = settings.OTP_ATTEMPTS
                profile.save()
                sender = OtpSender(user.phone, profile.otp).send_otp_on_phone()

                return redirect(f'/otp/{user.phone}')
            else:
                error = True
                message = "Превышено время повторной выдачи пароля. Попробуйте позже!"

    return render(request, 'accounts/login.html', {'error': error, 'msg': message})


class ProfileUser(LoginRequiredMixin, UpdateView):
    model = get_user_model()
    form_class = ProfileUserForm
    template_name = 'accounts/profile.html'
    extra_context = {'title': "Профиль пользователя"}

    def get_invite_code(self):
        return Profile.objects.get(user=self.request.user).invite

    def get_all_followers(self, invite_code):
        return list(Profile.objects.filter(invited=invite_code).all().values('user__phone'))

    def get_context_data(self, **kwargs):
        context = super(ProfileUser, self).get_context_data(**kwargs)
        context['invite'] = self.get_invite_code()
        context['followers'] = self.get_all_followers(context['invite'])
        return context

    def get_success_url(self):
        return reverse_lazy('profile', args=[self.request.user.pk])

    def get_object(self, queryset=None):
        return self.request.user


def otp(request: WSGIRequest, phone):
    error = False
    message = ''
    if request.method == 'POST':
        otp = int(request.POST.get('otp'))
        profile = Profile.objects.get(user=get_user_model().objects.get(phone=phone))
        profile.otpattempts -= 1
        timedelta = datetime.datetime.utcnow() - profile.otptime.replace(tzinfo=None)
        try:
            profile.save()
            if timedelta.seconds < settings.OTP_LIFETIME:
                if profile.otpattempts > 0:
                    if otp == profile.otp:
                        login(request, profile.user)
                        return redirect('/profile/')
                    else:
                        error = True
                        message = f'Введены не корректные данные'
                else:
                    error = True
                    message = f'Исчерпано количество попыток! <a href="{reverse_lazy("home")}">Ещё раз</a>'
            else:
                error = True
                message = f'Время жизни пароля истекло! <a href="{reverse_lazy("home")}">Ещё раз</a>'
        except Exception as err:
            error = True
            message = f'Ошибка регистрации {err}'

    return render(request, 'accounts/otp.html', {'error': error, 'msg': message})


def logout_view(request: WSGIRequest):
    logout(request)
    return redirect('/')
