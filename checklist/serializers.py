"""
Checklist serializers for SOAPify.
"""
from rest_framework import serializers
from .models import ChecklistCatalog, ChecklistEval, ChecklistTemplate


class ChecklistCatalogSerializer(serializers.ModelSerializer):
    """Serializer for ChecklistCatalog model."""
    
    class Meta:
        model = ChecklistCatalog
        fields = [
            'id', 'title', 'description', 'category', 'priority',
            'keywords', 'question_template', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ChecklistEvalSerializer(serializers.ModelSerializer):
    """Serializer for ChecklistEval model."""
    
    catalog_item = ChecklistCatalogSerializer(read_only=True)
    catalog_item_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ChecklistEval
        fields = [
            'id', 'encounter', 'catalog_item', 'catalog_item_id',
            'status', 'confidence_score', 'evidence_text',
            'anchor_positions', 'generated_question', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_confidence_score(self, value):
        """Validate confidence score is between 0.0 and 1.0."""
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError("Confidence score must be between 0.0 and 1.0")
        return value


class ChecklistSummarySerializer(serializers.Serializer):
    """Serializer for checklist summary data."""
    
    total_items = serializers.IntegerField()
    covered_items = serializers.IntegerField()
    missing_items = serializers.IntegerField()
    partial_items = serializers.IntegerField()
    unclear_items = serializers.IntegerField()
    coverage_percentage = serializers.FloatField()
    needs_attention = serializers.ListField(
        child=ChecklistEvalSerializer()
    )


class ChecklistTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ChecklistTemplate model."""
    
    catalog_items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChecklistTemplate
        fields = [
            'id', 'name', 'description', 'specialty', 'is_default',
            'catalog_items_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_catalog_items_count(self, obj):
        """Get count of catalog items in this template."""
        return obj.catalog_items.count()