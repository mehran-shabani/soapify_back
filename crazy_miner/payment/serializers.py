from rest_framework import serializers
from .models import PaymentTransaction, PaymentLog


class CreatePaymentSerializer(serializers.Serializer):
    """Serializer for creating payment requests"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)
    callback_url = serializers.URLField(required=False, allow_blank=True)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value


class PaymentCallbackSerializer(serializers.Serializer):
    """Serializer for payment gateway callbacks"""
    trans_id = serializers.CharField()
    id_get = serializers.CharField()
    
    # Optional fields that might come from gateway
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    status = serializers.CharField(required=False)
    tracking_code = serializers.CharField(required=False)


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for PaymentTransaction model"""
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'user', 'user_phone', 'amount', 'currency', 'status',
            'gateway_transaction_id', 'gateway_reference_id', 'gateway_tracking_code',
            'description', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'gateway_transaction_id', 
            'gateway_reference_id', 'gateway_tracking_code',
            'created_at', 'updated_at', 'completed_at'
        ]


class PaymentStatusSerializer(serializers.Serializer):
    """Serializer for payment status response"""
    transaction_id = serializers.UUIDField()
    status = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    gateway_tracking_code = serializers.CharField(required=False)
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(required=False)
    payment_url = serializers.URLField(required=False)


class PaymentLogSerializer(serializers.ModelSerializer):
    """Serializer for PaymentLog model"""
    
    class Meta:
        model = PaymentLog
        fields = ['id', 'transaction', 'log_type', 'message', 'raw_data', 'created_at']
        read_only_fields = ['id', 'created_at']