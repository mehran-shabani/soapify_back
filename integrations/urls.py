"""
URL patterns for integrations app.
"""

from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    # OTP Authentication
    path('otp/send/', views.send_otp, name='send_otp'),
    path('otp/verify/', views.verify_otp, name='verify_otp'),
    
    # Session Management
    path('session/extend/', views.extend_session, name='extend_session'),
    path('session/status/', views.get_session_status, name='get_session_status'),
    path('logout/', views.logout, name='logout'),
    
    # Patient Data Access (Helssa)
    path('patients/search/', views.search_patients, name='search_patients'),
    path('patients/<str:patient_ref>/access/', views.request_patient_access, name='request_patient_access'),
    path('patients/<str:patient_ref>/info/', views.get_patient_info, name='get_patient_info'),
    
    # Health Monitoring
    path('health/', views.integration_health, name='integration_health'),
]
