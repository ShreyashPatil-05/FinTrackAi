"""
Accounts app - URL Configuration
"""
from django.urls import path
from . import views


urlpatterns = [
    path('register/',        views.register_view,       name='register'),
    path('login/',           views.login_view,           name='login'),
    path('logout/',          views.logout_view,          name='logout'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('verify/<uuid:token>/', views.verify_email,     name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('verify-pending/',  views.verify_pending,       name='verify_pending'),
]
