"""
Serializers for STT app.
"""

from rest_framework import serializers
from encounters.models import TranscriptSegment


class TranscriptionRequestSerializer(serializers.Serializer):
    audio_chunk_id = serializers.IntegerField()
    language = serializers.CharField(required=False, default='en')
    prompt = serializers.CharField(required=False, allow_blank=True)


class TranscriptionStatusSerializer(serializers.Serializer):
    chunk_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['queued', 'processing', 'completed', 'failed'])
    progress = serializers.IntegerField(min_value=0, max_value=100)
    result = serializers.JSONField(required=False, allow_null=True)


class TranscriptSegmentSerializer(serializers.ModelSerializer):
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = TranscriptSegment
        fields = [
            'id', 'segment_number', 'start_time', 'end_time',
            'text', 'confidence', 'created_at', 'duration'
        ]
    
    def get_duration(self, obj):
        """Calculate segment duration in seconds."""
        if obj.start_time is not None and obj.end_time is not None:
            return round(obj.end_time - obj.start_time, 2)
        return None


class TranscriptSegmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptSegment
        fields = ['text']
        
    def validate_text(self, value):
        """Validate transcript text."""
        if not value or not value.strip():
            raise serializers.ValidationError("Text cannot be empty")
        
        if len(value.strip()) > 5000:
            raise serializers.ValidationError("Text is too long (max 5000 characters)")
        
        return value.strip()
