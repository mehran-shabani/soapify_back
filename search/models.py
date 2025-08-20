"""
Search models for SOAPify.
"""
from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class SearchableContent(models.Model):
    """Searchable content index for full-text search."""
    
    CONTENT_TYPE_CHOICES = [
        ('encounter', 'Encounter'),
        ('transcript', 'Transcript'),
        ('soap', 'SOAP Note'),
        ('checklist', 'Checklist'),
        ('notes', 'Clinical Notes'),
    ]
    
    encounter = models.ForeignKey('encounters.Encounter', on_delete=models.CASCADE, related_name='search_content')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    content_id = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    content = models.TextField()
    search_vector = SearchVectorField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            GinIndex(fields=['search_vector']),
            models.Index(fields=['encounter', 'content_type']),
            models.Index(fields=['content_type', 'content_id']),
            models.Index(fields=['created_at']),
        ]
        unique_together = ['content_type', 'content_id']
    
    def __str__(self):
        return f"{self.content_type}:{self.content_id} - {self.title}"


class SearchQuery(models.Model):
    """Store search queries for analytics and caching."""
    
    query_text = models.TextField()
    filters = models.JSONField(default=dict)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    results_count = models.PositiveIntegerField(default=0)
    execution_time_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Search: {self.query_text[:50]}..."


class SearchResult(models.Model):
    """Cached search results."""
    
    query = models.ForeignKey(SearchQuery, on_delete=models.CASCADE, related_name='cached_results')
    content = models.ForeignKey(SearchableContent, on_delete=models.CASCADE)
    relevance_score = models.FloatField()
    rank = models.PositiveIntegerField()
    snippet = models.TextField()
    
    class Meta:
        indexes = [
            models.Index(fields=['query', 'rank']),
            models.Index(fields=['relevance_score']),
        ]
        unique_together = ['query', 'content']
        ordering = ['rank']
    
    def __str__(self):
        return f"Result {self.rank} for query {self.query.id}"