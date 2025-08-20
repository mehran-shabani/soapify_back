"""
Embeddings models for SOAPify.
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField


class TextEmbedding(models.Model):
    """Store text embeddings for semantic search."""
    
    CONTENT_TYPE_CHOICES = [
        ('transcript', 'Transcript Segment'),
        ('soap_draft', 'SOAP Draft'),
        ('soap_final', 'SOAP Final'),
        ('notes', 'Clinical Notes'),
        ('checklist', 'Checklist Item'),
    ]
    
    encounter = models.ForeignKey('encounters.Encounter', on_delete=models.CASCADE, related_name='embeddings')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    content_id = models.PositiveIntegerField(help_text="ID of the related content object")
    text_content = models.TextField(help_text="Original text that was embedded")
    embedding_vector = ArrayField(
        models.FloatField(),
        size=1536,  # OpenAI text-embedding-ada-002 dimension
        help_text="Vector embedding of the text"
    )
    model_name = models.CharField(max_length=50, default='text-embedding-ada-002')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['encounter', 'content_type']),
            models.Index(fields=['content_type', 'content_id']),
            models.Index(fields=['created_at']),
        ]
        unique_together = ['content_type', 'content_id']
    
    def __str__(self):
        return f"{self.content_type}:{self.content_id} - {self.text_content[:50]}..."
    
    @property
    def vector_dimension(self):
        """Get the dimension of the embedding vector."""
        return len(self.embedding_vector) if self.embedding_vector else 0


# Backwards-compatible aliases for tests
class EmbeddingVector(TextEmbedding):
    class Meta:
        proxy = True


class EmbeddingIndex(models.Model):
    """Index for managing embedding collections and metadata."""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    model_name = models.CharField(max_length=50)
    dimension = models.PositiveIntegerField()
    total_embeddings = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.total_embeddings} embeddings)"


class EmbeddingCollection(EmbeddingIndex):
    class Meta:
        proxy = True


class SimilaritySearch(models.Model):
    """Store similarity search results for caching."""
    
    query_text = models.TextField()
    query_embedding = ArrayField(
        models.FloatField(),
        size=1536,
        help_text="Embedding vector of the search query"
    )
    encounter = models.ForeignKey('encounters.Encounter', on_delete=models.CASCADE, null=True, blank=True)
    results = models.JSONField(help_text="Cached search results")
    similarity_threshold = models.FloatField(default=0.7)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['encounter', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Search: {self.query_text[:50]}..."