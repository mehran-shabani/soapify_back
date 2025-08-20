"""
Celery tasks for embeddings.
"""
import logging
from celery import shared_task
from django.db import transaction

from .services import EmbeddingService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def embed_texts_for_encounter(self, encounter_id):
    """
    Generate embeddings for all texts in an encounter.
    
    Args:
        encounter_id: ID of the encounter
    
    Returns:
        Dict with results
    """
    try:
        service = EmbeddingService()
        results = service.embed_texts_for_encounter(encounter_id)
        
        logger.info(f"Completed embedding generation for encounter {encounter_id}: {results}")
        return {
            'encounter_id': encounter_id,
            'status': 'completed',
            'results': results
        }
    
    except Exception as e:
        logger.error(f"Failed to generate embeddings for encounter {encounter_id}: {str(e)}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {
            'encounter_id': encounter_id,
            'status': 'failed',
            'error': str(e)
        }


@shared_task(bind=True, max_retries=3)
def embed_single_content(self, encounter_id, content_type, content_id, text):
    """
    Generate embedding for a single piece of content.
    
    Args:
        encounter_id: ID of the encounter
        content_type: Type of content
        content_id: ID of the content object
        text: Text to embed
    
    Returns:
        Dict with results
    """
    try:
        service = EmbeddingService()
        embedding_obj = service.store_embedding(encounter_id, content_type, content_id, text)
        
        logger.info(f"Generated embedding for {content_type}:{content_id}")
        return {
            'encounter_id': encounter_id,
            'content_type': content_type,
            'content_id': content_id,
            'embedding_id': embedding_obj.id,
            'status': 'completed'
        }
    
    except Exception as e:
        logger.error(f"Failed to generate embedding for {content_type}:{content_id}: {str(e)}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = 30 * (2 ** self.request.retries)  # 30s, 60s, 120s
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {
            'encounter_id': encounter_id,
            'content_type': content_type,
            'content_id': content_id,
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def cleanup_old_embeddings(days_old=30):
    """
    Clean up old embeddings to save storage space.
    
    Args:
        days_old: Number of days old to consider for cleanup
    
    Returns:
        Dict with cleanup results
    """
    from datetime import datetime, timedelta
    from .models import TextEmbedding, SimilaritySearch
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    try:
        with transaction.atomic():
            # Clean up old embeddings
            deleted_embeddings = TextEmbedding.objects.filter(
                created_at__lt=cutoff_date
            ).delete()
            
            # Clean up old similarity searches
            deleted_searches = SimilaritySearch.objects.filter(
                created_at__lt=cutoff_date
            ).delete()
        
        logger.info(f"Cleaned up {deleted_embeddings[0]} embeddings and {deleted_searches[0]} similarity searches")
        
        return {
            'status': 'completed',
            'deleted_embeddings': deleted_embeddings[0],
            'deleted_searches': deleted_searches[0],
            'cutoff_date': cutoff_date.isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to cleanup old embeddings: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def update_embedding_index_stats():
    """
    Update statistics for embedding indexes.
    
    Returns:
        Dict with update results
    """
    from .models import EmbeddingIndex, TextEmbedding
    
    try:
        # Update stats for each index
        for index in EmbeddingIndex.objects.filter(is_active=True):
            total_embeddings = TextEmbedding.objects.filter(
                model_name=index.model_name
            ).count()
            
            index.total_embeddings = total_embeddings
            index.save(update_fields=['total_embeddings', 'last_updated'])
        
        logger.info("Updated embedding index statistics")
        
        return {
            'status': 'completed',
            'updated_indexes': EmbeddingIndex.objects.filter(is_active=True).count()
        }
    
    except Exception as e:
        logger.error(f"Failed to update embedding index stats: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }