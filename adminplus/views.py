"""
Admin Plus views for SOAPify.
"""
import json
from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Count, Avg
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import SystemHealth, TaskMonitor, OperationLog
from .services import AdminService


def is_admin_user(user):
    """Check if user is admin."""
    return user.is_authenticated and user.is_staff


@user_passes_test(is_admin_user)
def dashboard(request):
    """Admin dashboard view."""
    # Get system health summary
    health_summary = SystemHealth.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Get recent tasks
    recent_tasks = TaskMonitor.objects.select_related().order_by('-created_at')[:10]
    
    # Get task statistics
    task_stats = TaskMonitor.objects.filter(
        created_at__gte=datetime.now() - timedelta(hours=24)
    ).values('status').annotate(count=Count('id'))
    
    # Get recent operations
    recent_operations = OperationLog.objects.select_related('user').order_by('-created_at')[:10]
    
    context = {
        'health_summary': health_summary,
        'recent_tasks': recent_tasks,
        'task_stats': task_stats,
        'recent_operations': recent_operations,
    }
    
    return render(request, 'adminplus/dashboard.html', context)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def system_health(request):
    """Get system health status."""
    admin_service = AdminService()
    health_data = admin_service.check_system_health()
    
    return Response(health_data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def task_monitor(request):
    """Get task monitoring data."""
    # Query parameters
    status_filter = request.GET.get('status')
    task_name_filter = request.GET.get('task_name')
    hours = int(request.GET.get('hours', 24))
    
    # Build queryset
    queryset = TaskMonitor.objects.all()
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if task_name_filter:
        queryset = queryset.filter(task_name__icontains=task_name_filter)
    
    if hours:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        queryset = queryset.filter(created_at__gte=cutoff_time)
    
    # Pagination
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 50)), 200)
    
    paginator = Paginator(queryset.order_by('-created_at'), page_size)
    page_obj = paginator.get_page(page)
    
    # Serialize data
    tasks_data = []
    for task in page_obj:
        tasks_data.append({
            'id': task.id,
            'task_id': task.task_id,
            'task_name': task.task_name,
            'status': task.status,
            'args': task.args,
            'kwargs': task.kwargs,
            'result': task.result,
            'runtime': task.runtime,
            'retries': task.retries,
            'max_retries': task.max_retries,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'traceback': task.traceback if task.status == 'failure' else None
        })
    
    return Response({
        'tasks': tasks_data,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_tasks': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def retry_task(request):
    """Retry a failed task."""
    task_id = request.data.get('task_id')
    
    if not task_id:
        return Response(
            {'error': 'task_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        task_monitor = get_object_or_404(TaskMonitor, task_id=task_id)
        
        if task_monitor.status not in ['failure', 'retry']:
            return Response(
                {'error': 'Task is not in a retryable state'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        admin_service = AdminService()
        result = admin_service.retry_task(task_id)
        
        # Log the operation
        OperationLog.objects.create(
            user=request.user,
            action='task_retry',
            description=f'Retried task {task_monitor.task_name}',
            target_object='TaskMonitor',
            target_id=task_monitor.id,
            metadata={'original_task_id': task_id},
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'message': 'Task retry initiated',
            'new_task_id': result.get('new_task_id'),
            'status': result.get('status')
        })
    
    except Exception as e:
        return Response(
            {'error': f'Failed to retry task: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def cancel_task(request):
    """Cancel a running task."""
    task_id = request.data.get('task_id')
    
    if not task_id:
        return Response(
            {'error': 'task_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        task_monitor = get_object_or_404(TaskMonitor, task_id=task_id)
        
        if task_monitor.status not in ['pending', 'started']:
            return Response(
                {'error': 'Task is not in a cancellable state'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        admin_service = AdminService()
        result = admin_service.cancel_task(task_id)
        
        # Log the operation
        OperationLog.objects.create(
            user=request.user,
            action='task_cancel',
            description=f'Cancelled task {task_monitor.task_name}',
            target_object='TaskMonitor',
            target_id=task_monitor.id,
            metadata={'task_id': task_id},
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'message': 'Task cancellation initiated',
            'status': result.get('status')
        })
    
    except Exception as e:
        return Response(
            {'error': f'Failed to cancel task: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def task_statistics(request):
    """Get task execution statistics."""
    admin_service = AdminService()
    stats = admin_service.get_task_statistics()
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def operation_logs(request):
    """Get operation logs."""
    # Query parameters
    action_filter = request.GET.get('action')
    user_filter = request.GET.get('user')
    days = int(request.GET.get('days', 7))
    
    # Build queryset
    queryset = OperationLog.objects.select_related('user')
    
    if action_filter:
        queryset = queryset.filter(action=action_filter)
    
    if user_filter:
        queryset = queryset.filter(user__username__icontains=user_filter)
    
    if days:
        cutoff_date = datetime.now() - timedelta(days=days)
        queryset = queryset.filter(created_at__gte=cutoff_date)
    
    # Pagination
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 50)), 200)
    
    paginator = Paginator(queryset.order_by('-created_at'), page_size)
    page_obj = paginator.get_page(page)
    
    # Serialize data
    logs_data = []
    for log in page_obj:
        logs_data.append({
            'id': log.id,
            'user': log.user.username,
            'action': log.action,
            'description': log.description,
            'target_object': log.target_object,
            'target_id': log.target_id,
            'metadata': log.metadata,
            'ip_address': log.ip_address,
            'created_at': log.created_at
        })
    
    return Response({
        'logs': logs_data,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_logs': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def export_data(request):
    """Export system data."""
    export_type = request.data.get('export_type')
    date_from = request.data.get('date_from')
    date_to = request.data.get('date_to')
    
    if not export_type:
        return Response(
            {'error': 'export_type is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    valid_types = ['encounters', 'tasks', 'logs', 'health']
    if export_type not in valid_types:
        return Response(
            {'error': f'Invalid export_type. Valid options: {valid_types}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        admin_service = AdminService()
        export_result = admin_service.export_data(
            export_type=export_type,
            date_from=date_from,
            date_to=date_to,
            user=request.user
        )
        
        # Log the operation
        OperationLog.objects.create(
            user=request.user,
            action='data_export',
            description=f'Exported {export_type} data',
            metadata={
                'export_type': export_type,
                'date_from': date_from,
                'date_to': date_to,
                'record_count': export_result.get('record_count', 0)
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'message': 'Export completed successfully',
            'download_url': export_result.get('download_url'),
            'record_count': export_result.get('record_count'),
            'file_size': export_result.get('file_size')
        })
    
    except Exception as e:
        return Response(
            {'error': f'Export failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )