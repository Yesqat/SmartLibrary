"""One uncached database snapshot per circulation transaction; no service defaults."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.administration import SystemSetting


@dataclass(frozen=True)
class CirculationPolicy:
    borrow_period_days: int
    max_books_per_user: int
    reservation_hold_hours: int
    return_reminder_days: int
    reservation_reminder_hours: int
    block_borrowing_if_overdue: bool
    block_reservation_if_overdue: bool


def circulation_policy(db: Session) -> CirculationPolicy:
    keys = CirculationPolicy.__annotations__
    values: dict[str, Any] = {
        key: value
        for key, value in db.execute(
            select(SystemSetting.key, SystemSetting.value).where(SystemSetting.key.in_(keys))
        )
    }
    if set(values) != set(keys) or any(type(values[k]) is not t for k, t in keys.items()):
        raise AppError("SETTINGS_UNAVAILABLE", "Кітапхана баптаулары уақытша қолжетімсіз.", 503)
    return CirculationPolicy(**values)
