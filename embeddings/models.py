# embeddings/models.py
"""
Embeddings models for SOAPify (MySQL + JSON embeddings).
"""
from __future__ import annotations

from django.db import models
from django.core.exceptions import ValidationError

EMBED_DIM = 1536  # ابعاد امبدینگ شما

def validate_embedding_list(value):
    # انتظار: list[float] با طول دقیق EMBED_DIM
    if not isinstance(value, list):
        raise ValidationError("Embedding must be a JSON array (list).")
    if len(value) != EMBED_DIM:
        raise ValidationError(f"Embedding length must be {EMBED_DIM}, got {len(value)}.")
    for i, x in enumerate(value):
        if not isinstance(x, (int, float)):
            raise ValidationError(f"Embedding items must be numbers (index {i} is {type(x).__name__}).")

class TextEmbedding(models.Model):
    """Store text embeddings for semantic search (JSON-based for MySQL)."""

    CONTENT_TYPE_CHOICES = [
        ("transcript", "Transcript Segment"),
        ("soap_draft", "SOAP Draft"),
        ("soap_final", "SOAP Final"),
        ("notes", "Clinical Notes"),
        ("checklist", "Checklist Item"),
    ]

    encounter = models.ForeignKey(
        "encounters.Encounter",
        on_delete=models.CASCADE,
        related_name="embeddings",
    )
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    content_id = models.PositiveIntegerField(help_text="ID of the related content object")
    text_content = models.TextField(help_text="Original text that was embedded")

    # JSONField به‌جای VectorField
    embedding_vector = models.JSONField(
        help_text=f"Embedding vector as JSON array (length = {EMBED_DIM})",
        validators=[validate_embedding_list],
    )

    model_name = models.CharField(max_length=50, default="text-embedding-3-small")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["encounter", "content_type"]),
            models.Index(fields=["content_type", "content_id"]),
            models.Index(fields=["created_at"]),
        ]
        # پیشنهاد: یونیک سه‌تایی برای جلوگیری از تداخل id بین encounterها
        constraints = [
            models.UniqueConstraint(
                fields=["encounter", "content_type", "content_id"],
                name="uniq_encounter_contenttype_contentid",
            ),
        ]

    def __str__(self):
        head = (self.text_content or "")[:50].replace("\n", " ")
        return f"{self.content_type}:{self.content_id} - {head}..."

    @property
    def vector_dimension(self) -> int:
        return EMBED_DIM


class EmbeddingVector(TextEmbedding):
    """Backwards-compatible alias for tests."""
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
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.total_embeddings} embeddings)"


class EmbeddingCollection(EmbeddingIndex):
    class Meta:
        proxy = True


class SimilaritySearch(models.Model):
    """Store similarity search results for caching."""

    query_text = models.TextField()
    query_embedding = models.JSONField(
        help_text=f"Embedding vector of the query (JSON array length = {EMBED_DIM})",
        validators=[validate_embedding_list],
    )
    encounter = models.ForeignKey("encounters.Encounter", on_delete=models.CASCADE, null=True, blank=True)
    results = models.JSONField(help_text="Cached search results")
    similarity_threshold = models.FloatField(default=0.7)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["encounter", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Search: {self.query_text[:50]}..."