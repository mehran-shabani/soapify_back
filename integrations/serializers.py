"""
Serializers for integrations app.
"""

from rest_framework import serializers
from .models import OTPSession, PatientAccessSession, ExternalServiceLog, IntegrationHealth


class OTPSessionSerializer(serializers.ModelSerializer):
    is_expired = serializers.ReadOnlyField()
    can_verify = serializers.ReadOnlyField()
    
    class Meta:
        model = OTPSession
        fields = [
            'id', 'phone_number', 'status', 'send_attempts', 'verify_attempts',
            'max_verify_attempts', 'created_at', 'sent_at', 'verified_at',
            'expires_at', 'is_expired', 'can_verify', 'last_error'
        ]
        read_only_fields = [
            'created_at', 'sent_at', 'verified_at', 'send_attempts', 'verify_attempts'
        ]


class PatientAccessSessionSerializer(serializers.ModelSerializer):
    is_expired = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = PatientAccessSession
        fields = [
            'id', 'user', 'user_name', 'patient_ref', 'access_granted',
            'access_level', 'requested_at', 'granted_at', 'expires_at',
            'last_accessed_at', 'access_count', 'is_expired', 'is_active'
        ]
        read_only_fields = [
            'requested_at', 'granted_at', 'last_accessed_at', 'access_count'
        ]


class ExternalServiceLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = ExternalServiceLog
        fields = [
            'id', 'service', 'action', 'endpoint', 'response_status',
            'response_time_ms', 'success', 'error_message', 'created_at',
            'user', 'user_name'
        ]


class IntegrationHealthSerializer(serializers.ModelSerializer):
    status_text = serializers.SerializerMethodField()
    uptime_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = IntegrationHealth
        fields = [
            'service', 'is_healthy', 'status_text', 'last_check_at',
            'last_success_at', 'last_error', 'response_time_ms',
            'consecutive_failures', 'uptime_percentage'
        ]
    
    def get_status_text(self, obj):
        return "Healthy" if obj.is_healthy else "Unhealthy"
    
    def get_uptime_percentage(self, obj):
        # Simple uptime calculation based on consecutive failures
        if obj.consecutive_failures == 0:
            return 100.0
        elif obj.consecutive_failures < 5:
            return 95.0
        elif obj.consecutive_failures < 10:
            return 80.0
        else:
            return 50.0


class OTPSendSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if not value.startswith('+98'):
            raise serializers.ValidationError("Phone number must start with +98")
        
        if len(value) != 13:
            raise serializers.ValidationError("Phone number must be in format +98XXXXXXXXX")
        
        return value


class OTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=10)
    session_id = serializers.IntegerField(required=False)
    
    def validate_otp_code(self, value):
        """Validate OTP code format."""
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        
        if len(value) < 4 or len(value) > 8:
            raise serializers.ValidationError("OTP code must be 4-8 digits")
        
        return value


class PatientSearchSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=100, help_text="Search query")
    limit = serializers.IntegerField(default=20, min_value=1, max_value=50)
    
    def validate_q(self, value):
        """Validate search query."""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Search query must be at least 2 characters")
        
        return value.strip()


class SessionExtensionSerializer(serializers.Serializer):
    additional_minutes = serializers.IntegerField(default=30, min_value=1, max_value=60)
