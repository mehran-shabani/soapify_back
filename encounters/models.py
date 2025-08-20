"""
Medical encounters and audio chunks models.
"""

from django.db import models
from django.conf import settings


class Encounter(models.Model):
    """
    A medical encounter/consultation session.
    """
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('recording', 'Recording'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]
    
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='encounters')
    patient_ref = models.CharField(max_length=100, help_text="Patient reference ID (no PHI)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'encounters'
        indexes = [
            models.Index(fields=['doctor', 'created_at']),
            models.Index(fields=['patient_ref']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Encounter {self.id} - {self.patient_ref}"


class AudioChunk(models.Model):
    """
    Audio chunks uploaded for an encounter.
    """
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('committed', 'Committed'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('error', 'Error'),
    ]
    
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='audio_chunks')
    chunk_number = models.PositiveIntegerField()
    file_path = models.CharField(max_length=500, help_text="S3 object key")
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    duration_seconds = models.FloatField(null=True, blank=True)
    format = models.CharField(max_length=10, choices=[('wav', 'WAV'), ('mp3', 'MP3'), ('m4a', 'M4A')])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    committed_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'audio_chunks'
        unique_together = ['encounter', 'chunk_number']
        indexes = [
            models.Index(fields=['encounter', 'chunk_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"AudioChunk {self.chunk_number} for {self.encounter}"


class TranscriptSegment(models.Model):
    """
    Transcript segments from STT processing.
    """
    audio_chunk = models.ForeignKey(AudioChunk, on_delete=models.CASCADE, related_name='transcript_segments')
    segment_number = models.PositiveIntegerField()
    start_time = models.FloatField(help_text="Start time in seconds")
    end_time = models.FloatField(help_text="End time in seconds")
    text = models.TextField()
    confidence = models.FloatField(null=True, blank=True, help_text="STT confidence score")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'transcript_segments'
        unique_together = ['audio_chunk', 'segment_number']
        indexes = [
            models.Index(fields=['audio_chunk', 'segment_number']),
            models.Index(fields=['start_time']),
        ]
    
    def __str__(self):
        return f"Segment {self.segment_number} - {self.text[:50]}..."