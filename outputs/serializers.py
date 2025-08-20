"""
Serializers for outputs app.
"""

from rest_framework import serializers
from .models import FinalizedSOAP, OutputFile, PatientLink, DeliveryLog, OutputFormat, PatientInfo


class FinalizedSOAPSerializer(serializers.ModelSerializer):
    patient_ref = serializers.CharField(source='patient_ref', read_only=True)
    encounter_id = serializers.IntegerField(source='soap_draft.encounter.id', read_only=True)
    doctor_name = serializers.CharField(source='soap_draft.encounter.doctor.get_full_name', read_only=True)
    encounter_date = serializers.DateTimeField(source='soap_draft.encounter.created_at', read_only=True)
    draft_completion = serializers.IntegerField(source='soap_draft.completion_percentage', read_only=True)
    
    class Meta:
        model = FinalizedSOAP
        fields = [
            'id', 'status', 'finalized_data', 'markdown_content',
            'pdf_file_path', 'json_file_path', 'finalization_model',
            'finalization_version', 'quality_score', 'created_at',
            'updated_at', 'finalized_at', 'exported_at',
            'patient_ref', 'encounter_id', 'doctor_name',
            'encounter_date', 'draft_completion'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'finalized_at', 'exported_at'
        ]


class OutputFileSerializer(serializers.ModelSerializer):
    file_size_mb = serializers.SerializerMethodField()
    is_presigned_url_valid = serializers.ReadOnlyField()
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = OutputFile
        fields = [
            'id', 'file_type', 'file_path', 'file_size', 'file_size_mb',
            'presigned_url', 'presigned_expires_at', 'is_presigned_url_valid',
            'generated_at', 'generation_time_seconds', 'template_version',
            'download_url'
        ]
    
    def get_file_size_mb(self, obj):
        return obj.get_file_size_mb()
    
    def get_download_url(self, obj):
        """Return valid download URL or None."""
        if obj.is_presigned_url_valid:
            return obj.presigned_url
        return None


class PatientLinkSerializer(serializers.ModelSerializer):
    is_accessible = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    access_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientLink
        fields = [
            'id', 'link_id', 'delivery_method', 'status',
            'expires_at', 'max_views', 'view_count',
            'sent_at', 'first_viewed_at', 'last_viewed_at',
            'created_at', 'is_accessible', 'is_expired', 'access_url'
        ]
        read_only_fields = [
            'link_id', 'view_count', 'sent_at', 'first_viewed_at',
            'last_viewed_at', 'created_at'
        ]
    
    def get_access_url(self, obj):
        """Generate access URL for the link."""
        return obj.generate_access_url()


class OutputFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutputFormat
        fields = ['id', 'name', 'format_type', 'template_name', 'settings', 'is_active', 'created_at']


class PatientInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientInfo
        fields = ['id', 'encounter', 'patient_id', 'patient_name', 'date_of_birth', 'gender', 'additional_info', 'created_at']


class ReportGenerationSerializer(serializers.Serializer):
    soap_draft_id = serializers.IntegerField(required=False)
    format_type = serializers.ChoiceField(choices=['pdf', 'json', 'markdown', 'html', 'docx'])
    include_patient_info = serializers.BooleanField(default=False)

class PatientLinkCreateSerializer(serializers.Serializer):
    delivery_method = serializers.ChoiceField(
        choices=['sms', 'email', 'direct'],
        default='sms'
    )
    patient_phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    patient_email = serializers.EmailField(required=False, allow_blank=True)
    expiry_hours = serializers.IntegerField(default=72, min_value=1, max_value=168)  # 1 hour to 1 week
    
    def validate(self, data):
        """Validate delivery method requirements."""
        delivery_method = data.get('delivery_method')
        patient_phone = data.get('patient_phone', '')
        patient_email = data.get('patient_email', '')
        
        if delivery_method == 'sms' and not patient_phone:
            raise serializers.ValidationError("Patient phone number required for SMS delivery")
        
        if delivery_method == 'email' and not patient_email:
            raise serializers.ValidationError("Patient email required for email delivery")
        
        return data


class DeliveryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryLog
        fields = [
            'id', 'delivery_method', 'recipient', 'status',
            'provider', 'provider_message_id', 'queued_at',
            'sent_at', 'delivered_at', 'error_message',
            'retry_count', 'max_retries'
        ]


class PatientSOAPAccessSerializer(serializers.Serializer):
    """Serializer for patient SOAP access response."""
    patient_ref = serializers.CharField()
    doctor_name = serializers.CharField()
    encounter_date = serializers.DateTimeField()
    soap_data = serializers.JSONField()
    view_count = serializers.IntegerField()
    max_views = serializers.IntegerField()
    expires_at = serializers.DateTimeField()
