# search/models.py
"""
Search models for SOAPify (MySQL/MariaDB + FULLTEXT).
"""
from __future__ import annotations

import json
from django.db import models


class SearchableContent(models.Model):
    """Searchable content index for FULLTEXT search (MySQL)."""

    CONTENT_TYPE_CHOICES = [
        ("encounter", "Encounter"),
        ("transcript", "Transcript"),
        ("soap", "SOAP Note"),
        ("checklist", "Checklist"),
        ("notes", "Clinical Notes"),
    ]

    encounter = models.ForeignKey(
        "encounters.Encounter",
        on_delete=models.CASCADE,
        related_name="search_content",
    )
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    content_id = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    content = models.TextField()

    # به‌جای SearchVectorField (Postgres)، متن کمکی برای ایندکس
    search_vector = models.TextField(null=True, blank=True)

    metadata = models.JSONField(default=dict)
    metadata_text = models.TextField(blank=True, default="")

    # ستون fulltext_all را در مایگریشن به‌صورت Generated می‌سازیم
    # fulltext_all = models.TextField(editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["encounter", "content_type"]),
            models.Index(fields=["content_type", "content_id"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["encounter", "content_type", "content_id"],
                name="uniq_search_encounter_contenttype_contentid",
            ),
        ]

    def __str__(self):
        return f"{self.content_type}:{self.content_id} - {self.title}"

    def save(self, *args, **kwargs):
        # JSON → متن برای FULLTEXT
        try:
            self.metadata_text = json.dumps(self.metadata, ensure_ascii=False, separators=(", ", ": "))
        except Exception:
            self.metadata_text = ""
        super().save(*args, **kwargs)


class SearchQuery(models.Model):
    """Store search queries for analytics and caching."""

    query_text = models.TextField()
    filters = models.JSONField(default=dict)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    results_count = models.PositiveIntegerField(default=0)
    execution_time_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Search: {self.query_text[:50]}..."


class SearchResult(models.Model):
    """Cached search results."""

    query = models.ForeignKey(
        SearchQuery, on_delete=models.CASCADE, related_name="cached_results"
    )
    content = models.ForeignKey(SearchableContent, on_delete=models.CASCADE)
    relevance_score = models.FloatField()
    rank = models.PositiveIntegerField()
    snippet = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=["query", "rank"]),
            models.Index(fields=["relevance_score"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["query", "content"], name="uniq_query_content"
            ),
        ]
        ordering = ["rank"]

    def __str__(self):
        return f"Result {self.rank} for query {self.query.id}"