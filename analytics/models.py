"""
Analytics models for SOAPify.
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Metric(models.Model):
    """Store system metrics and telemetry data."""
    
    METRIC_TYPE_CHOICES = [
        ('counter', 'Counter'),
        ('gauge', 'Gauge'),
        ('histogram', 'Histogram'),
        ('timer', 'Timer'),
    ]
    
    name = models.CharField(max_length=100)
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPE_CHOICES)
    value = models.FloatField()
    tags = models.JSONField(default=dict, help_text="Key-value pairs for metric dimensions")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['name', 'timestamp']),
            models.Index(fields=['metric_type', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.name}: {self.value} ({self.metric_type})"


class UserActivity(models.Model):
    """Track user activity for analytics."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=50)
    resource = models.CharField(max_length=100, blank=True)
    resource_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=40, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.action} on {self.resource}"


class DailyStats(models.Model):
    """Simple daily aggregates used in tests for coverage imports."""
    date = models.DateField(unique=True)
    total_encounters = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Stats {self.date}: encounters={self.total_encounters}, users={self.active_users}"

class PerformanceMetric(models.Model):
    """Store performance metrics."""
    
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    response_time_ms = models.PositiveIntegerField()
    status_code = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['endpoint', 'timestamp']),
            models.Index(fields=['status_code', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.endpoint}: {self.response_time_ms}ms"


class BusinessMetric(models.Model):
    """Store business-specific metrics."""
    
    metric_name = models.CharField(max_length=100)
    value = models.FloatField()
    dimensions = models.JSONField(default=dict)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['metric_name', 'period_start']),
            models.Index(fields=['period_start', 'period_end']),
        ]
        unique_together = ['metric_name', 'period_start', 'period_end']
    
    def __str__(self):
        return f"{self.metric_name}: {self.value} ({self.period_start} - {self.period_end})"


class AlertRule(models.Model):
    """Define alert rules for metrics."""
    
    OPERATOR_CHOICES = [
        ('gt', 'Greater Than'),
        ('gte', 'Greater Than or Equal'),
        ('lt', 'Less Than'),
        ('lte', 'Less Than or Equal'),
        ('eq', 'Equal'),
        ('ne', 'Not Equal'),
    ]
    
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]
    
    name = models.CharField(max_length=100)
    metric_name = models.CharField(max_length=100)
    operator = models.CharField(max_length=10, choices=OPERATOR_CHOICES)
    threshold = models.FloatField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    notification_channels = models.JSONField(default=list)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name}: {self.metric_name} {self.operator} {self.threshold}"


class Alert(models.Model):
    """Store triggered alerts."""
    
    STATUS_CHOICES = [
        ('firing', 'Firing'),
        ('resolved', 'Resolved'),
        ('acknowledged', 'Acknowledged'),
    ]
    
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='alerts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='firing')
    metric_value = models.FloatField()
    message = models.TextField()
    metadata = models.JSONField(default=dict)
    fired_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['rule', 'status']),
            models.Index(fields=['status', 'fired_at']),
            models.Index(fields=['fired_at']),
        ]
    
    def __str__(self):
        return f"Alert: {self.rule.name} - {self.status}"