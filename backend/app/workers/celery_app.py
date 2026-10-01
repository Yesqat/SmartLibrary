"""Separate circulation/ML queues and durable periodic domain workflows."""

from celery import Celery
from kombu import Queue

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "smartlibrary",
    broker=settings.redis_dsn,
    include=["app.workers.embeddings", "app.workers.circulation"],
)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    task_ignore_result=True,
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=3,
    task_default_queue="default",
    task_queues=(Queue("default"), Queue("ml")),
    worker_prefetch_multiplier=1,
    task_track_started=False,
    beat_schedule={
        "circulation-maintenance": {
            "task": "smartlibrary.circulation.sweep",
            "schedule": 60.0,
            "options": {"queue": "default", "expires": 55},
        },
        "missing-embeddings": {
            "task": "smartlibrary.embeddings.sweep",
            "schedule": 60.0,
            "options": {"queue": "ml", "expires": 55},
        },
    },
)
