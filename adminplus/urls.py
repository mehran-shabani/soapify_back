"""
URL configuration for adminplus app.
"""
from django.urls import path
from . import views

app_name = 'adminplus'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # API endpoints
    path('api/health/', views.system_health, name='system_health'),
    path('api/tasks/', views.task_monitor, name='task_monitor'),
    path('api/tasks/retry/', views.retry_task, name='retry_task'),
    path('api/tasks/cancel/', views.cancel_task, name='cancel_task'),
    path('api/tasks/stats/', views.task_statistics, name='task_statistics'),
    path('api/logs/', views.operation_logs, name='operation_logs'),
    path('api/export/', views.export_data, name='export_data'),
]