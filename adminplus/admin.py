"""
Admin configuration for adminplus app.
"""
from django.contrib import admin
from .models import SystemHealth, TaskMonitor, OperationLog


@admin.register(SystemHealth)
class SystemHealthAdmin(admin.ModelAdmin):
    """Admin interface for SystemHealth."""
    
    list_display = ['component', 'status', 'message_preview', 'checked_at']
    list_filter = ['component', 'status', 'checked_at']
    search_fields = ['component', 'message']
    ordering = ['-checked_at']
    
    fieldsets = (
        (None, {
            'fields': ('component', 'status', 'message')
        }),
        ('Metrics', {
            'fields': ('metrics',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('checked_at',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['checked_at']
    
    def message_preview(self, obj):
        """Get preview of message."""
        return obj.message[:100] + "..." if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'
    
    actions = ['mark_as_resolved']
    
    def mark_as_resolved(self, request, queryset):
        """Mark health issues as resolved (for display purposes)."""
        # This is just for admin convenience - doesn't change actual status
        self.message_user(request, f"Marked {queryset.count()} health records as viewed.")
    mark_as_resolved.short_description = "Mark as viewed"


@admin.register(TaskMonitor)
class TaskMonitorAdmin(admin.ModelAdmin):
    """Admin interface for TaskMonitor."""
    
    list_display = ['task_id_short', 'task_name', 'status', 'runtime', 'retries', 'created_at']
    list_filter = ['task_name', 'status', 'created_at']
    search_fields = ['task_id', 'task_name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('task_id', 'task_name', 'status')
        }),
        ('Parameters', {
            'fields': ('args', 'kwargs'),
            'classes': ('collapse',)
        }),
        ('Execution', {
            'fields': ('runtime', 'retries', 'max_retries', 'started_at', 'completed_at')
        }),
        ('Result', {
            'fields': ('result', 'traceback'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at']
    
    def task_id_short(self, obj):
        """Get shortened task ID for display."""
        return f"{obj.task_id[:8]}..." if len(obj.task_id) > 8 else obj.task_id
    task_id_short.short_description = 'Task ID'
    
    actions = ['retry_failed_tasks']
    
    def retry_failed_tasks(self, request, queryset):
        """Retry selected failed tasks."""
        from .services import AdminService
        
        admin_service = AdminService()
        success_count = 0
        
        for task in queryset.filter(status='failure'):
            try:
                admin_service.retry_task(task.task_id)
                success_count += 1
            except Exception:
                continue
        
        self.message_user(request, f"Retried {success_count} tasks.")
    retry_failed_tasks.short_description = "Retry selected failed tasks"


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    """Admin interface for OperationLog."""
    
    list_display = ['user', 'action', 'description_preview', 'target_object', 'created_at']
    list_filter = ['action', 'target_object', 'created_at']
    search_fields = ['user__username', 'description', 'target_object']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'action', 'description')
        }),
        ('Target', {
            'fields': ('target_object', 'target_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at']
    
    def description_preview(self, obj):
        """Get preview of description."""
        return obj.description[:100] + "..." if len(obj.description) > 100 else obj.description
    description_preview.short_description = 'Description'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user')