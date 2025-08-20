"""
Celery tasks for STT processing.
"""

import os
import boto3
import tempfile
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from encounters.models import AudioChunk, TranscriptSegment
from .services.whisper_service import WhisperService
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_audio_stt(self, audio_chunk_id: int):
    """
    Process committed audio chunk for STT transcription.
    
    Args:
        audio_chunk_id: ID of the AudioChunk to process
        
    Returns:
        Dict with processing results
    """
    try:
        # Get audio chunk
        try:
            audio_chunk = AudioChunk.objects.get(id=audio_chunk_id)
        except AudioChunk.DoesNotExist:
            logger.error(f"AudioChunk {audio_chunk_id} not found")
            return {'error': 'AudioChunk not found'}
        
        # Check if already processing or processed
        if audio_chunk.status in ['processing', 'processed']:
            logger.info(f"AudioChunk {audio_chunk_id} already {audio_chunk.status}")
            return {'status': audio_chunk.status}
        
        # Update status to processing
        audio_chunk.status = 'processing'
        audio_chunk.save()
        
        logger.info(f"Starting STT processing for AudioChunk {audio_chunk_id}")
        
        # Download file from S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL
        )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            suffix=f'.{audio_chunk.format}',
            delete=False
        ) as temp_file:
            try:
                # Download from S3
                s3_client.download_fileobj(
                    settings.AWS_STORAGE_BUCKET_NAME,
                    audio_chunk.file_path,
                    temp_file
                )
                temp_file_path = temp_file.name
                
                logger.info(f"Downloaded audio file to {temp_file_path}")
                
                # Initialize Whisper service
                whisper_service = WhisperService()
                
                # Transcribe audio
                result = whisper_service.transcribe_audio(
                    temp_file_path,
                    language='fa'  # Persian language hint
                )
                
                # Update audio chunk duration if not set
                if not audio_chunk.duration_seconds and result.get('duration'):
                    audio_chunk.duration_seconds = result['duration']
                
                # Save transcript segments
                segments_created = 0
                for segment_data in result.get('segments', []):
                    TranscriptSegment.objects.create(
                        audio_chunk=audio_chunk,
                        segment_number=segment_data['id'],
                        start_time=segment_data['start'],
                        end_time=segment_data['end'],
                        text=segment_data['text'],
                        confidence=segment_data.get('confidence')
                    )
                    segments_created += 1
                
                # Update audio chunk status
                audio_chunk.status = 'processed'
                audio_chunk.processed_at = timezone.now()
                audio_chunk.save()
                
                # Update encounter status
                encounter = audio_chunk.encounter
                if encounter.status == 'recording':
                    # Check if all audio chunks are processed
                    total_chunks = encounter.audio_chunks.filter(status='committed').count()
                    processed_chunks = encounter.audio_chunks.filter(status='processed').count()
                    
                    if processed_chunks >= total_chunks and total_chunks > 0:
                        encounter.status = 'processing'
                        encounter.save()
                
                logger.info(
                    f"STT processing completed for AudioChunk {audio_chunk_id}. "
                    f"Created {segments_created} segments. Text length: {len(result.get('text', ''))}"
                )
                
                return {
                    'status': 'success',
                    'segments_created': segments_created,
                    'text_length': len(result.get('text', '')),
                    'duration': result.get('duration', 0),
                    'language': result.get('language', 'unknown')
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    logger.debug(f"Cleaned up temporary file: {temp_file_path}")
        
    except Exception as e:
        logger.error(f"STT processing failed for AudioChunk {audio_chunk_id}: {str(e)}")
        
        # Update status to error
        try:
            audio_chunk = AudioChunk.objects.get(id=audio_chunk_id)
            audio_chunk.status = 'error'
            audio_chunk.save()
        except AudioChunk.DoesNotExist:
            pass
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries * 60  # 1min, 2min, 4min
            logger.info(f"Retrying STT processing in {retry_delay} seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {'error': str(e)}


@shared_task
def process_encounter_audio(encounter_id: int):
    """
    Process all committed audio chunks for an encounter.
    
    Args:
        encounter_id: ID of the Encounter to process
        
    Returns:
        Dict with processing results
    """
    try:
        from encounters.models import Encounter
        
        encounter = Encounter.objects.get(id=encounter_id)
        committed_chunks = encounter.audio_chunks.filter(status='committed')
        
        if not committed_chunks.exists():
            logger.warning(f"No committed audio chunks found for encounter {encounter_id}")
            return {'warning': 'No committed audio chunks found'}
        
        # Queue STT processing for each chunk
        task_ids = []
        for chunk in committed_chunks:
            task = process_audio_stt.delay(chunk.id)
            task_ids.append(task.id)
        
        logger.info(f"Queued STT processing for {len(task_ids)} chunks in encounter {encounter_id}")
        
        return {
            'status': 'queued',
            'chunks_queued': len(task_ids),
            'task_ids': task_ids
        }
        
    except Exception as e:
        logger.error(f"Failed to process encounter {encounter_id}: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_temp_files():
    """
    Cleanup old temporary files that might have been left behind.
    """
    import tempfile
    import glob
    import time
    
    temp_dir = tempfile.gettempdir()
    pattern = os.path.join(temp_dir, 'tmp*')
    
    cleaned_count = 0
    for temp_file in glob.glob(pattern):
        try:
            # Remove files older than 1 hour
            if os.path.isfile(temp_file) and time.time() - os.path.getmtime(temp_file) > 3600:
                os.unlink(temp_file)
                cleaned_count += 1
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
    
    logger.info(f"Cleaned up {cleaned_count} temporary files")
    return {'cleaned_files': cleaned_count}


@shared_task
def process_bulk_transcription(audio_chunk_ids: list):
    """Process multiple audio chunks for transcription (used by tests)."""
    results = []
    for chunk_id in audio_chunk_ids:
        try:
            result = process_audio_stt.apply(args=(chunk_id,)).get()
            results.append({'chunk_id': chunk_id, 'result': result})
        except Exception as exc:
            results.append({'chunk_id': chunk_id, 'error': str(exc)})
    return {'processed': len(results), 'results': results}
