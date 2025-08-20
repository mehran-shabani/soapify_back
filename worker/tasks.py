"""
Worker tasks for SOAPify.
"""
import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def system_health_check(self):
    """Perform system health check."""
    try:
        from adminplus.services import AdminService
        
        admin_service = AdminService()
        health_data = admin_service.check_system_health()
        
        logger.info(f"System health check completed: {health_data['overall_status']}")
        
        return {
            'status': 'completed',
            'overall_status': health_data['overall_status'],
            'components_checked': len(health_data['components']),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        
        # Retry up to 3 times
        if self.request.retries < 3:
            raise self.retry(countdown=60, exc=e)
        
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@shared_task(bind=True)
def check_alert_rules(self):
    """Check alert rules and trigger alerts."""
    try:
        from analytics.services import AnalyticsService
        
        analytics_service = AnalyticsService()
        triggered_alerts = analytics_service.check_alert_rules()
        
        logger.info(f"Alert rules check completed: {len(triggered_alerts)} alerts triggered")
        
        # Send notifications for triggered alerts
        for alert in triggered_alerts:
            # Here you would integrate with notification services
            # For now, just log the alert
            logger.warning(f"ALERT: {alert['rule_name']} - {alert['message']}")
        
        return {
            'status': 'completed',
            'triggered_alerts': len(triggered_alerts),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Alert rules check failed: {str(e)}")
        
        # Retry up to 2 times
        if self.request.retries < 2:
            raise self.retry(countdown=30, exc=e)
        
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@shared_task(bind=True)
def calculate_hourly_metrics(self):
    """Calculate hourly business metrics."""
    try:
        from analytics.services import AnalyticsService
        
        # Calculate metrics for the past hour
        now = timezone.now()
        hour_start = now.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        
        analytics_service = AnalyticsService()
        metrics = analytics_service.calculate_business_metrics(hour_start, hour_end)
        
        logger.info(f"Hourly metrics calculated for {hour_start} - {hour_end}: {metrics}")
        
        return {
            'status': 'completed',
            'period_start': hour_start.isoformat(),
            'period_end': hour_end.isoformat(),
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Hourly metrics calculation failed: {str(e)}")
        
        # Retry up to 2 times
        if self.request.retries < 2:
            raise self.retry(countdown=300, exc=e)  # 5 minute delay
        
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@shared_task(bind=True)
def cleanup_old_task_results(self):
    """Clean up old task results and monitoring data."""
    try:
        from adminplus.models import TaskMonitor
        from analytics.models import Metric, UserActivity, PerformanceMetric
        
        # Clean up task monitoring data older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        
        with transaction.atomic():
            # Clean up old task monitors
            deleted_tasks = TaskMonitor.objects.filter(
                created_at__lt=cutoff_date
            ).delete()
            
            # Clean up old metrics (keep only 7 days)
            metrics_cutoff = timezone.now() - timedelta(days=7)
            deleted_metrics = Metric.objects.filter(
                timestamp__lt=metrics_cutoff
            ).delete()
            
            # Clean up old user activities (keep only 90 days)
            activity_cutoff = timezone.now() - timedelta(days=90)
            deleted_activities = UserActivity.objects.filter(
                timestamp__lt=activity_cutoff
            ).delete()
            
            # Clean up old performance metrics (keep only 30 days)
            perf_cutoff = timezone.now() - timedelta(days=30)
            deleted_perf = PerformanceMetric.objects.filter(
                timestamp__lt=perf_cutoff
            ).delete()
        
        logger.info(f"Cleanup completed: {deleted_tasks[0]} tasks, {deleted_metrics[0]} metrics, "
                   f"{deleted_activities[0]} activities, {deleted_perf[0]} performance records")
        
        return {
            'status': 'completed',
            'deleted_tasks': deleted_tasks[0],
            'deleted_metrics': deleted_metrics[0],
            'deleted_activities': deleted_activities[0],
            'deleted_performance': deleted_perf[0],
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        
        # Don't retry cleanup tasks to avoid cascading issues
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@shared_task(bind=True, max_retries=3)
def send_notification(self, notification_type, recipient, message, metadata=None):
    """
    Send notification to user or admin.
    
    Args:
        notification_type: Type of notification (email, sms, webhook)
        recipient: Recipient identifier
        message: Notification message
        metadata: Additional metadata
    
    Returns:
        Dict with notification result
    """
    try:
        metadata = metadata or {}
        
        if notification_type == 'email':
            # Implement email notification
            # For now, just log
            logger.info(f"EMAIL to {recipient}: {message}")
            
        elif notification_type == 'sms':
            # Implement SMS notification using Crazy Miner
            from integrations.clients.crazy_miner_client import CrazyMinerClient
            
            client = CrazyMinerClient()
            # This would send SMS - implement based on your needs
            logger.info(f"SMS to {recipient}: {message}")
            
        elif notification_type == 'webhook':
            # Implement webhook notification
            import requests
            
            webhook_url = metadata.get('webhook_url')
            if webhook_url:
                payload = {
                    'message': message,
                    'recipient': recipient,
                    'timestamp': datetime.now().isoformat(),
                    'metadata': metadata
                }
                
                response = requests.post(webhook_url, json=payload, timeout=30)
                response.raise_for_status()
                
                logger.info(f"Webhook sent to {webhook_url}")
            
        else:
            raise ValueError(f"Unknown notification type: {notification_type}")
        
        return {
            'status': 'sent',
            'notification_type': notification_type,
            'recipient': recipient,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Notification failed: {str(e)}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {
            'status': 'failed',
            'notification_type': notification_type,
            'recipient': recipient,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@shared_task(bind=True)
def generate_daily_report(self):
    """Generate daily system report."""
    try:
        from analytics.services import AnalyticsService
        from datetime import date
        
        # Generate report for yesterday
        yesterday = date.today() - timedelta(days=1)
        period_start = timezone.make_aware(datetime.combine(yesterday, datetime.min.time()))
        period_end = timezone.make_aware(datetime.combine(yesterday, datetime.max.time()))
        
        analytics_service = AnalyticsService()
        
        # Get business metrics
        business_metrics = analytics_service.calculate_business_metrics(period_start, period_end)
        
        # Get user analytics
        user_analytics = analytics_service.get_user_analytics(days=1)
        
        # Get performance analytics
        performance_analytics = analytics_service.get_performance_analytics(days=1)
        
        # Compile report
        report = {
            'date': yesterday.isoformat(),
            'business_metrics': business_metrics,
            'user_analytics': user_analytics,
            'performance_analytics': performance_analytics,
            'generated_at': datetime.now().isoformat()
        }
        
        # Here you would typically:
        # 1. Generate a PDF report
        # 2. Send it via email to administrators
        # 3. Store it in S3 for archival
        
        logger.info(f"Daily report generated for {yesterday}")
        
        return {
            'status': 'completed',
            'report_date': yesterday.isoformat(),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Daily report generation failed: {str(e)}")
        
        # Retry once after 30 minutes
        if self.request.retries < 1:
            raise self.retry(countdown=1800, exc=e)
        
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@shared_task(bind=True)
def backup_database(self):
    """Backup database (placeholder for actual implementation)."""
    try:
        # This is a placeholder - implement actual database backup logic
        # You might use pg_dump for PostgreSQL or similar tools
        
        logger.info("Database backup task executed (placeholder)")
        
        return {
            'status': 'completed',
            'message': 'Database backup completed (placeholder)',
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Database backup failed: {str(e)}")
        
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@shared_task
def test_task():
    """Simple test task for debugging."""
    logger.info("Test task executed successfully")
    return {
        'status': 'success',
        'message': 'Test task completed',
        'timestamp': datetime.now().isoformat()
    }