"""
Embedding services for SOAPify.
"""
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from django.db import transaction

from .models import TextEmbedding
from integrations.clients.gpt_client import GapGPTClient

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing text embeddings."""
    
    def __init__(self):
        self.gpt_client = GapGPTClient()
        self.model_name = 'text-embedding-ada-002'
        self.dimension = 1536
        self.similarity_threshold = 0.7
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a text string.
        
        Args:
            text: Text to embed
        
        Returns:
            List of floats representing the embedding vector
        """
        try:
            # Clean and prepare text
            cleaned_text = self._clean_text(text)
            if not cleaned_text:
                raise ValueError("Empty text after cleaning")
            
            # Generate embedding using GapGPT
            response = self.gpt_client.create_embedding(
                input=cleaned_text,
                model=self.model_name
            )
            
            if not response or 'data' not in response or not response['data']:
                raise ValueError("Invalid embedding response")
            
            embedding = response['data'][0]['embedding']
            
            # Validate embedding dimension
            if len(embedding) != self.dimension:
                raise ValueError(f"Expected {self.dimension} dimensions, got {len(embedding)}")
            
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    def store_embedding(self, encounter_id: int, content_type: str, content_id: int, text: str) -> TextEmbedding:
        """
        Generate and store embedding for content.
        
        Args:
            encounter_id: ID of the encounter
            content_type: Type of content (transcript, soap_draft, etc.)
            content_id: ID of the content object
            text: Text content to embed
        
        Returns:
            TextEmbedding object
        """
        try:
            # Generate embedding
            embedding_vector = self.generate_embedding(text)
            
            # Store in database
            with transaction.atomic():
                embedding_obj, created = TextEmbedding.objects.update_or_create(
                    content_type=content_type,
                    content_id=content_id,
                    defaults={
                        'encounter_id': encounter_id,
                        'text_content': text[:1000],  # Truncate for storage
                        'embedding_vector': embedding_vector,
                        'model_name': self.model_name
                    }
                )
            
            logger.info(f"{'Created' if created else 'Updated'} embedding for {content_type}:{content_id}")
            return embedding_obj
        
        except Exception as e:
            logger.error(f"Failed to store embedding: {str(e)}")
            raise
    
    def embed_texts_for_encounter(self, encounter_id: int) -> Dict[str, int]:
        """
        Generate embeddings for all relevant texts in an encounter.
        
        Args:
            encounter_id: ID of the encounter
        
        Returns:
            Dict with counts of embeddings created by content type
        """
        from encounters.models import Encounter
        
        try:
            encounter = Encounter.objects.get(id=encounter_id)
        except Encounter.DoesNotExist:
            raise ValueError(f"Encounter {encounter_id} not found")
        
        results = {
            'transcript': 0,
            'soap_draft': 0,
            'soap_final': 0,
            'notes': 0,
            'checklist': 0
        }
        
        # Embed transcript segments
        for segment in encounter.transcript_segments.all():
            if segment.text and len(segment.text.strip()) > 10:  # Skip very short segments
                self.store_embedding(
                    encounter_id=encounter_id,
                    content_type='transcript',
                    content_id=segment.id,
                    text=segment.text
                )
                results['transcript'] += 1
        
        # Embed SOAP drafts
        for draft in encounter.soap_drafts.all():
            if draft.content:
                # Combine all SOAP sections
                combined_text = self._combine_soap_content(draft.content)
                if combined_text:
                    self.store_embedding(
                        encounter_id=encounter_id,
                        content_type='soap_draft',
                        content_id=draft.id,
                        text=combined_text
                    )
                    results['soap_draft'] += 1
        
        # Embed final artifacts
        if hasattr(encounter, 'final_artifacts') and encounter.final_artifacts:
            artifacts = encounter.final_artifacts
            if artifacts.soap_content:
                combined_text = self._combine_soap_content(artifacts.soap_content)
                if combined_text:
                    self.store_embedding(
                        encounter_id=encounter_id,
                        content_type='soap_final',
                        content_id=artifacts.id,
                        text=combined_text
                    )
                    results['soap_final'] += 1
        
        # Embed checklist evaluations
        for eval_obj in encounter.checklist_evals.all():
            if eval_obj.evidence_text:
                self.store_embedding(
                    encounter_id=encounter_id,
                    content_type='checklist',
                    content_id=eval_obj.id,
                    text=eval_obj.evidence_text
                )
                results['checklist'] += 1
        
        logger.info(f"Generated embeddings for encounter {encounter_id}: {results}")
        return results
    
    def similarity_search(self, query_text: str, encounter_id: Optional[int] = None, 
                         content_types: Optional[List[str]] = None, 
                         limit: int = 10, threshold: float = None) -> List[Dict[str, Any]]:
        """
        Perform similarity search using embeddings.
        
        Args:
            query_text: Text to search for
            encounter_id: Optional encounter ID to limit search scope
            content_types: Optional list of content types to search
            limit: Maximum number of results
            threshold: Minimum similarity threshold
        
        Returns:
            List of similar content with similarity scores
        """
        if threshold is None:
            threshold = self.similarity_threshold
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query_text)
        
        # Build queryset
        queryset = TextEmbedding.objects.all()
        
        if encounter_id:
            queryset = queryset.filter(encounter_id=encounter_id)
        
        if content_types:
            queryset = queryset.filter(content_type__in=content_types)
        
        # Calculate similarities (this is a simplified version - in production, use pgvector)
        results = []
        
        for embedding_obj in queryset:
            similarity = self._cosine_similarity(query_embedding, embedding_obj.embedding_vector)
            
            if similarity >= threshold:
                results.append({
                    'id': embedding_obj.id,
                    'encounter_id': embedding_obj.encounter_id,
                    'content_type': embedding_obj.content_type,
                    'content_id': embedding_obj.content_id,
                    'text_content': embedding_obj.text_content,
                    'similarity_score': similarity,
                    'created_at': embedding_obj.created_at
                })
        
        # Sort by similarity score
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return results[:limit]
    
    def _clean_text(self, text: str) -> str:
        """Clean text for embedding generation."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        cleaned = ' '.join(text.split())
        
        # Truncate if too long (OpenAI has token limits)
        if len(cleaned) > 8000:  # Rough character limit
            cleaned = cleaned[:8000] + "..."
        
        return cleaned
    
    def _combine_soap_content(self, soap_content: Dict[str, Any]) -> str:
        """Combine SOAP sections into a single text."""
        sections = []
        
        for section_name, section_data in soap_content.items():
            if isinstance(section_data, dict) and 'content' in section_data:
                sections.append(f"{section_name.upper()}: {section_data['content']}")
            elif isinstance(section_data, str):
                sections.append(f"{section_name.upper()}: {section_data}")
        
        return "\\n\\n".join(sections)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            # Convert to numpy arrays
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
        
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {str(e)}")
            return 0.0
    
    def get_related_content(self, encounter_id: int, reference_text: str, 
                          content_types: Optional[List[str]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get content related to a reference text within an encounter.
        
        Args:
            encounter_id: ID of the encounter
            reference_text: Reference text to find related content for
            content_types: Optional list of content types to search
            limit: Maximum number of results
        
        Returns:
            List of related content
        """
        return self.similarity_search(
            query_text=reference_text,
            encounter_id=encounter_id,
            content_types=content_types,
            limit=limit,
            threshold=0.6  # Lower threshold for related content
        )
    
    def cluster_similar_content(self, encounter_id: int, content_type: str = 'transcript') -> Dict[str, Any]:
        """
        Cluster similar content within an encounter.
        
        Args:
            encounter_id: ID of the encounter
            content_type: Type of content to cluster
        
        Returns:
            Dict with clustering results
        """
        # Get all embeddings for the encounter and content type
        embeddings = TextEmbedding.objects.filter(
            encounter_id=encounter_id,
            content_type=content_type
        )
        
        if embeddings.count() < 2:
            return {'clusters': [], 'message': 'Not enough content to cluster'}
        
        # This is a simplified clustering - in production, use scikit-learn or similar
        # For now, just group by high similarity
        clusters = []
        processed_ids = set()
        
        for embedding in embeddings:
            if embedding.id in processed_ids:
                continue
            
            cluster = {
                'representative': {
                    'id': embedding.id,
                    'text': embedding.text_content,
                    'content_id': embedding.content_id
                },
                'similar_items': []
            }
            
            # Find similar items
            for other_embedding in embeddings:
                if other_embedding.id != embedding.id and other_embedding.id not in processed_ids:
                    similarity = self._cosine_similarity(
                        embedding.embedding_vector,
                        other_embedding.embedding_vector
                    )
                    
                    if similarity > 0.8:  # High similarity threshold for clustering
                        cluster['similar_items'].append({
                            'id': other_embedding.id,
                            'text': other_embedding.text_content,
                            'content_id': other_embedding.content_id,
                            'similarity': similarity
                        })
                        processed_ids.add(other_embedding.id)
            
            processed_ids.add(embedding.id)
            
            # Only include clusters with similar items
            if cluster['similar_items']:
                clusters.append(cluster)
        
        return {
            'encounter_id': encounter_id,
            'content_type': content_type,
            'clusters': clusters,
            'total_clusters': len(clusters)
        }