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
    phone_number = models.CharField(max_length=15, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


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