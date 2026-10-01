from typing import Any

from app.core.config import get_settings
from app.db.session import create_db_engine
from app.services.notifications.scheduled import ScheduledCirculation
from app.workers.celery_app import celery_app


@celery_app.task(  # type: ignore[untyped-decorator]
    name="smartlibrary.circulation.sweep",
    bind=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=240,
    time_limit=300,
)
def sweep(self: Any) -> dict[str, int]:
    settings = get_settings()
    engine = create_db_engine(settings)
    try:
        result = ScheduledCirculation(engine, settings).sweep()
        if result["failed"]:
            raise RuntimeError("SCHEDULED_CIRCULATION_INCOMPLETE")
        return result
    except Exception:
        raise self.retry(exc=RuntimeError("SCHEDULED_CIRCULATION_FAILED"), countdown=60) from None
    finally:
        engine.dispose()
