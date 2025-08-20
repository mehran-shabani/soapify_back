"""
Admin Plus models for SOAPify.
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class SystemHealth(models.Model):
    """System health monitoring."""
    
    component = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=[
        ('healthy', 'Healthy'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('down', 'Down')
    ])
    message = models.TextField()
    metrics = models.JSONField(default=dict)
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['component', 'status']),
            models.Index(fields=['checked_at']),
        ]
    
    def __str__(self):
        return f"{self.component}: {self.status}"


class TaskMonitor(models.Model):
    """Monitor Celery task execution."""
    
    task_id = models.CharField(max_length=255, unique=True)
    task_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('started', 'Started'),
        ('retry', 'Retry'),
        ('failure', 'Failure'),
        ('success', 'Success')
    ])
    args = models.JSONField(default=list)
    kwargs = models.JSONField(default=dict)
    result = models.JSONField(null=True, blank=True)
    traceback = models.TextField(blank=True)
    runtime = models.FloatField(null=True, blank=True)
    retries = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task_name', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.task_name} ({self.task_id[:8]}...): {self.status}"


class OperationLog(models.Model):
    """Log administrative operations."""
    
    ACTION_CHOICES = [
        ('task_retry', 'Task Retry'),
        ('task_cancel', 'Task Cancel'),
        ('system_maintenance', 'System Maintenance'),
        ('data_export', 'Data Export'),
        ('user_action', 'User Action'),
        ('system_config', 'System Configuration'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    target_object = models.CharField(max_length=100, blank=True)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.action} - {self.description[:50]}"