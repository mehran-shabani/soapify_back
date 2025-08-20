"""
Admin interface for encounters app.
"""

from django.contrib import admin
from .models import Encounter, AudioChunk, TranscriptSegment


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ['id', 'doctor', 'patient_ref', 'status', 'created_at', 'audio_count']
    list_filter = ['status', 'created_at', 'doctor']
    search_fields = ['patient_ref', 'doctor__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def audio_count(self, obj):
        return obj.audio_chunks.count()
    audio_count.short_description = 'Audio Files'


@admin.register(AudioChunk)
class AudioChunkAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'encounter', 'chunk_number', 'format', 'file_size_mb', 
        'status', 'uploaded_at', 'committed_at'
    ]
    list_filter = ['status', 'format', 'uploaded_at', 'committed_at']
    search_fields = ['encounter__patient_ref', 'file_path']
    readonly_fields = ['uploaded_at', 'committed_at', 'processed_at']
    
    def file_size_mb(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"
    file_size_mb.short_description = 'File Size'


@admin.register(TranscriptSegment)
class TranscriptSegmentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'audio_chunk', 'segment_number', 'start_time', 
        'end_time', 'confidence', 'text_preview'
    ]
    list_filter = ['audio_chunk__encounter', 'created_at']
    search_fields = ['text', 'audio_chunk__encounter__patient_ref']
    readonly_fields = ['created_at']
    
    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Text Preview'
