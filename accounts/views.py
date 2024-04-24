import datetime
import random

from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.handlers.wsgi import WSGIRequest
from django.forms import model_to_dict
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.authentication import SessionAuthentication

from accounts.forms import ProfileUserForm
from accounts.serializers import OTPSerializer, LoginUserSerializer, ProfileOutUserSerializer, ProfileInUserSerializer
from accounts.utils import OtpSender
from accounts.models import Profile
from config import settings


def get_invite_code(user) -> str:
    return Profile.objects.get(user=user).invite


def get_invited(user) -> str:
    return Profile.objects.get(user=user).invited


def get_all_followers(invite_code) -> list:
    return list(Profile.objects.filter(invited=invite_code).all().values('user__phone'))


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return None


class MyApiView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def get_success_headers(self, data):
        try:
            return {'Location': str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            return {}


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
                    profile = Profile.objects.create(user=user, invited=invited)
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

    def get_context_data(self, **kwargs):
        context = super(ProfileUser, self).get_context_data(**kwargs)
        context['invite'] = get_invite_code(self.request.user)
        context['followers'] = get_all_followers(context['invite'])
        return context

    def get_initial(self):
        initial = super(ProfileUser, self).get_initial()
        initial['invited'] = get_invited(self.request.user)
        return initial

    def get_success_url(self):
        return reverse_lazy('profile', args=[self.request.user.pk])

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        user = form.save()
        invited_code = form.data.get('invited')
        if invited_code:
            profile = Profile.objects.get(user=user)
            profile.invited = invited_code
            profile.save()
        return redirect('profile')


def otp_request(request: WSGIRequest, phone):
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


# ============== API handlers =================


class LoginOTPAPIView(MyApiView):
    serializer_class = OTPSerializer
    queryset = Profile.objects.all()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = self.queryset.get(user=get_user_model().objects.get(phone=kwargs.get('phone')))
        profile.otpattempts -= 1
        timedelta = datetime.datetime.utcnow() - profile.otptime.replace(tzinfo=None)
        try:
            profile.save()
            if timedelta.seconds < settings.OTP_LIFETIME:
                if profile.otpattempts > 0:
                    if int(request.data.get('otp')) == profile.otp:
                        login(self.request, user=profile.user)
                    else:
                        return Response({'detail': 'Не корректный пароль!'},
                                        status=status.HTTP_401_UNAUTHORIZED)
                else:
                    return Response({'detail': 'Исчерпано количество попыток!'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            else:
                return Response({'detail': 'Время жизни пароля истекло!'}, status=status.HTTP_408_REQUEST_TIMEOUT)
        except Exception as err:
            return Response({'detail': f'Ошибка регистрации {err}'}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response({'detail': 'login successful'}, status=status.HTTP_200_OK, headers=headers)


class LoginOrCreateAPIView(MyApiView):
    serializer_class = LoginUserSerializer
    queryset = Profile.objects.all()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.data.get('phone')
        user = get_user_model().objects.filter(phone=phone).first()
        profile = Profile.objects.filter(user=user).first()
        if not profile:
            try:
                user = get_user_model().objects.create(phone=phone)
                profile = Profile.objects.create(user=user)
            except Exception as err:
                return Response({'detail': f'Ошибка регистрации {err}'}, status=status.HTTP_400_BAD_REQUEST)
        if last_otp_time := profile.otptime:
            timedelta = datetime.datetime.utcnow() - last_otp_time.replace(tzinfo=None)
        else:
            timedelta = datetime.timedelta(seconds=settings.OTP_RETRY_TIMEOUT+1)
        if not last_otp_time or timedelta.seconds > settings.OTP_RETRY_TIMEOUT:
            profile.otp = random.randint(999, 9999)
            profile.otptime = datetime.datetime.utcnow()
            profile.otpattempts = settings.OTP_ATTEMPTS
            profile.save()
            sender = OtpSender(user.phone, profile.otp).send_otp_on_phone()

        else:
            return Response({'detail': 'Превышено время повторной выдачи пароля. Попробуйте позже!'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)
        headers = self.get_success_headers(serializer.data)

        return Response({'detail': f'your OTP is {profile.otp}',
                         'login_url': f'{reverse_lazy("OTPLogin", args=[phone])}'},
                        status=status.HTTP_200_OK, headers=headers)


class ProfileAPIUpdate(MyApiView):
    queryset = get_user_model()
    serializer_class = ProfileInUserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.data.get('phone')
        user = get_user_model().objects.filter(phone=phone).first()
        profile = Profile.objects.filter(user=user).first()
        if profile:
            invite = get_invite_code(user)
            followers = [flw.get('user__phone') for flw in get_all_followers(invite)]
        else:
            return Response({'detail': 'Пользователь не найден!'},
                            status=status.HTTP_404_NOT_FOUND)
        headers = self.get_success_headers(serializer.data)
        merged_data = model_to_dict(user) | model_to_dict(profile) | {'phone': str(user), 'followers': followers}
        out_serializer = ProfileOutUserSerializer(data=merged_data)
        if out_serializer.is_valid(raise_exception=False):
            return Response(out_serializer.validated_data,
                        status=status.HTTP_200_OK, headers=headers)
        else:
            return Response({'detail': 'Ошибка записи в базе'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR, headers=headers)

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.data.get('phone')
        invited = serializer.data.get('invited')
        user = get_user_model().objects.filter(phone=phone).first()
        profile = Profile.objects.filter(user=user).first()
        valid_invite = Profile.objects.filter(invite=invited)
        if not profile:  # если профиля с таким номером нет, то проверяем приглашение
            if valid_invite or not invited:  # если приглашение корректное или его нет
                try:
                    user = get_user_model().objects.create(phone=phone)
                    profile = Profile.objects.create(user=user, invited=invited)
                except Exception as err:
                    return Response({'detail': f'Ошибка внесения пользователя в систему {err}'},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({'detail': 'Этот пригласительный код не существует!'},
                                status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'detail': 'Телефон уже зарегистрирован!'},
                            status=status.HTTP_409_CONFLICT)

        headers = self.get_success_headers(serializer.data)
        merged_data = model_to_dict(user) | model_to_dict(profile) | {'phone': str(user), 'followers': []}
        out_serializer = ProfileOutUserSerializer(data=merged_data)
        if out_serializer.is_valid(raise_exception=False):
            return Response(out_serializer.validated_data,
                        status=status.HTTP_200_OK, headers=headers)
        else:
            return Response({'detail': 'Ошибка записи в базе'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR, headers=headers)

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.data.get('phone')
        new_invited = serializer.data.get('invited')
        new_email = serializer.data.get('email')
        new_first_name = serializer.data.get('first_name')
        new_last_name = serializer.data.get('last_name')
        user = get_user_model().objects.filter(phone=phone).first()
        profile = Profile.objects.filter(user=user).first()
        valid_invite = Profile.objects.filter(invite=new_invited)
        if new_invited or new_email or new_first_name or new_last_name:
            if profile:
                if str(new_invited) == str(profile.invite):
                    return Response({'detail': f'Нельзя пригласить самого себя!'},
                             status=status.HTTP_409_CONFLICT)
                if valid_invite or not new_invited:  # если приглашение корректное или его нет
                    try:
                        if new_email: user.email = new_email
                        if new_first_name: user.first_name = new_first_name
                        if new_last_name: user.last_name = new_last_name
                        if new_invited and not profile.invited: profile.invited = new_invited
                        user.save()
                        profile.save()
                    except Exception as err:
                        return Response({'detail': f'Ошибка изменения пользователя в системе {err}'},
                                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    return Response({'detail': 'Этот пригласительный код не существует!'},
                                    status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'detail': 'Такого пользователя не существует!'},
                                status=status.HTTP_404_NOT_FOUND)

        followers = [flw.get('user__phone') for flw in get_all_followers(profile.invite)]
        headers = self.get_success_headers(serializer.data)
        merged_data = model_to_dict(user) | model_to_dict(profile) | {'phone': str(user), 'followers': followers}
        out_serializer = ProfileOutUserSerializer(data=merged_data)
        if out_serializer.is_valid(raise_exception=False):
            return Response(out_serializer.validated_data,
                        status=status.HTTP_200_OK, headers=headers)
        else:
            return Response({'detail': 'Ошибка записи в базе'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR, headers=headers)
