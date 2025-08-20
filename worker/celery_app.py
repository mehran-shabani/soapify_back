"""
Celery app configuration for SOAPify.
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soapify.settings')

app = Celery('soapify')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure task routes
app.conf.task_routes = {
    'stt.tasks.*': {'queue': 'stt'},
    'nlp.tasks.*': {'queue': 'nlp'},
    'outputs.tasks.*': {'queue': 'outputs'},
    'embeddings.tasks.*': {'queue': 'embeddings'},
    'encounters.tasks.*': {'queue': 'encounters'},
    'integrations.tasks.*': {'queue': 'integrations'},
    # Default queue for other tasks
    '*': {'queue': 'default'},
}

# Configure task priorities
app.conf.task_default_priority = 5
app.conf.task_priority_steps = [0, 3, 6, 9]

# Configure worker settings
app.conf.worker_prefetch_multiplier = 1
app.conf.worker_max_tasks_per_child = 1000
app.conf.worker_disable_rate_limits = False

# Configure result backend
app.conf.result_expires = 3600  # 1 hour

# Configure task serialization
app.conf.task_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'

# Configure timezone
app.conf.timezone = 'UTC'
app.conf.enable_utc = True

# Configure beat schedule
app.conf.beat_schedule = {
    # Cleanup tasks
    'cleanup-uncommitted-files': {
        'task': 'encounters.tasks.cleanup_uncommitted_files',
        'schedule': 7200.0,  # Every 2 hours
        'options': {'queue': 'encounters'}
    },
    'cleanup-old-embeddings': {
        'task': 'embeddings.tasks.cleanup_old_embeddings',
        'schedule': 86400.0,  # Daily
        'options': {'queue': 'embeddings'}
    },
    'update-embedding-stats': {
        'task': 'embeddings.tasks.update_embedding_index_stats',
        'schedule': 3600.0,  # Hourly
        'options': {'queue': 'embeddings'}
    },
    
    # Health checks
    'system-health-check': {
        'task': 'worker.tasks.system_health_check',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'queue': 'default'}
    },
    
    # Analytics
    'check-alert-rules': {
        'task': 'worker.tasks.check_alert_rules',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'queue': 'default'}
    },
    'calculate-hourly-metrics': {
        'task': 'worker.tasks.calculate_hourly_metrics',
        'schedule': 3600.0,  # Hourly
        'options': {'queue': 'default'}
    },
    
    # Maintenance
    'cleanup-old-task-results': {
        'task': 'worker.tasks.cleanup_old_task_results',
        'schedule': 86400.0,  # Daily
        'options': {'queue': 'default'}
    },
}

# Task monitoring
@app.task(bind=True)
def debug_task(self):
    """Debug task for testing."""
    print(f'Request: {self.request!r}')


# Task failure handler
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """Handle task failures."""
    from adminplus.models import TaskMonitor
    from django.utils import timezone
    import logging
    
    logger = logging.getLogger(__name__)
    logger.error(f'Task {task_id} failed: {exception}')
    
    # Update task monitor
    try:
        task_monitor = TaskMonitor.objects.get(task_id=task_id)
        task_monitor.status = 'failure'
        task_monitor.traceback = str(traceback) if traceback else str(exception)
        task_monitor.completed_at = timezone.now()
        task_monitor.save()
    except TaskMonitor.DoesNotExist:
        pass


# Task success handler
def task_success_handler(sender=None, result=None, **kwargs):
    """Handle task success."""
    from adminplus.models import TaskMonitor
    from django.utils import timezone
    
    task_id = kwargs.get('task_id')
    if not task_id:
        return
    
    try:
        task_monitor = TaskMonitor.objects.get(task_id=task_id)
        task_monitor.status = 'success'
        task_monitor.result = result
        task_monitor.completed_at = timezone.now()
        
        # Calculate runtime if started_at is available
        if task_monitor.started_at:
            runtime = (task_monitor.completed_at - task_monitor.started_at).total_seconds()
            task_monitor.runtime = runtime
        
        task_monitor.save()
    except TaskMonitor.DoesNotExist:
        pass


# Task started handler
def task_started_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task start."""
    from adminplus.models import TaskMonitor
    from django.utils import timezone
    
    try:
        task_monitor = TaskMonitor.objects.get(task_id=task_id)
        task_monitor.status = 'started'
        task_monitor.started_at = timezone.now()
        task_monitor.save()
    except TaskMonitor.DoesNotExist:
        # Create new task monitor entry
        TaskMonitor.objects.create(
            task_id=task_id,
            task_name=task.name if task else 'unknown',
            status='started',
            args=list(args) if args else [],
            kwargs=kwargs if kwargs else {},
            started_at=timezone.now()
        )


# Connect signal handlers
from celery.signals import task_failure, task_success, task_prerun

task_failure.connect(task_failure_handler)
task_success.connect(task_success_handler)
task_prerun.connect(task_started_handler)