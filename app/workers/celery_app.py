"""
Celery application configuration for FileConverter Pro.
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

# Create Celery app
celery_app = Celery(
    "fileconverter",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=['app.workers.celery_worker']
)

# Configure Celery
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,
    result_expires=86400,  # Results expire after 24 hours
    task_track_started=True,
    task_time_limit=600,  # 10 minute hard limit
    task_soft_time_limit=540,  # 9 minute soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    broker_connection_retry_on_startup=True,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-files': {
        'task': 'app.workers.celery_worker.cleanup_old_files_task',
        'schedule': crontab(minute='*/30'),  # Run every 30 minutes
    },
    'worker-heartbeat': {
        'task': 'app.workers.celery_worker.worker_heartbeat_task',
        'schedule': 60.0,  # Run every 60 seconds
    },
}

if __name__ == '__main__':
    celery_app.start()
