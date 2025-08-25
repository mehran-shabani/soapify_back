"""
Views for encounters and audio file management.
"""

import uuid
import boto3
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from botocore.exceptions import ClientError
from .models import Encounter, AudioChunk
from .serializers import EncounterSerializer, AudioChunkSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_encounter(request):
    """
    Create a new medical encounter.
    """
    from .serializers import EncounterCreateSerializer
    
    serializer = EncounterCreateSerializer(data=request.data)
    if serializer.is_valid():
        encounter = serializer.save(doctor=request.user)
        # Return the full encounter data using the main serializer
        response_serializer = EncounterSerializer(encounter)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_presigned_url(request):
    """
    Generate a pre-signed URL for uploading audio files to S3.
    """
    try:
        filename = request.data.get('filename')
        file_size = request.data.get('file_size')
        content_type = request.data.get('content_type', 'audio/m4a')
        encounter_id = request.data.get('encounter_id')
        
        if not all([filename, file_size, encounter_id]):
            return Response(
                {'error': 'filename, file_size, and encounter_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 25MB)
        if file_size > 25 * 1024 * 1024:
            return Response(
                {'error': 'File size exceeds 25MB limit'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file format
        allowed_extensions = ['.wav', '.mp3', '.m4a']
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            return Response(
                {'error': 'Invalid file format. Allowed: WAV, MP3, M4A'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if encounter exists and belongs to user
        try:
            encounter = Encounter.objects.get(id=encounter_id, doctor=request.user)
        except Encounter.DoesNotExist:
            return Response(
                {'error': 'Encounter not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate unique file key
        file_id = str(uuid.uuid4())
        file_extension = filename.split('.')[-1].lower()
        s3_key = f"audio/{encounter_id}/{file_id}.{file_extension}"
        
        # Create AudioChunk record
        chunk_number = encounter.audio_chunks.count() + 1
        audio_chunk = AudioChunk.objects.create(
            encounter=encounter,
            chunk_number=chunk_number,
            file_path=s3_key,
            file_size=file_size,
            format=file_extension,
            status='uploaded'
        )
        
        # Generate pre-signed URL
        try:
            # Check if MinIO is configured
            if not all([
                settings.MINIO_ACCESS_KEY,
                settings.MINIO_SECRET_KEY,
                settings.MINIO_MEDIA_BUCKET
            ]):
                # For tests or development without MinIO
                presigned_url = f"https://mock-minio-url.com/upload/{s3_key}"
            else:
                # استفاده از MinIO client
                from uploads.minio import get_minio_client
                minio_client = get_minio_client()
                
                presigned_url = minio_client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': settings.MINIO_MEDIA_BUCKET,
                        'Key': s3_key,
                        'ContentType': content_type,
                    },
                    ExpiresIn=3600  # 1 hour
                )
        except Exception as s3_error:
            return Response(
                {'error': f'S3 configuration error: {str(s3_error)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'presigned_url': presigned_url,
            'chunk_id': audio_chunk.id,
            'expires_at': (timezone.now() + timedelta(hours=1)).isoformat(),
        })
        
    except ClientError as e:
        return Response(
            {'error': f'S3 error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {'error': f'Server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def commit_audio_file(request):
    """
    Commit an uploaded audio file.
    """
    try:
        file_id = request.data.get('chunk_id') or request.data.get('file_id')
        
        if not file_id:
            return Response(
                {'error': 'file_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get AudioChunk and verify ownership
        try:
            audio_chunk = AudioChunk.objects.get(
                id=file_id,
                encounter__doctor=request.user
            )
        except AudioChunk.DoesNotExist:
            return Response(
                {'error': 'Audio file not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already committed
        if audio_chunk.status == 'committed':
            return Response(
                {'message': 'File already committed'},
                status=status.HTTP_200_OK
            )
        
        # Verify file exists in S3
        # استفاده از MinIO client
        from uploads.minio import get_minio_client
        minio_client = get_minio_client()
        
        try:
            minio_client.head_object(
                Bucket=settings.MINIO_MEDIA_BUCKET,
                Key=audio_chunk.file_path
            )
        except ClientError:
            return Response(
                {'error': 'File not found in storage'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update AudioChunk status
        audio_chunk.status = 'committed'
        audio_chunk.committed_at = timezone.now()
        audio_chunk.save()

        # Trigger STT processing
        from .tasks import trigger_stt_processing
        trigger_stt_processing.delay(audio_chunk.id)
        
        # Update encounter status if this is the first audio
        if audio_chunk.encounter.status == 'created':
            audio_chunk.encounter.status = 'recording'
            audio_chunk.encounter.save()
        
        return Response({
            'message': 'File committed successfully',
            'file_id': audio_chunk.id,
            'status': audio_chunk.status,
            'committed_at': audio_chunk.committed_at.isoformat(),
        })
        
    except ClientError as e:
        return Response(
            {'error': f'S3 error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {'error': f'Server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_encounters(request):
    """
    List user's encounters.
    """
    encounters = Encounter.objects.filter(doctor=request.user).order_by('-created_at')
    serializer = EncounterSerializer(encounters, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def encounter_detail(request, encounter_id):
    """
    Get encounter details with audio chunks.
    """
    try:
        encounter = Encounter.objects.get(id=encounter_id, doctor=request.user)
        serializer = EncounterSerializer(encounter)
        return Response(serializer.data)
    except Encounter.DoesNotExist:
        return Response(
            {'error': 'Encounter not found'},
            status=status.HTTP_404_NOT_FOUND
        )