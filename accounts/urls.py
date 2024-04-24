from django.urls import path

from accounts import views


urlpatterns = [
    path('login/', views.LoginOrCreateAPIView.as_view()),
    path('login/<int:phone>/', views.LoginOTPAPIView.as_view(), name='OTPLogin'),
    path('profile/', views.ProfileAPIUpdate.as_view()),
]
