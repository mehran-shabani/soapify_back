"""
User accounts and authentication models for SOAPify.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for SOAPify.
    """
    ROLE_CHOICES = [
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='doctor')
    phone_number = models.CharField(max_length=15, blank=True, unique=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class PhoneVerification(models.Model):
    """
    Store phone verification codes.
    """
    phone_number = models.CharField(max_length=15)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    purpose = models.CharField(max_length=20, choices=[
        ('register', 'Registration'),
        ('login', 'Login'),
        ('reset_password', 'Password Reset'),
    ])
    
    class Meta:
        db_table = 'phone_verifications'
        indexes = [
            models.Index(fields=['phone_number', 'code']),
            models.Index(fields=['created_at']),
        ]
    
    def is_valid(self):
        """Check if code is still valid (15 minutes)"""
        from django.utils import timezone
        from datetime import timedelta
        return (not self.is_used and 
                self.created_at >= timezone.now() - timedelta(minutes=15))


class UserSession(models.Model):
    """
    Track user sessions for JWT window management.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['session_token']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Session for {self.user.username}"