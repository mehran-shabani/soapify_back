"""
Serializers for encounters app.
"""

from rest_framework import serializers
from .models import Encounter, AudioChunk, TranscriptSegment


class TranscriptSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptSegment
        fields = [
            'id', 'segment_number', 'start_time', 'end_time',
            'text', 'confidence', 'created_at'
        ]


class AudioChunkSerializer(serializers.ModelSerializer):
    transcript_segments = TranscriptSegmentSerializer(many=True, read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = AudioChunk
        fields = [
            'id', 'chunk_number', 'file_path', 'file_size',
            'duration_seconds', 'duration_minutes', 'format', 'status',
            'uploaded_at', 'committed_at', 'processed_at',
            'transcript_segments'
        ]
        read_only_fields = ['uploaded_at', 'committed_at', 'processed_at']
    
    def get_duration_minutes(self, obj):
        """Convert duration to minutes:seconds format."""
        if obj.duration_seconds:
            minutes = int(obj.duration_seconds // 60)
            seconds = int(obj.duration_seconds % 60)
            return f"{minutes}:{seconds:02d}"
        return None


class EncounterSerializer(serializers.ModelSerializer):
    audio_chunks = AudioChunkSerializer(many=True, read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    total_duration = serializers.SerializerMethodField()
    audio_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Encounter
        fields = [
            'id', 'doctor', 'doctor_name', 'patient_ref', 'status',
            'created_at', 'updated_at', 'completed_at',
            'audio_chunks', 'total_duration', 'audio_count'
        ]
        read_only_fields = ['doctor', 'created_at', 'updated_at', 'completed_at']
    
    def get_total_duration(self, obj):
        """Calculate total duration of all audio chunks."""
        total_seconds = sum(
            chunk.duration_seconds or 0 
            for chunk in obj.audio_chunks.all()
        )
        if total_seconds > 0:
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            return f"{minutes}:{seconds:02d}"
        return "0:00"
    
    def get_audio_count(self, obj):
        """Get count of committed audio chunks."""
        return obj.audio_chunks.filter(status='committed').count()


class EncounterCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Encounter
        fields = ['patient_ref']