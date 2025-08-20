"""
Admin configuration for checklist app.
"""
from django.contrib import admin
from .models import ChecklistCatalog, ChecklistEval, ChecklistTemplate, ChecklistTemplateItem


@admin.register(ChecklistCatalog)
class ChecklistCatalogAdmin(admin.ModelAdmin):
    """Admin interface for ChecklistCatalog."""
    
    list_display = ['title', 'category', 'priority', 'is_active', 'created_at']
    list_filter = ['category', 'priority', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'keywords']
    ordering = ['category', 'priority', 'title']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'category', 'priority', 'is_active')
        }),
        ('Evaluation Settings', {
            'fields': ('keywords', 'question_template'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System-generated fields'
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        """Set created_by field when saving."""
        if not change:  # Only set on create
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ChecklistEval)
class ChecklistEvalAdmin(admin.ModelAdmin):
    """Admin interface for ChecklistEval."""
    
    list_display = ['encounter', 'catalog_item', 'status', 'confidence_score', 'created_at']
    list_filter = ['status', 'catalog_item__category', 'catalog_item__priority', 'created_at']
    search_fields = ['encounter__id', 'catalog_item__title', 'evidence_text']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('encounter', 'catalog_item', 'status', 'confidence_score')
        }),
        ('Evidence', {
            'fields': ('evidence_text', 'anchor_positions', 'generated_question'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('encounter', 'catalog_item')


class ChecklistTemplateItemInline(admin.TabularInline):
    """Inline admin for ChecklistTemplateItem."""
    
    model = ChecklistTemplateItem
    extra = 0
    fields = ['catalog_item', 'order', 'is_required']
    ordering = ['order']


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    """Admin interface for ChecklistTemplate."""
    
    list_display = ['name', 'specialty', 'is_default', 'catalog_items_count', 'created_at']
    list_filter = ['specialty', 'is_default', 'created_at']
    search_fields = ['name', 'description', 'specialty']
    ordering = ['name']
    
    inlines = [ChecklistTemplateItemInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'specialty', 'is_default')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def catalog_items_count(self, obj):
        """Get count of catalog items in template."""
        return obj.catalog_items.count()
    catalog_items_count.short_description = 'Items Count'
    
    def save_model(self, request, obj, form, change):
        """Set created_by field when saving."""
        if not change:  # Only set on create
            obj.created_by = request.user
        super().save_model(request, obj, form, change)