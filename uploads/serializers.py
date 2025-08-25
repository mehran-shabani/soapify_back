# upload/serializers.py
from __future__ import annotations

from rest_framework import serializers
from .models import AudioChunk, AudioSession


class AudioSessionCreateSerializer(serializers.Serializer):
    storage_backend = serializers.ChoiceField(choices=["local", "s3"], default="local")

    def create(self, validated_data):
        return AudioSession.objects.create(
            storage_backend=validated_data.get("storage_backend", "local")
        )


class AudioChunkSerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = AudioChunk
        fields = ["session_id", "chunk_index", "file"]

    def validate(self, attrs):
        session_id = attrs.get("session_id")
        try:
            session = AudioSession.objects.get(id=session_id)
        except AudioSession.DoesNotExist as err:
            raise serializers.ValidationError({"session_id": "Invalid session"}) from err
        attrs["session"] = session
        attrs.pop("session_id", None)
        return attrs


class CommitSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    filename = serializers.CharField(required=False, default="audio.wav")
