from __future__ import annotations

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import AudioSession
from .serializers import AudioChunkSerializer, AudioSessionCreateSerializer, CommitSerializer
from .s3 import build_object_key, get_bucket_name, get_s3_client


@csrf_exempt
@api_view(["POST"]) 
@permission_classes([AllowAny])
def create_session(request):
    serializer = AudioSessionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    session = serializer.create(serializer.validated_data)
    return Response({"session_id": str(session.id), "storage_backend": session.storage_backend})


@csrf_exempt
@api_view(["POST"]) 
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def upload_chunk(request):
    serializer = AudioChunkSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({"ok": True}, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(["POST"]) 
@permission_classes([AllowAny])
def commit_session(request):
    serializer = CommitSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    session = get_object_or_404(AudioSession, id=serializer.validated_data["session_id"])
    if session.is_committed:
        return Response({"detail": "Already committed"}, status=status.HTTP_400_BAD_REQUEST)

    if session.storage_backend == "local":
        from django.core.files.base import ContentFile
        chunks = session.chunks.order_by("chunk_index").all()
        parts: list[bytes] = []
        for chunk in chunks:
            with chunk.file.open("rb") as fh:
                parts.append(fh.read())
        combined = b"".join(parts)
        filename = serializer.validated_data.get("filename") or "audio.wav"
        session.final_file.save(filename, ContentFile(combined), save=False)
        session.is_committed = True
        session.save(update_fields=["final_file", "is_committed"]) 
        return Response({"ok": True, "storage": "local", "final_path": session.final_file.url})
    else:
        # For S3, we assume client uploaded to pre-signed URL, so just mark committed
        session.is_committed = True
        session.save(update_fields=["is_committed"]) 
        return Response({"ok": True, "storage": "s3", "object_key": session.s3_object_key})


@api_view(["GET"]) 
def download_final(_request, session_id: str):
    session = get_object_or_404(AudioSession, id=session_id, is_committed=True)
    if session.storage_backend == "local":
        return FileResponse(session.final_file.open("rb"), as_attachment=True)
    # For S3 we could redirect to a signed GET URL
    s3 = get_s3_client()
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": get_bucket_name(), "Key": session.s3_object_key},
        ExpiresIn=300,
    )
    return Response({"url": url})


@csrf_exempt
@api_view(["POST"]) 
@permission_classes([AllowAny])
def s3_presign_upload(request):
    session_id = request.data.get("session_id")
    filename = request.data.get("filename", "audio.wav")
    session = get_object_or_404(AudioSession, id=session_id)
    if session.storage_backend != "s3":
        return Response({"detail": "Session is not S3-backed"}, status=400)
    key = build_object_key(str(session.id), filename)
    s3 = get_s3_client()
    fields = None
    conditions = None
    url = s3.generate_presigned_post(
        Bucket=get_bucket_name(),
        Key=key,
        ExpiresIn=300,
        Fields=fields,
        Conditions=conditions,
    )
    # Save key for later commit/GET
    session.s3_object_key = key
    session.save(update_fields=["s3_object_key"]) 
    return Response(url)


@csrf_exempt
@api_view(["POST"]) 
@permission_classes([AllowAny])
def s3_confirm_upload(request):
    session_id = request.data.get("session_id")
    session = get_object_or_404(AudioSession, id=session_id)
    if session.storage_backend != "s3":
        return Response({"detail": "Session is not S3-backed"}, status=400)
    # Client calls this after uploading to S3 successfully
    return Response({"ok": True, "object_key": session.s3_object_key})

