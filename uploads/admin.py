# upload/admin.py
from django.contrib import admin
from .models import AudioSession, AudioChunk

@admin.register(AudioSession)
class AudioSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "storage_backend", "is_committed", "created_at")
    list_filter = ("storage_backend", "is_committed", "created_at")
    search_fields = ("id", "s3_object_key")

@admin.register(AudioChunk)
class AudioChunkAdmin(admin.ModelAdmin):
    list_display = ("session", "chunk_index", "created_at")
    list_filter = ("created_at",)
    search_fields = ("session__id",)
