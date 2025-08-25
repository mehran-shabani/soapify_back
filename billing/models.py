"""
Billing models for SOAPify - Wallet, Subscription, and Transaction management.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from datetime import timedelta

User = get_user_model()


class Wallet(models.Model):
    """
    User wallet for managing credits and balance.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current wallet balance"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'billing_wallets'
        
    def __str__(self):
        return f"{self.user.username}'s Wallet: {self.balance}"
    
    def has_sufficient_balance(self, amount):
        """Check if wallet has sufficient balance for a transaction."""
        return self.balance >= Decimal(str(amount))
    
    def deduct(self, amount, description="Service charge"):
        """
        Deduct amount from wallet balance.
        Returns the transaction object.
        """
        amount = Decimal(str(amount))
        if not self.has_sufficient_balance(amount):
            raise ValidationError(f"Insufficient balance. Current balance: {self.balance}")
        
        with transaction.atomic():
            self.balance -= amount
            self.save()
            
            # Create transaction record
            trans = Transaction.objects.create(
                user=self.user,
                amount=-amount,  # Negative for deduction
                transaction_type='debit',
                description=description,
                balance_after=self.balance,
                status='completed'
            )
            return trans
    
    def add_credit(self, amount, description="Credit added"):
        """
        Add credit to wallet balance.
        Returns the transaction object.
        """
        amount = Decimal(str(amount))
        
        with transaction.atomic():
            self.balance += amount
            self.save()
            
            # Create transaction record
            trans = Transaction.objects.create(
                user=self.user,
                amount=amount,
                transaction_type='credit',
                description=description,
                balance_after=self.balance,
                status='completed'
            )
            return trans
    
    def get_balance(self):
        """Get current wallet balance."""
        return self.balance


class SubscriptionPlan(models.Model):
    """
    Available subscription plans.
    """
    PLAN_TYPE_CHOICES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    
    BILLING_PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_period = models.CharField(max_length=20, choices=BILLING_PERIOD_CHOICES)
    
    # Features
    max_encounters_per_month = models.IntegerField(default=10)
    max_stt_minutes_per_month = models.IntegerField(default=60)
    max_ai_requests_per_month = models.IntegerField(default=100)
    includes_pdf_export = models.BooleanField(default=False)
    includes_api_access = models.BooleanField(default=False)
    includes_priority_support = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'billing_subscription_plans'
        ordering = ['price']
        
    def __str__(self):
        return f"{self.name} ({self.get_billing_period_display()})"
    
    def get_duration_days(self):
        """Get subscription duration in days."""
        if self.billing_period == 'monthly':
            return 30
        elif self.billing_period == 'quarterly':
            return 90
        elif self.billing_period == 'yearly':
            return 365
        return 30


class Subscription(models.Model):
    """
    User subscription management.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Dates
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    encounters_used = models.IntegerField(default=0)
    stt_minutes_used = models.IntegerField(default=0)
    ai_requests_used = models.IntegerField(default=0)
    
    # Payment
    auto_renew = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'billing_subscriptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['expires_at']),
        ]
        
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"
    
    def activate(self):
        """Activate subscription."""
        self.status = 'active'
        self.started_at = timezone.now()
        self.expires_at = self.started_at + timedelta(days=self.plan.get_duration_days())
        self.save()
    
    def cancel(self):
        """Cancel subscription."""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.auto_renew = False
        self.save()
    
    def is_valid(self):
        """Check if subscription is currently valid."""
        return (
            self.status == 'active' and
            self.expires_at and
            self.expires_at > timezone.now()
        )
    
    def can_use_encounter(self):
        """Check if user can create new encounter."""
        return self.is_valid() and self.encounters_used < self.plan.max_encounters_per_month
    
    def can_use_stt(self, minutes):
        """Check if user can use STT for given minutes."""
        return self.is_valid() and (self.stt_minutes_used + minutes) <= self.plan.max_stt_minutes_per_month
    
    def can_use_ai(self):
        """Check if user can make AI request."""
        return self.is_valid() and self.ai_requests_used < self.plan.max_ai_requests_per_month
    
    def reset_monthly_usage(self):
        """Reset monthly usage counters."""
        self.encounters_used = 0
        self.stt_minutes_used = 0
        self.ai_requests_used = 0
        self.save()


class Transaction(models.Model):
    """
    Financial transaction records.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('subscription', 'Subscription Payment'),
        ('refund', 'Refund'),
        ('bonus', 'Bonus'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Positive for credit, negative for debit"
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Details
    description = models.CharField(max_length=255)
    reference_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Related objects
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    
    # Balance tracking
    balance_before = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'billing_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['reference_id']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.get_status_display()}"
    
    def complete(self):
        """Mark transaction as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def fail(self, reason=""):
        """Mark transaction as failed."""
        self.status = 'failed'
        if reason:
            self.gateway_response['failure_reason'] = reason
        self.save()


class UsageLog(models.Model):
    """
    Track usage of various features for billing purposes.
    """
    FEATURE_CHOICES = [
        ('encounter', 'Encounter Creation'),
        ('stt', 'Speech to Text'),
        ('ai_request', 'AI Request'),
        ('pdf_export', 'PDF Export'),
        ('api_call', 'API Call'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usage_logs'
    )
    feature = models.CharField(max_length=20, choices=FEATURE_CHOICES)
    quantity = models.IntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'billing_usage_logs'
        indexes = [
            models.Index(fields=['user', 'feature', 'created_at']),
            models.Index(fields=['subscription', 'created_at']),
        ]
        
    def __str__(self):
        return f"{self.user.username} - {self.feature} ({self.quantity})"