"""
URL patterns for accounts app.
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('users/', views.UserListCreateView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', views.UserRetrieveUpdateView.as_view(), name='user-detail'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
]