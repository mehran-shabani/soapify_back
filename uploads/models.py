# upload/models.py
from __future__ import annotations

import uuid
from django.db import models
from django.utils import timezone


def upload_to_audio(instance: "AudioChunk", filename: str) -> str:
    # توجه: instance.session_id (فیلد ضمنی FK) معتبر است
    return f"audio_chunks/{instance.session_id}/{instance.chunk_index}_{filename}"


def upload_to_sessions(instance: "AudioSession", filename: str) -> str:
    return f"audio_sessions/{instance.id}/{filename}"


class AudioSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_committed = models.BooleanField(default=False)
    final_file = models.FileField(upload_to=upload_to_sessions, null=True, blank=True)
    storage_backend = models.CharField(
        max_length=16,
        choices=(
            ("local", "Local"),
            ("s3", "S3"),
        ),
        default="local",
    )
    s3_object_key = models.CharField(max_length=512, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class AudioChunk(models.Model):
    session = models.ForeignKey(AudioSession, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    file = models.FileField(upload_to=upload_to_audio)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("session", "chunk_index")
        ordering = ["chunk_index"]
