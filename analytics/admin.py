"""
Admin configuration for analytics app.
"""
from django.contrib import admin
from .models import Metric, UserActivity, PerformanceMetric, BusinessMetric, AlertRule, Alert


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    """Admin interface for Metric."""
    
    list_display = ['name', 'metric_type', 'value', 'timestamp']
    list_filter = ['metric_type', 'name', 'timestamp']
    search_fields = ['name']
    ordering = ['-timestamp']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'metric_type', 'value')
        }),
        ('Tags', {
            'fields': ('tags',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['timestamp']
    
    def get_queryset(self, request):
        """Limit to recent metrics for performance."""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=7)
        return super().get_queryset(request).filter(timestamp__gte=cutoff_date)


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Admin interface for UserActivity."""
    
    list_display = ['user', 'action', 'resource', 'resource_id', 'timestamp']
    list_filter = ['action', 'resource', 'timestamp']
    search_fields = ['user__username', 'action', 'resource']
    ordering = ['-timestamp']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'action', 'resource', 'resource_id')
        }),
        ('Session Info', {
            'fields': ('session_id', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'timestamp'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['timestamp']
    
    def get_queryset(self, request):
        """Optimize queryset and limit to recent activities."""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=30)
        return super().get_queryset(request).select_related('user').filter(timestamp__gte=cutoff_date)


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    """Admin interface for PerformanceMetric."""
    
    list_display = ['endpoint', 'method', 'status_code', 'response_time_ms', 'user', 'timestamp']
    list_filter = ['method', 'status_code', 'timestamp']
    search_fields = ['endpoint', 'user__username']
    ordering = ['-timestamp']
    
    fieldsets = (
        (None, {
            'fields': ('endpoint', 'method', 'status_code', 'response_time_ms', 'user')
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'timestamp'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['timestamp']
    
    def get_queryset(self, request):
        """Optimize queryset and limit to recent metrics."""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=7)
        return super().get_queryset(request).select_related('user').filter(timestamp__gte=cutoff_date)


@admin.register(BusinessMetric)
class BusinessMetricAdmin(admin.ModelAdmin):
    """Admin interface for BusinessMetric."""
    
    list_display = ['metric_name', 'value', 'period_start', 'period_end', 'created_at']
    list_filter = ['metric_name', 'period_start']
    search_fields = ['metric_name']
    ordering = ['-period_start']
    
    fieldsets = (
        (None, {
            'fields': ('metric_name', 'value')
        }),
        ('Period', {
            'fields': ('period_start', 'period_end')
        }),
        ('Dimensions', {
            'fields': ('dimensions',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at']


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    """Admin interface for AlertRule."""
    
    list_display = ['name', 'metric_name', 'operator', 'threshold', 'severity', 'is_active', 'created_at']
    list_filter = ['severity', 'operator', 'is_active', 'created_at']
    search_fields = ['name', 'metric_name', 'description']
    ordering = ['name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Rule Configuration', {
            'fields': ('metric_name', 'operator', 'threshold', 'severity')
        }),
        ('Notifications', {
            'fields': ('notification_channels',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        """Set created_by field when saving."""
        if not change:  # Only set on create
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['activate_rules', 'deactivate_rules']
    
    def activate_rules(self, request, queryset):
        """Activate selected alert rules."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} alert rules.")
    activate_rules.short_description = "Activate selected rules"
    
    def deactivate_rules(self, request, queryset):
        """Deactivate selected alert rules."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} alert rules.")
    deactivate_rules.short_description = "Deactivate selected rules"


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """Admin interface for Alert."""
    
    list_display = ['rule', 'status', 'metric_value', 'severity', 'fired_at', 'acknowledged_by']
    list_filter = ['status', 'rule__severity', 'fired_at']
    search_fields = ['rule__name', 'message']
    ordering = ['-fired_at']
    
    fieldsets = (
        (None, {
            'fields': ('rule', 'status', 'metric_value', 'message')
        }),
        ('Timeline', {
            'fields': ('fired_at', 'resolved_at', 'acknowledged_by', 'acknowledged_at')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['fired_at']
    
    def severity(self, obj):
        """Get severity from rule."""
        return obj.rule.severity
    severity.short_description = 'Severity'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('rule', 'acknowledged_by')
    
    actions = ['acknowledge_alerts', 'resolve_alerts']
    
    def acknowledge_alerts(self, request, queryset):
        """Acknowledge selected alerts."""
        from django.utils import timezone
        updated = queryset.filter(status='firing').update(
            status='acknowledged',
            acknowledged_by=request.user,
            acknowledged_at=timezone.now()
        )
        self.message_user(request, f"Acknowledged {updated} alerts.")
    acknowledge_alerts.short_description = "Acknowledge selected alerts"
    
    def resolve_alerts(self, request, queryset):
        """Resolve selected alerts."""
        from django.utils import timezone
        updated = queryset.filter(status__in=['firing', 'acknowledged']).update(
            status='resolved',
            resolved_at=timezone.now()
        )
        self.message_user(request, f"Resolved {updated} alerts.")
    resolve_alerts.short_description = "Resolve selected alerts"