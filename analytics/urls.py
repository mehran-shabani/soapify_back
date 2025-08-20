"""
URL configuration for analytics app.
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Overview and dashboards
    path('overview/', views.system_overview, name='system_overview'),
    path('users/', views.user_analytics, name='user_analytics'),
    path('performance/', views.performance_analytics, name='performance_analytics'),
    
    # Business metrics
    path('business-metrics/', views.calculate_business_metrics, name='calculate_business_metrics'),
    
    # Data collection
    path('activity/', views.record_activity, name='record_activity'),
    path('metric/', views.record_metric, name='record_metric'),
    
    # Alerts
    path('alerts/', views.alerts, name='alerts'),
    path('alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('alerts/check/', views.check_alert_rules, name='check_alert_rules'),
]