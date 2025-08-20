"""
Admin interface for integrations app.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import OTPSession, PatientAccessSession, ExternalServiceLog, IntegrationHealth


@admin.register(OTPSession)
class OTPSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'phone_number', 'status_colored', 'send_attempts',
        'verify_attempts', 'created_at', 'expires_at', 'is_expired'
    ]
    list_filter = ['status', 'created_at', 'verified_at']
    search_fields = ['phone_number', 'otp_id']
    readonly_fields = [
        'created_at', 'sent_at', 'verified_at', 'is_expired', 'can_verify'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('phone_number', 'status', 'otp_id')
        }),
        ('Attempts', {
            'fields': ('send_attempts', 'verify_attempts', 'max_verify_attempts')
        }),
        ('Timing', {
            'fields': ('created_at', 'sent_at', 'verified_at', 'expires_at', 'is_expired', 'can_verify')
        }),
        ('Associated User', {
            'fields': ('verified_user',)
        }),
        ('Error Info', {
            'fields': ('last_error',),
            'classes': ('collapse',)
        }),
    )
    
    def status_colored(self, obj):
        colors = {
            'pending': 'orange',
            'sent': 'blue',
            'verified': 'green',
            'expired': 'red',
            'failed': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'


@admin.register(PatientAccessSession)
class PatientAccessSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'patient_ref', 'access_granted_colored',
        'access_level', 'access_count', 'expires_at', 'is_active'
    ]
    list_filter = ['access_granted', 'access_level', 'requested_at', 'expires_at']
    search_fields = ['user__username', 'patient_ref']
    readonly_fields = [
        'requested_at', 'granted_at', 'last_accessed_at', 'access_count',
        'is_expired', 'is_active'
    ]
    
    def access_granted_colored(self, obj):
        color = 'green' if obj.access_granted else 'red'
        text = 'Granted' if obj.access_granted else 'Denied'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            text
        )
    access_granted_colored.short_description = 'Access'


@admin.register(ExternalServiceLog)
class ExternalServiceLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'service', 'action', 'success_colored',
        'response_time_ms', 'user', 'created_at'
    ]
    list_filter = ['service', 'action', 'success', 'created_at']
    search_fields = ['user__username', 'endpoint', 'error_message']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Request Info', {
            'fields': ('service', 'action', 'endpoint', 'user')
        }),
        ('Response Info', {
            'fields': ('response_status', 'response_time_ms', 'success')
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Data', {
            'fields': ('request_data', 'response_data'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('created_at',)
        }),
    )
    
    def success_colored(self, obj):
        color = 'green' if obj.success else 'red'
        text = 'Success' if obj.success else 'Failed'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            text
        )
    success_colored.short_description = 'Result'


@admin.register(IntegrationHealth)
class IntegrationHealthAdmin(admin.ModelAdmin):
    list_display = [
        'service', 'is_healthy_colored', 'last_check_at',
        'response_time_ms', 'consecutive_failures'
    ]
    list_filter = ['is_healthy', 'last_check_at']
    readonly_fields = ['last_check_at', 'last_success_at']
    
    def is_healthy_colored(self, obj):
        color = 'green' if obj.is_healthy else 'red'
        text = 'Healthy' if obj.is_healthy else 'Unhealthy'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            text
        )
    is_healthy_colored.short_description = 'Health Status'
