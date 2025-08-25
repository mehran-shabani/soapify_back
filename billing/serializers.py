"""
Serializers for billing app.
"""

from rest_framework import serializers
from .models import Wallet, SubscriptionPlan, Subscription, Transaction, UsageLog


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for wallet."""
    
    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'created_at', 'updated_at']
        read_only_fields = ['balance', 'created_at', 'updated_at']


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans."""
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'plan_type', 'price', 'billing_period',
            'max_encounters_per_month', 'max_stt_minutes_per_month',
            'max_ai_requests_per_month', 'includes_pdf_export',
            'includes_api_access', 'includes_priority_support'
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for subscriptions."""
    
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        source='plan',
        write_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'plan_id', 'status', 'started_at', 'expires_at',
            'encounters_used', 'stt_minutes_used', 'ai_requests_used',
            'auto_renew', 'is_valid', 'created_at'
        ]
        read_only_fields = [
            'status', 'started_at', 'expires_at', 'encounters_used',
            'stt_minutes_used', 'ai_requests_used', 'created_at'
        ]


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transactions."""
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'amount', 'transaction_type', 'status', 'description',
            'reference_id', 'balance_after', 'created_at', 'completed_at'
        ]
        read_only_fields = [
            'status', 'balance_after', 'created_at', 'completed_at'
        ]


class AddCreditSerializer(serializers.Serializer):
    """Serializer for adding credit to wallet."""
    
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1000)
    gateway = serializers.ChoiceField(choices=['zarinpal', 'idpay', 'nextpay'])
    
    def validate_amount(self, value):
        # Minimum 1000 Toman
        if value < 1000:
            raise serializers.ValidationError("Minimum amount is 1000 Toman")
        return value


class UsageLogSerializer(serializers.ModelSerializer):
    """Serializer for usage logs."""
    
    class Meta:
        model = UsageLog
        fields = ['id', 'feature', 'quantity', 'metadata', 'created_at']
        read_only_fields = ['created_at']