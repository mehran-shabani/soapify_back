"""
Admin configuration for embeddings app.
"""
from django.contrib import admin
from .models import SimilaritySearch, TextEmbedding, EmbeddingIndex


@admin.register(TextEmbedding)
class TextEmbeddingAdmin(admin.ModelAdmin):
    """Admin interface for TextEmbedding."""
    
    list_display = ['id', 'encounter', 'content_type', 'content_id', 'model_name', 'vector_dimension', 'created_at']
    list_filter = ['content_type', 'model_name', 'created_at']
    search_fields = ['encounter__id', 'text_content']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('encounter', 'content_type', 'content_id', 'model_name')
        }),
        ('Content', {
            'fields': ('text_content',),
            'classes': ('collapse',)
        }),
        ('Vector Data', {
            'fields': ('embedding_vector',),
            'classes': ('collapse',),
            'description': 'Vector embedding data (read-only for security)'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at', 'embedding_vector']
    
    def vector_dimension(self, obj):
        """Get vector dimension for display."""
        return obj.vector_dimension
    vector_dimension.short_description = 'Vector Dim'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('encounter')


@admin.register(EmbeddingIndex)
class EmbeddingIndexAdmin(admin.ModelAdmin):
    """Admin interface for EmbeddingIndex."""
    
    list_display = ['name', 'model_name', 'dimension', 'total_embeddings', 'is_active', 'last_updated']
    list_filter = ['model_name', 'is_active', 'last_updated']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Configuration', {
            'fields': ('model_name', 'dimension')
        }),
        ('Statistics', {
            'fields': ('total_embeddings', 'last_updated'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['last_updated']
    
    actions = ['update_statistics', 'activate_indexes', 'deactivate_indexes']
    
    def update_statistics(self, request, queryset):
        """Update statistics for selected indexes."""
        from .tasks import update_embedding_index_stats
        
        # Trigger async task
        update_embedding_index_stats.delay()
        
        self.message_user(request, "Statistics update task has been queued.")
    update_statistics.short_description = "Update statistics"
    
    def activate_indexes(self, request, queryset):
        """Activate selected indexes."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} indexes.")
    activate_indexes.short_description = "Activate selected indexes"
    
    def deactivate_indexes(self, request, queryset):
        """Deactivate selected indexes."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} indexes.")
    deactivate_indexes.short_description = "Deactivate selected indexes"


@admin.register(SimilaritySearch)
class SimilaritySearchAdmin(admin.ModelAdmin):
    """Admin interface for SimilaritySearch."""
    
    list_display = ['id', 'query_text_short', 'encounter', 'similarity_threshold', 'results_count', 'created_at']
    list_filter = ['similarity_threshold', 'created_at']
    search_fields = ['query_text']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('query_text', 'encounter', 'similarity_threshold')
        }),
        ('Results', {
            'fields': ('results',),
            'classes': ('collapse',)
        }),
        ('Vector Data', {
            'fields': ('query_embedding',),
            'classes': ('collapse',),
            'description': 'Query embedding vector (read-only)'
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'query_embedding']
    
    def query_text_short(self, obj):
        """Get shortened query text for display."""
        return obj.query_text[:50] + "..." if len(obj.query_text) > 50 else obj.query_text
    query_text_short.short_description = 'Query'
    
    def results_count(self, obj):
        """Get count of results."""
        if isinstance(obj.results, list):
            return len(obj.results)
        return 0
    results_count.short_description = 'Results Count'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('encounter')