"""CPU inference is separated from circulation workers; retries are idempotent."""

from typing import Any

from app.ai.embeddings.pipeline import generate_batch
from app.core.config import get_settings
from app.db.session import create_db_engine
from app.workers.celery_app import celery_app


@celery_app.task(  # type: ignore[untyped-decorator]
    name="smartlibrary.embeddings.sweep",
    bind=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=240,
    time_limit=300,
)
def sweep(self: Any) -> dict[str, int]:
    settings = get_settings()
    if not settings.embedding_model:
        return {}
    engine = create_db_engine(settings)
    try:
        return generate_batch(engine, settings, limit=100)
    except Exception:
        # Only a stable safe reason enters task logs; source text and secrets do not.
        raise self.retry(exc=RuntimeError("EMBEDDING_GENERATION_FAILED"), countdown=60) from None
    finally:
        engine.dispose()
