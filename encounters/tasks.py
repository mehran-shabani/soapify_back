"""
Celery tasks for encounters app.
"""

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_uncommitted_files():
    """
    Periodic task to cleanup uncommitted audio files.
    Should be scheduled to run every 2 hours.
    """
    try:
        call_command('cleanup_uncommitted_files', hours=2)
        logger.info(f"Cleanup task completed at {timezone.now()}")
        return "Cleanup completed successfully"
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        raise


@shared_task
def process_audio_chunk(chunk_id):
    """
    Process committed audio chunk for STT.
    This will be implemented in Stage 3.
    """
    from .models import AudioChunk
    
    try:
        chunk = AudioChunk.objects.get(id=chunk_id)
        chunk.status = 'processing'
        chunk.save()
        
        # TODO: Implement STT processing in Stage 3
        logger.info(f"Audio chunk {chunk_id} marked for processing")
        
        return f"Audio chunk {chunk_id} processing initiated"
    except AudioChunk.DoesNotExist:
        logger.error(f"Audio chunk {chunk_id} not found")
        raise
    except Exception as e:
        logger.error(f"Failed to process audio chunk {chunk_id}: {e}")
        raise

# Import STT task
from stt.tasks import process_audio_stt

@shared_task
def trigger_stt_processing(chunk_id):
    """
    Trigger STT processing after successful commit.
    """
    try:
        # Start STT processing
        task = process_audio_stt.delay(chunk_id)
        logger.info(f"Triggered STT processing for chunk {chunk_id}, task: {task.id}")
        return f"STT processing triggered: {task.id}"
    except Exception as e:
        logger.error(f"Failed to trigger STT processing for chunk {chunk_id}: {e}")
        raise
