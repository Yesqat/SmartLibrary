"""Best-effort wakeup; committed missing vectors remain discoverable by the sweep."""

import logging

from celery import Celery

from app.core.config import Settings


def request_generation(settings: Settings) -> None:
    if not settings.embedding_model or not settings.embedding_model_revision:
        return
    try:
        with Celery(broker=settings.redis_dsn) as client:
            client.conf.update(broker_connection_timeout=2, task_serializer="json")
            client.send_task("smartlibrary.embeddings.sweep", queue="ml", retry=False)
    except Exception:
        logging.getLogger("smartlibrary").warning("embedding_wakeup_unavailable")
