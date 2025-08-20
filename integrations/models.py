"""
Models for integrations and external service management.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class OTPSession(models.Model):
    """
    OTP session tracking for Crazy Miner integration.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('verified', 'Verified'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
    ]
    
    phone_number = models.CharField(max_length=15)
    otp_code = models.CharField(max_length=10, blank=True)
    otp_id = models.CharField(max_length=100, blank=True, help_text="Crazy Miner OTP ID")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Attempt tracking
    send_attempts = models.IntegerField(default=0)
    verify_attempts = models.IntegerField(default=0)
    max_verify_attempts = models.IntegerField(default=3)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    # Associated user (after verification)
    verified_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='otp_sessions'
    )
    
    # Error tracking
    last_error = models.TextField(blank=True)
    
    class Meta:
        db_table = 'otp_sessions'
        indexes = [
            models.Index(fields=['phone_number', 'status']),
            models.Index(fields=['otp_id']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"OTP Session for {self.phone_number} ({self.status})"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def can_verify(self):
        return (
            self.status in ['sent', 'pending'] and
            not self.is_expired and
            self.verify_attempts < self.max_verify_attempts
        )
    
    def increment_verify_attempt(self):
        """Increment verification attempt counter."""
        self.verify_attempts += 1
        if self.verify_attempts >= self.max_verify_attempts:
            self.status = 'failed'
        self.save()


class ExternalServiceLog(models.Model):
    """
    Log of external service API calls.
    """
    SERVICE_CHOICES = [
        ('crazy_miner', 'Crazy Miner'),
        ('helssa', 'Helssa'),
        ('openai', 'OpenAI/GapGPT'),
    ]
    
    ACTION_CHOICES = [
        ('otp_send', 'OTP Send'),
        ('otp_verify', 'OTP Verify'),
        ('sms_send', 'SMS Send'),
        ('patient_search', 'Patient Search'),
        ('patient_info', 'Patient Info'),
        ('access_verify', 'Access Verify'),
        ('health_check', 'Health Check'),
    ]
    
    service = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    endpoint = models.CharField(max_length=200)
    
    # Request details
    request_data = models.JSONField(default=dict, help_text="Request data (sanitized)")
    request_headers = models.JSONField(default=dict, help_text="Request headers (sanitized)")
    
    # Response details
    response_status = models.IntegerField(null=True, blank=True)
    response_data = models.JSONField(default=dict, help_text="Response data (sanitized)")
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    # Result
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    
    # User context (if available)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='external_service_logs'
    )
    
    class Meta:
        db_table = 'external_service_logs'
        indexes = [
            models.Index(fields=['service', 'action']),
            models.Index(fields=['success', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.service}.{self.action} - {status}"


class PatientAccessSession(models.Model):
    """
    Track patient data access sessions via Helssa.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_access_sessions')
    patient_ref = models.CharField(max_length=100, help_text="Patient reference ID")
    
    # Access details
    access_granted = models.BooleanField(default=False)
    access_level = models.CharField(max_length=20, default='read_only')
    helssa_session_id = models.CharField(max_length=100, blank=True)
    
    # Timing
    requested_at = models.DateTimeField(auto_now_add=True)
    granted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    access_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'patient_access_sessions'
        unique_together = ['user', 'patient_ref']
        indexes = [
            models.Index(fields=['user', 'patient_ref']),
            models.Index(fields=['access_granted', 'expires_at']),
        ]
    
    def __str__(self):
        return f"Access to {self.patient_ref} by {self.user.username}"
    
    @property
    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at
    
    @property
    def is_active(self):
        return self.access_granted and not self.is_expired
    
    def record_access(self):
        """Record a patient data access."""
        self.access_count += 1
        self.last_accessed_at = timezone.now()
        self.save()


class IntegrationHealth(models.Model):
    """
    Health status tracking for external integrations.
    """
    service = models.CharField(max_length=20, unique=True)
    is_healthy = models.BooleanField(default=False)
    last_check_at = models.DateTimeField(auto_now=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    consecutive_failures = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'integration_health'
    
    def __str__(self):
        status = "Healthy" if self.is_healthy else "Unhealthy"
        return f"{self.service} - {status}"
    
    def mark_success(self, response_time_ms: int = None):
        """Mark service as healthy."""
        self.is_healthy = True
        self.last_success_at = timezone.now()
        self.consecutive_failures = 0
        if response_time_ms:
            self.response_time_ms = response_time_ms
        self.save()
    
    def mark_failure(self, error_message: str):
        """Mark service as unhealthy."""
        self.is_healthy = False
        self.last_error = error_message
        self.consecutive_failures += 1
        self.save()
