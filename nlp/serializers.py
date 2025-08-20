"""
Serializers for NLP app.
"""

from rest_framework import serializers
from .models import SOAPDraft, ChecklistItem, ExtractionLog, SOAPSection, ExtractionTask


class SOAPDraftSerializer(serializers.ModelSerializer):
    completion_percentage = serializers.ReadOnlyField()
    doctor_name = serializers.CharField(source='encounter.doctor.get_full_name', read_only=True)
    patient_ref = serializers.CharField(source='encounter.patient_ref', read_only=True)
    encounter_date = serializers.DateTimeField(source='encounter.created_at', read_only=True)
    version = serializers.ReadOnlyField()
    
    class Meta:
        model = SOAPDraft
        fields = [
            'id', 'encounter', 'status', 'soap_data', 'confidence_score',
            'extraction_version', 'created_at', 'updated_at', 'reviewed_at',
            'completion_percentage', 'doctor_name', 'patient_ref', 'encounter_date', 'version'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ChecklistItemSerializer(serializers.ModelSerializer):
    is_critical = serializers.ReadOnlyField()
    completion_score = serializers.ReadOnlyField()
    
    class Meta:
        model = ChecklistItem
        fields = [
            'id', 'item_id', 'section', 'title', 'description',
            'item_type', 'status', 'weight', 'confidence', 'notes',
            'created_at', 'updated_at', 'is_critical', 'completion_score'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ChecklistItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistItem
        fields = ['status', 'notes']
        
    def validate_status(self, value):
        """Validate checklist item status."""
        valid_statuses = ['missing', 'partial', 'complete', 'not_applicable']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        return value


class SOAPSectionUpdateSerializer(serializers.Serializer):
    section = serializers.ChoiceField(
        choices=['subjective', 'objective', 'assessment', 'plan']
    )
    field = serializers.CharField(max_length=100)
    value = serializers.JSONField()
    
    def validate_section(self, value):
        """Validate SOAP section."""
        valid_sections = ['subjective', 'objective', 'assessment', 'plan']
        if value not in valid_sections:
            raise serializers.ValidationError(f"Invalid section. Must be one of: {valid_sections}")
        return value


class SOAPSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SOAPSection
        fields = ['id', 'soap_draft', 'section_type', 'content', 'metadata', 'created_at', 'updated_at']


class ExtractionTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractionTask
        fields = ['id', 'encounter', 'task_type', 'status', 'result', 'created_at', 'completed_at']


class SOAPGenerateSerializer(serializers.Serializer):
    soap_draft_id = serializers.IntegerField(required=False)
    encounter_id = serializers.IntegerField(required=False)
    regenerate_sections = serializers.ListField(child=serializers.ChoiceField(choices=['subjective', 'objective', 'assessment', 'plan']), required=False)


class ExtractionLogSerializer(serializers.ModelSerializer):
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = ExtractionLog
        fields = [
            'id', 'model_used', 'prompt_version', 'input_text_length',
            'output_json_length', 'processing_time_seconds', 'duration_formatted',
            'tokens_used', 'success', 'error_message', 'created_at'
        ]
    
    def get_duration_formatted(self, obj):
        """Format processing time in a readable way."""
        if obj.processing_time_seconds:
            if obj.processing_time_seconds < 60:
                return f"{obj.processing_time_seconds:.1f}s"
            else:
                minutes = int(obj.processing_time_seconds // 60)
                seconds = int(obj.processing_time_seconds % 60)
                return f"{minutes}m {seconds}s"
        return None


class SOAPValidationSerializer(serializers.Serializer):
    """Serializer for SOAP validation results."""
    overall_completion = serializers.IntegerField()
    section_completeness = serializers.JSONField()
    suggestions = serializers.ListField()
    critical_missing_count = serializers.IntegerField()
