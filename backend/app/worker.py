"""
Celery worker for background tasks.
"""
from celery import Celery

from app.config import settings

# Create Celery app
celery = Celery(
    "scribber",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.transcription", "app.tasks.summarization"]
)

# Celery configuration
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max for transcription tasks
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,
)

# Configure task routes
celery.conf.task_routes = {
    "app.tasks.transcription.*": {"queue": "transcription"},
    "app.tasks.summarization.*": {"queue": "summarization"},
}

# Default queue
celery.conf.task_default_queue = "default"
