"""
Admin interface for NLP app.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import SOAPDraft, ChecklistItem, ExtractionLog


@admin.register(SOAPDraft)
class SOAPDraftAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'encounter', 'patient_ref', 'status', 'completion_percentage',
        'confidence_score', 'created_at'
    ]
    list_filter = ['status', 'extraction_version', 'created_at']
    search_fields = ['encounter__patient_ref', 'encounter__doctor__username']
    readonly_fields = ['created_at', 'updated_at', 'completion_percentage']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('encounter', 'status', 'extraction_version')
        }),
        ('SOAP Data', {
            'fields': ('soap_data', 'confidence_score', 'completion_percentage'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'reviewed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def patient_ref(self, obj):
        return obj.encounter.patient_ref
    patient_ref.short_description = 'Patient Ref'
    
    def completion_percentage(self, obj):
        percentage = obj.completion_percentage
        color = 'green' if percentage >= 80 else 'orange' if percentage >= 60 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            f"{percentage}%"
        )
    completion_percentage.short_description = 'Completion'


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'soap_draft', 'title', 'section', 'item_type',
        'status_colored', 'weight', 'confidence', 'is_critical'
    ]
    list_filter = ['section', 'item_type', 'status', 'weight']
    search_fields = ['title', 'description', 'soap_draft__encounter__patient_ref']
    readonly_fields = ['created_at', 'updated_at', 'is_critical', 'completion_score']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('soap_draft', 'item_id', 'title', 'description')
        }),
        ('Classification', {
            'fields': ('section', 'item_type', 'weight', 'is_critical')
        }),
        ('Status', {
            'fields': ('status', 'confidence', 'notes', 'completion_score')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_colored(self, obj):
        colors = {
            'complete': 'green',
            'partial': 'orange', 
            'missing': 'red',
            'not_applicable': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'


@admin.register(ExtractionLog)
class ExtractionLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'soap_draft', 'model_used', 'success_colored',
        'processing_time_seconds', 'tokens_used', 'created_at'
    ]
    list_filter = ['model_used', 'success', 'created_at']
    search_fields = ['soap_draft__encounter__patient_ref', 'error_message']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('soap_draft', 'model_used', 'prompt_version')
        }),
        ('Processing Details', {
            'fields': (
                'input_text_length', 'output_json_length',
                'processing_time_seconds', 'tokens_used'
            )
        }),
        ('Results', {
            'fields': ('success', 'error_message')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def success_colored(self, obj):
        color = 'green' if obj.success else 'red'
        text = 'Success' if obj.success else 'Failed'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            text
        )
    success_colored.short_description = 'Result'
