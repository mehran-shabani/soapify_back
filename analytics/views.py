"""
Analytics views for SOAPify.
"""
from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.utils import timezone
from django.utils.dateparse import parse_date

from .services import AnalyticsService


@api_view(['GET'])
@permission_classes([IsAdminUser])
def system_overview(request):
    """Get system overview metrics."""
    try:
        analytics_service = AnalyticsService()
        overview = analytics_service.get_system_overview()
        
        return Response(overview)
    
    except Exception as e:
        return Response(
            {'error': f'Failed to get system overview: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def user_analytics(request):
    """
    Get user analytics.
    
    Query parameters:
    - user_id: Specific user ID (optional)
    - days: Number of days to analyze (default: 30)
    """
    user_id = request.GET.get('user_id')
    days = int(request.GET.get('days', 30))
    
    if days < 1 or days > 365:
        return Response(
            {'error': 'Days parameter must be between 1 and 365'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if user_id:
        try:
            user_id = int(user_id)
        except ValueError:
            return Response(
                {'error': 'Invalid user_id format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    try:
        analytics_service = AnalyticsService()
        analytics = analytics_service.get_user_analytics(user_id=user_id, days=days)
        
        return Response(analytics)
    
    except Exception as e:
        return Response(
            {'error': f'Failed to get user analytics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def performance_analytics(request):
    """
    Get API performance analytics.
    
    Query parameters:
    - days: Number of days to analyze (default: 7)
    """
    days = int(request.GET.get('days', 7))
    
    if days < 1 or days > 90:
        return Response(
            {'error': 'Days parameter must be between 1 and 90'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        analytics_service = AnalyticsService()
        analytics = analytics_service.get_performance_analytics(days=days)
        
        return Response(analytics)
    
    except Exception as e:
        return Response(
            {'error': f'Failed to get performance analytics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def calculate_business_metrics(request):
    """
    Calculate business metrics for a specific period.
    
    Body parameters:
    - date_from: Start date (YYYY-MM-DD)
    - date_to: End date (YYYY-MM-DD)
    """
    date_from = request.data.get('date_from')
    date_to = request.data.get('date_to')
    
    if not date_from or not date_to:
        return Response(
            {'error': 'date_from and date_to are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        period_start = parse_date(date_from)
        period_end = parse_date(date_to)
        
        if not period_start or not period_end:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if period_start >= period_end:
            return Response(
                {'error': 'date_from must be before date_to'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert to datetime objects
        period_start = timezone.make_aware(datetime.combine(period_start, datetime.min.time()))
        period_end = timezone.make_aware(datetime.combine(period_end, datetime.max.time()))
        
        analytics_service = AnalyticsService()
        metrics = analytics_service.calculate_business_metrics(period_start, period_end)
        
        return Response({
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'metrics': metrics
        })
    
    except Exception as e:
        return Response(
            {'error': f'Failed to calculate business metrics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_activity(request):
    """
    Record user activity.
    
    Body parameters:
    - action: Action name (required)
    - resource: Resource name (optional)
    - resource_id: Resource ID (optional)
    - metadata: Additional metadata (optional)
    """
    action = request.data.get('action')
    
    if not action:
        return Response(
            {'error': 'action is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    resource = request.data.get('resource', '')
    resource_id = request.data.get('resource_id')
    metadata = request.data.get('metadata', {})
    
    try:
        if resource_id:
            resource_id = int(resource_id)
    except ValueError:
        return Response(
            {'error': 'Invalid resource_id format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        analytics_service = AnalyticsService()
        activity = analytics_service.record_user_activity(
            user=request.user,
            action=action,
            resource=resource,
            resource_id=resource_id,
            metadata=metadata,
            request=request
        )
        
        return Response({
            'message': 'Activity recorded successfully',
            'activity_id': activity.id
        })
    
    except Exception as e:
        return Response(
            {'error': f'Failed to record activity: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_metric(request):
    """
    Record a custom metric.
    
    Body parameters:
    - name: Metric name (required)
    - value: Metric value (required)
    - metric_type: Type of metric (default: gauge)
    - tags: Metric tags (optional)
    """
    name = request.data.get('name')
    value = request.data.get('value')
    
    if not name or value is None:
        return Response(
            {'error': 'name and value are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        value = float(value)
    except (ValueError, TypeError):
        return Response(
            {'error': 'Invalid value format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    metric_type = request.data.get('metric_type', 'gauge')
    tags = request.data.get('tags', {})
    
    valid_types = ['counter', 'gauge', 'histogram', 'timer']
    if metric_type not in valid_types:
        return Response(
            {'error': f'Invalid metric_type. Valid options: {valid_types}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        analytics_service = AnalyticsService()
        metric = analytics_service.record_metric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags
        )
        
        return Response({
            'message': 'Metric recorded successfully',
            'metric_id': metric.id
        })
    
    except Exception as e:
        return Response(
            {'error': f'Failed to record metric: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def alerts(request):
    """Get active alerts."""
    try:
        from .models import Alert
        
        status_filter = request.GET.get('status', 'firing')
        
        alerts = Alert.objects.filter(status=status_filter).select_related('rule')
        
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'id': alert.id,
                'rule_name': alert.rule.name,
                'severity': alert.rule.severity,
                'status': alert.status,
                'message': alert.message,
                'metric_value': alert.metric_value,
                'fired_at': alert.fired_at,
                'resolved_at': alert.resolved_at,
                'acknowledged_by': alert.acknowledged_by.username if alert.acknowledged_by else None,
                'acknowledged_at': alert.acknowledged_at
            })
        
        return Response({
            'alerts': alerts_data,
            'total_count': len(alerts_data)
        })
    
    except Exception as e:
        return Response(
            {'error': f'Failed to get alerts: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def acknowledge_alert(request, alert_id):
    """Acknowledge an alert."""
    try:
        from .models import Alert
        
        alert = Alert.objects.get(id=alert_id)
        
        if alert.status != 'firing':
            return Response(
                {'error': 'Alert is not in firing state'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alert.status = 'acknowledged'
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        
        return Response({
            'message': 'Alert acknowledged successfully'
        })
    
    except Alert.DoesNotExist:
        return Response(
            {'error': 'Alert not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    except Exception as e:
        return Response(
            {'error': f'Failed to acknowledge alert: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def check_alert_rules(request):
    """Manually trigger alert rule checking."""
    try:
        analytics_service = AnalyticsService()
        triggered_alerts = analytics_service.check_alert_rules()
        
        return Response({
            'message': 'Alert rules checked successfully',
            'triggered_alerts': triggered_alerts,
            'count': len(triggered_alerts)
        })
    
    except Exception as e:
        return Response(
            {'error': f'Failed to check alert rules: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )