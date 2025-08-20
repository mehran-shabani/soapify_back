"""
Views for STT processing and transcript management.
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from encounters.models import AudioChunk, TranscriptSegment, Encounter
from .tasks import process_audio_stt, process_encounter_audio, process_bulk_transcription
from .serializers import TranscriptSegmentSerializer
import logging
from celery.result import AsyncResult
from .services.whisper_service import WhisperService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_stt_processing(request):
    """
    Start STT processing for a specific audio chunk.
    Expected body: {"chunk_id": <int>}
    """
    try:
        # Get chunk_id from request body
        chunk_id = request.data.get('chunk_id')
        if not chunk_id:
            return Response(
                {'error': 'chunk_id is required in request body'},
                status=status.HTTP_400_BAD_REQUEST
            )
        

        # Get audio chunk and verify ownership
        audio_chunk = get_object_or_404(
            AudioChunk,
            id=chunk_id,
            encounter__doctor=request.user
        )
        
        # Check if chunk is committed
        if audio_chunk.status != 'committed':
            return Response(
                {'error': f'Audio chunk must be committed before processing. Current status: {audio_chunk.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already processing or processed
        if audio_chunk.status in ['processing', 'processed']:
            return Response(
                {'message': f'Audio chunk is already {audio_chunk.status}'},
                status=status.HTTP_200_OK
            )
        
        # Start STT processing task
        task = process_audio_stt.delay(audio_chunk.id)
        
        logger.info(f"Started STT processing for AudioChunk {audio_chunk.id}, task: {task.id}")
        
        return Response(
            {
                'status': 'processing',
                'task_id': task.id,
                'audio_chunk_id': audio_chunk.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )
        
    except Exception as e:
        logger.error(f"Failed to start STT processing for chunk {chunk_id}: {e}")
        return Response(
            {'error': f'Failed to start processing: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_encounter_stt(request, encounter_id):
    """
    Start STT processing for all committed audio chunks in an encounter.
    """
    try:
        # Get encounter and verify ownership
        encounter = get_object_or_404(
            Encounter,
            id=encounter_id,
            doctor=request.user
        )
        
        # Check if encounter has committed chunks
        committed_chunks = encounter.audio_chunks.filter(status='committed')
        if not committed_chunks.exists():
            return Response(
                {'error': 'No committed audio chunks found in this encounter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start processing task
        task = process_encounter_audio.delay(encounter.id)
        
        logger.info(f"Started encounter STT processing for Encounter {encounter.id}, task: {task.id}")
        
        return Response(
            {
                'status': 'processing',
                'task_id': task.id,
                'encounter_id': encounter.id,
                'chunks_to_process': committed_chunks.count(),
            },
            status=status.HTTP_202_ACCEPTED,
        )
        
    except Exception as e:
        logger.error(f"Failed to start encounter STT processing for {encounter_id}: {e}")
        return Response(
            {'error': f'Failed to start processing: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transcript(request, audio_chunk_id):
    """
    Get transcript segments for an audio chunk.
    """
    try:
        # Get audio chunk and verify ownership
        audio_chunk = get_object_or_404(
            AudioChunk,
            id=audio_chunk_id,
            encounter__doctor=request.user
        )
        
        # Get transcript segments
        segments = TranscriptSegment.objects.filter(
            audio_chunk=audio_chunk
        ).order_by('segment_number')
        
        serializer = TranscriptSegmentSerializer(segments, many=True)
        
        return Response({
            'audio_chunk_id': audio_chunk.id,
            'status': audio_chunk.status,
            'segments': serializer.data,
            'total_segments': segments.count(),
            'full_text': ' '.join([seg.text for seg in segments])
        })
        
    except Exception as e:
        logger.error(f"Failed to get transcript for chunk {audio_chunk_id}: {e}")
        return Response(
            {'error': f'Failed to get transcript: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_encounter_transcript(request, encounter_id):
    """
    Get full transcript for all audio chunks in an encounter.
    """
    try:
        # Get encounter and verify ownership
        encounter = get_object_or_404(
            Encounter,
            id=encounter_id,
            doctor=request.user
        )
        
        # Get all audio chunks with their segments
        audio_chunks = encounter.audio_chunks.filter(
            status='processed'
        ).order_by('chunk_number')
        
        transcript_data = []
        full_text_parts = []
        
        for chunk in audio_chunks:
            segments = TranscriptSegment.objects.filter(
                audio_chunk=chunk
            ).order_by('segment_number')
            
            chunk_text = ' '.join([seg.text for seg in segments])
            full_text_parts.append(chunk_text)
            
            transcript_data.append({
                'chunk_id': chunk.id,
                'chunk_number': chunk.chunk_number,
                'status': chunk.status,
                'segments': TranscriptSegmentSerializer(segments, many=True).data,
                'chunk_text': chunk_text
            })
        
        return Response({
            'encounter_id': encounter.id,
            'status': encounter.status,
            'chunks': transcript_data,
            'total_chunks': len(transcript_data),
            'full_text': ' '.join(full_text_parts)
        })
        
    except Exception as e:
        logger.error(f"Failed to get encounter transcript for {encounter_id}: {e}")
        return Response(
            {'error': f'Failed to get transcript: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_transcript_segment(request, segment_id):
    """
    Update a transcript segment text (manual editing).
    """
    try:
        # Get segment and verify ownership
        segment = get_object_or_404(
            TranscriptSegment,
            id=segment_id,
            audio_chunk__encounter__doctor=request.user
        )
        
        new_text = request.data.get('text', '').strip()
        if not new_text:
            return Response(
                {'error': 'Text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update segment
        segment.text = new_text
        segment.save()
        
        logger.info(f"Updated transcript segment {segment_id}")
        
        return Response({
            'message': 'Transcript segment updated',
            'segment': TranscriptSegmentSerializer(segment).data
        })
        
    except Exception as e:
        logger.error(f"Failed to update transcript segment {segment_id}: {e}")
        return Response(
            {'error': f'Failed to update segment: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_transcript(request):
    """
    Search transcript segments by text.
    """
    try:
        query = request.GET.get('q', '').strip()
        encounter_id = request.GET.get('encounter_id')
        if not query:
            return Response({'error': 'Search query is required'}, status=status.HTTP_400_BAD_REQUEST)
        # Base queryset
        segments = TranscriptSegment.objects.filter(
            audio_chunk__encounter__doctor=request.user,
            text__icontains=query
        )
        if encounter_id:
            segments = segments.filter(audio_chunk__encounter_id=encounter_id)
        segments = segments.select_related(
            'audio_chunk', 'audio_chunk__encounter'
        ).order_by('-audio_chunk__encounter__created_at', 'audio_chunk__chunk_number', 'segment_number')
        results = []
        for segment in segments:
            results.append({
                'segment': TranscriptSegmentSerializer(segment).data,
                'audio_chunk_id': segment.audio_chunk.id,
                'encounter_id': segment.audio_chunk.encounter.id,
                'patient_ref': segment.audio_chunk.encounter.patient_ref,
                'created_at': segment.audio_chunk.encounter.created_at
            })
        return Response({'query': query, 'results': results, 'total_results': len(results)})
    except Exception as e:
        logger.error(f"Failed to search transcript: {e}")
        return Response({'error': f'Search failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transcription_status(request, task_id):
    """Return Celery task status and result if available."""
    result = AsyncResult(task_id)
    return Response({
        'state': result.state,
        'result': result.result if hasattr(result, 'result') else None,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transcription_history(request):
    """Return transcript history for an encounter (required: encounter_id)."""
    encounter_id = request.GET.get('encounter_id')
    if not encounter_id:
        return Response({'error': 'encounter_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    # Verify encounter ownership
    encounter = get_object_or_404(Encounter, id=encounter_id, doctor=request.user)
    chunks = encounter.audio_chunks.all().order_by('chunk_number')
    data = []
    for chunk in chunks:
        segments = TranscriptSegment.objects.filter(audio_chunk=chunk).order_by('segment_number')
        data.append({
            'chunk_id': chunk.id,
            'chunk_number': chunk.chunk_number,
            'segments': TranscriptSegmentSerializer(segments, many=True).data,
        })
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_and_transcribe(request):
    """Accept multipart file and transcribe directly via WhisperService."""
    file = request.FILES.get('audio')
    language = request.data.get('language')
    if not file:
        return Response({'error': 'No audio file provided'}, status=status.HTTP_400_BAD_REQUEST)
    service = WhisperService()
    result = service.transcribe_audio_chunk(file.read(), file.name, language=language)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_transcribe(request):
    """Queue bulk transcription for list of committed chunk ids."""
    chunk_ids = request.data.get('chunk_ids') or []
    # Validate all chunk ids belong to the user and are committed
    owned_committed = list(
        AudioChunk.objects.filter(
            id__in=chunk_ids, encounter__doctor=request.user, status='committed'
        ).values_list('id', flat=True)
    )
    if len(owned_committed) != len(chunk_ids):
        return Response({'error': 'Invalid chunk IDs or not committed'}, status=status.HTTP_400_BAD_REQUEST)
    task = process_bulk_transcription.delay(owned_committed)
    return Response({'status': 'processing', 'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
