"""
URL patterns for accounts app.
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints (no token required)
    path('auth/send-code/', views.send_verification_code, name='send-code'),
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/login-phone/', views.login_with_phone, name='login-phone'),
    path('auth/refresh/', views.refresh_token, name='refresh-token'),
    path('auth/reset-password/', views.reset_password, name='reset-password'),
    
    # Protected endpoints (token required)
    path('auth/current-user/', views.current_user, name='current-user'),
    path('auth/logout/', views.logout, name='logout'),
]