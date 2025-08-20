"""
Serializers برای دسترسی به اطلاعات بیماران
"""
from rest_framework import serializers
from .patient_access_models import PatientAccessRequest, PatientDataCache


class RequestPatientAccessSerializer(serializers.Serializer):
    """درخواست دسترسی به بیمار"""
    patient_phone = serializers.CharField(max_length=15)
    
    def validate_patient_phone(self, value):
        # اعتبارسنجی شماره موبایل ایران
        if not value.startswith('09') or len(value) != 11:
            raise serializers.ValidationError("شماره موبایل باید با 09 شروع شود و 11 رقم باشد")
        return value


class VerifyAccessSerializer(serializers.Serializer):
    """تایید دسترسی با OTP"""
    request_id = serializers.UUIDField()
    otp_code = serializers.CharField(max_length=6, min_length=6)
    
    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("کد تایید باید فقط شامل اعداد باشد")
        return value


class PatientAccessSerializer(serializers.ModelSerializer):
    """نمایش اطلاعات درخواست دسترسی"""
    doctor_name = serializers.CharField(source='doctor.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PatientAccessRequest
        fields = [
            'id', 'doctor', 'doctor_name', 'patient_phone',
            'status', 'status_display', 'verified_at',
            'access_expires_at', 'created_at'
        ]
        read_only_fields = ['id', 'doctor', 'verified_at', 'created_at']


class PatientDataSerializer(serializers.Serializer):
    """نمایش اطلاعات بیمار"""
    patient_phone = serializers.CharField()
    patient_name = serializers.CharField(required=False)
    latest_summary = serializers.JSONField(required=False)
    summary_date = serializers.DateTimeField(required=False)
    has_summary = serializers.BooleanField(default=False)
    from_cache = serializers.BooleanField(default=False)


class CreateSOAPifyPaymentSerializer(serializers.Serializer):
    """ایجاد پرداخت برای کاربران SOAPify"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=0)
    soapify_user_id = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default="پرداخت برای SOAPify")
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("مبلغ باید بیشتر از صفر باشد")
        if value < 10000:
            raise serializers.ValidationError("حداقل مبلغ پرداخت 10,000 ریال است")
        return value