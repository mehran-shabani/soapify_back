from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class PaymentTransaction(models.Model):
    """Model to track payment transactions"""
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='IRR')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # External payment gateway fields
    gateway_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_reference_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_tracking_code = models.CharField(max_length=255, blank=True, null=True)
    
    # Metadata
    description = models.TextField(blank=True)
    callback_url = models.URLField(blank=True)
    redirect_url = models.URLField(blank=True)
    
    # Encrypted data storage
    encrypted_data = models.TextField(blank=True, help_text="Stores encrypted sensitive data")
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['gateway_transaction_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.id} - {self.user} - {self.amount} {self.currency} - {self.status}"
    
    def mark_completed(self):
        """Mark transaction as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self):
        """Mark transaction as failed"""
        self.status = 'failed'
        self.save()


class PaymentLog(models.Model):
    """Model to log all payment-related activities"""
    
    LOG_TYPE_CHOICES = [
        ('request', 'Payment Request'),
        ('callback', 'Gateway Callback'),
        ('verification', 'Payment Verification'),
        ('error', 'Error'),
        ('info', 'Information'),
    ]
    
    transaction = models.ForeignKey(
        PaymentTransaction, 
        on_delete=models.CASCADE, 
        related_name='logs'
    )
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES)
    message = models.TextField()
    raw_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.log_type} - {self.transaction.id} - {self.created_at}"