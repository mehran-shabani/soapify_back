"""
Search services for SOAPify.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from django.db import models
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.contrib.auth import get_user_model

from .models import SearchableContent, SearchQuery as SearchQueryModel, SearchResult
from embeddings.services import EmbeddingService

logger = logging.getLogger(__name__)
User = get_user_model()


class SearchService:
    """Simple wrapper delegating to hybrid search for backward compatibility in tests."""
    def __init__(self):
        self._hybrid = None

    def search(self, *args, **kwargs):
        if self._hybrid is None:
            self._hybrid = HybridSearchService()
        # Return only the results list for compatibility with tests
        return [r for r in self._hybrid.search(*args, **kwargs).get('results', [])]


class HybridSearchService:
    """Hybrid search service combining full-text search and semantic search."""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.fts_weight = 0.6  # Weight for full-text search
        self.semantic_weight = 0.4  # Weight for semantic search
    
    def search(self, query_text: str, user: Optional[User] = None, 
               filters: Optional[Dict[str, Any]] = None, limit: int = 20) -> Dict[str, Any]:
        """
        Perform hybrid search combining FTS and semantic search.
        
        Args:
            query_text: Search query
            user: User performing the search
            filters: Optional filters (encounter_id, content_type, etc.)
            limit: Maximum number of results
        
        Returns:
            Dict with search results and metadata
        """
        start_time = time.time()
        
        if not query_text or not query_text.strip():
            return {
                'results': [],
                'total_count': 0,
                'execution_time_ms': 0,
                'query': query_text
            }
        
        filters = filters or {}
        
        # Perform full-text search
        fts_results = self._full_text_search(query_text, filters, limit)
        
        # Perform semantic search
        semantic_results = self._semantic_search(query_text, filters, limit)
        
        # Combine and rank results
        combined_results = self._combine_search_results(
            fts_results, semantic_results, query_text, limit
        )
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Store search query for analytics
        search_query_obj = SearchQueryModel.objects.create(
            query_text=query_text,
            filters=filters,
            user=user,
            results_count=len(combined_results),
            execution_time_ms=execution_time_ms
        )
        
        # Cache results
        self._cache_search_results(search_query_obj, combined_results)
        
        return {
            'results': combined_results,
            'total_count': len(combined_results),
            'execution_time_ms': execution_time_ms,
            'query': query_text,
            'filters': filters,
            'search_id': search_query_obj.id
        }
    
    def _full_text_search(self, query_text: str, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Perform full-text search using PostgreSQL."""
        try:
            # Build queryset
            queryset = SearchableContent.objects.all()
            
            # Apply filters
            if filters.get('encounter_id'):
                queryset = queryset.filter(encounter_id=filters['encounter_id'])
            
            if filters.get('content_type'):
                content_types = filters['content_type']
                if isinstance(content_types, str):
                    content_types = [content_types]
                queryset = queryset.filter(content_type__in=content_types)
            
            if filters.get('date_from'):
                queryset = queryset.filter(created_at__gte=filters['date_from'])
            
            if filters.get('date_to'):
                queryset = queryset.filter(created_at__lte=filters['date_to'])
            
            # Perform full-text search
            search_query = SearchQuery(query_text)
            search_vector = SearchVector('title', weight='A') + SearchVector('content', weight='B')
            
            results = queryset.annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query)
            ).filter(
                search=search_query
            ).order_by('-rank')[:limit]
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'id': result.id,
                    'encounter_id': result.encounter_id,
                    'content_type': result.content_type,
                    'content_id': result.content_id,
                    'title': result.title,
                    'content': result.content,
                    'snippet': self._generate_snippet(result.content, query_text),
                    'score': float(result.rank) if result.rank else 0.0,
                    'search_type': 'full_text',
                    'metadata': result.metadata,
                    'created_at': result.created_at
                })
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"Full-text search failed: {str(e)}")
            return []
    
    def _semantic_search(self, query_text: str, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings."""
        try:
            # Get content types for embedding search
            content_types = None
            if filters.get('content_type'):
                content_types = filters['content_type']
                if isinstance(content_types, str):
                    content_types = [content_types]
            
            # Perform similarity search
            similar_content = self.embedding_service.similarity_search(
                query_text=query_text,
                encounter_id=filters.get('encounter_id'),
                content_types=content_types,
                limit=limit,
                threshold=0.5  # Lower threshold for broader results
            )
            
            # Format results to match FTS format
            formatted_results = []
            for item in similar_content:
                # Get the corresponding searchable content
                try:
                    searchable_content = SearchableContent.objects.get(
                        content_type=item['content_type'],
                        content_id=item['content_id']
                    )
                    
                    formatted_results.append({
                        'id': searchable_content.id,
                        'encounter_id': item['encounter_id'],
                        'content_type': item['content_type'],
                        'content_id': item['content_id'],
                        'title': searchable_content.title,
                        'content': item['text_content'],
                        'snippet': self._generate_snippet(item['text_content'], query_text),
                        'score': item['similarity_score'],
                        'search_type': 'semantic',
                        'metadata': searchable_content.metadata,
                        'created_at': item['created_at']
                    })
                
                except SearchableContent.DoesNotExist:
                    # Skip if searchable content not found
                    continue
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            return []
    
    def _combine_search_results(self, fts_results: List[Dict], semantic_results: List[Dict], 
                               query_text: str, limit: int) -> List[Dict[str, Any]]:
        """Combine and rank results from both search methods."""
        # Create a dictionary to track unique results
        combined_dict = {}
        
        # Add FTS results
        for result in fts_results:
            key = f"{result['content_type']}:{result['content_id']}"
            result['combined_score'] = result['score'] * self.fts_weight
            combined_dict[key] = result
        
        # Add semantic results (merge if already exists)
        for result in semantic_results:
            key = f"{result['content_type']}:{result['content_id']}"
            
            if key in combined_dict:
                # Combine scores
                existing = combined_dict[key]
                semantic_score = result['score'] * self.semantic_weight
                existing['combined_score'] += semantic_score
                existing['search_type'] = 'hybrid'
                
                # Use better snippet if semantic search provides more context
                if len(result['snippet']) > len(existing['snippet']):
                    existing['snippet'] = result['snippet']
            else:
                # Add as new result
                result['combined_score'] = result['score'] * self.semantic_weight
                combined_dict[key] = result
        
        # Convert back to list and sort by combined score
        combined_results = list(combined_dict.values())
        combined_results.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return combined_results[:limit]
    
    def _generate_snippet(self, content: str, query_text: str, max_length: int = 200) -> str:
        """Generate a snippet highlighting the query terms."""
        if not content or not query_text:
            return content[:max_length] if content else ""
        
        # Simple snippet generation - find first occurrence of query terms
        content_lower = content.lower()
        query_terms = query_text.lower().split()
        
        best_position = 0
        best_score = 0
        
        # Find position with most query terms
        for i in range(0, len(content) - max_length, 20):
            chunk = content_lower[i:i + max_length]
            score = sum(1 for term in query_terms if term in chunk)
            
            if score > best_score:
                best_score = score
                best_position = i
        
        # Extract snippet
        snippet = content[best_position:best_position + max_length]
        
        # Add ellipsis if needed
        if best_position > 0:
            snippet = "..." + snippet
        if best_position + max_length < len(content):
            snippet = snippet + "..."
        
        return snippet.strip()
    
    def _cache_search_results(self, search_query_obj: SearchQueryModel, results: List[Dict]):
        """Cache search results for future use."""
        try:
            # Clear existing cached results
            SearchResult.objects.filter(query=search_query_obj).delete()
            
            # Create new cached results
            cached_results = []
            for rank, result in enumerate(results, 1):
                try:
                    searchable_content = SearchableContent.objects.get(
                        id=result['id']
                    )
                    
                    cached_results.append(SearchResult(
                        query=search_query_obj,
                        content=searchable_content,
                        relevance_score=result['combined_score'],
                        rank=rank,
                        snippet=result['snippet']
                    ))
                
                except SearchableContent.DoesNotExist:
                    continue
            
            # Bulk create cached results
            if cached_results:
                SearchResult.objects.bulk_create(cached_results)
        
        except Exception as e:
            logger.error(f"Failed to cache search results: {str(e)}")
    
    def index_content(self, encounter_id: int, content_type: str, content_id: int, 
                     title: str, content: str, metadata: Optional[Dict] = None) -> SearchableContent:
        """
        Index content for search.
        
        Args:
            encounter_id: ID of the encounter
            content_type: Type of content
            content_id: ID of the content object
            title: Title of the content
            content: Content text
            metadata: Optional metadata
        
        Returns:
            SearchableContent object
        """
        try:
            searchable_content, created = SearchableContent.objects.update_or_create(
                content_type=content_type,
                content_id=content_id,
                defaults={
                    'encounter_id': encounter_id,
                    'title': title,
                    'content': content,
                    'metadata': metadata or {}
                }
            )
            
            # Update search vector
            search_vector = SearchVector('title', weight='A') + SearchVector('content', weight='B')
            SearchableContent.objects.filter(id=searchable_content.id).update(
                search_vector=search_vector
            )
            
            logger.info(f"{'Created' if created else 'Updated'} searchable content for {content_type}:{content_id}")
            return searchable_content
        
        except Exception as e:
            logger.error(f"Failed to index content: {str(e)}")
            raise
    
    def reindex_encounter(self, encounter_id: int) -> Dict[str, int]:
        """
        Reindex all content for an encounter.
        
        Args:
            encounter_id: ID of the encounter to reindex
        
        Returns:
            Dict with counts of indexed content by type
        """
        from encounters.models import Encounter
        
        try:
            encounter = Encounter.objects.get(id=encounter_id)
        except Encounter.DoesNotExist:
            raise ValueError(f"Encounter {encounter_id} not found")
        
        results = {
            'transcript': 0,
            'soap': 0,
            'checklist': 0,
            'notes': 0
        }
        
        # Index transcript segments
        for segment in encounter.transcript_segments.all():
            if segment.text and len(segment.text.strip()) > 10:
                self.index_content(
                    encounter_id=encounter_id,
                    content_type='transcript',
                    content_id=segment.id,
                    title=f"Transcript Segment {segment.id}",
                    content=segment.text,
                    metadata={
                        'start_time': segment.start_time,
                        'end_time': segment.end_time,
                        'speaker': getattr(segment, 'speaker', None)
                    }
                )
                results['transcript'] += 1
        
        # Index SOAP drafts and final
        for draft in encounter.soap_drafts.all():
            if draft.content:
                combined_content = self._combine_soap_sections(draft.content)
                if combined_content:
                    self.index_content(
                        encounter_id=encounter_id,
                        content_type='soap',
                        content_id=draft.id,
                        title=f"SOAP Draft {draft.id}",
                        content=combined_content,
                        metadata={
                            'version': draft.version,
                            'is_final': False
                        }
                    )
                    results['soap'] += 1
        
        # Index final artifacts
        if hasattr(encounter, 'final_artifacts') and encounter.final_artifacts:
            artifacts = encounter.final_artifacts
            if artifacts.soap_content:
                combined_content = self._combine_soap_sections(artifacts.soap_content)
                if combined_content:
                    self.index_content(
                        encounter_id=encounter_id,
                        content_type='soap',
                        content_id=artifacts.id,
                        title=f"Final SOAP - Encounter {encounter_id}",
                        content=combined_content,
                        metadata={
                            'is_final': True,
                            'exported_at': artifacts.created_at.isoformat() if artifacts.created_at else None
                        }
                    )
                    results['soap'] += 1
        
        # Index checklist evaluations
        for eval_obj in encounter.checklist_evals.all():
            if eval_obj.evidence_text:
                self.index_content(
                    encounter_id=encounter_id,
                    content_type='checklist',
                    content_id=eval_obj.id,
                    title=f"Checklist: {eval_obj.catalog_item.title}",
                    content=eval_obj.evidence_text,
                    metadata={
                        'status': eval_obj.status,
                        'confidence_score': eval_obj.confidence_score,
                        'category': eval_obj.catalog_item.category
                    }
                )
                results['checklist'] += 1
        
        logger.info(f"Reindexed encounter {encounter_id}: {results}")
        return results
    
    def _combine_soap_sections(self, soap_content: Dict[str, Any]) -> str:
        """Combine SOAP sections into searchable text."""
        sections = []
        
        for section_name, section_data in soap_content.items():
            if isinstance(section_data, dict) and 'content' in section_data:
                sections.append(f"{section_name.upper()}:\\n{section_data['content']}")
            elif isinstance(section_data, str):
                sections.append(f"{section_name.upper()}:\\n{section_data}")
        
        return "\\n\\n".join(sections)
    
    def get_search_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get search analytics for the specified number of days.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dict with analytics data
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        queries = SearchQueryModel.objects.filter(created_at__gte=cutoff_date)
        
        total_searches = queries.count()
        avg_execution_time = queries.aggregate(
            avg_time=models.Avg('execution_time_ms')
        )['avg_time'] or 0
        
        # Top queries
        top_queries = queries.values('query_text').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]
        
        # Search patterns by content type
        content_type_stats = {}
        for query in queries:
            filters = query.filters
            content_types = filters.get('content_type', ['all'])
            if isinstance(content_types, str):
                content_types = [content_types]
            
            for content_type in content_types:
                content_type_stats[content_type] = content_type_stats.get(content_type, 0) + 1
        
        return {
            'total_searches': total_searches,
            'avg_execution_time_ms': round(avg_execution_time, 2),
            'top_queries': list(top_queries),
            'content_type_distribution': content_type_stats,
            'period_days': days
        }