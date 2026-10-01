"""Shared analytics/report time boundaries and real current-state predicates."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, Date, and_, cast, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import now
from app.db.models import Borrowing
from app.schemas.analytics import AnalyticsDates, CountPoint, PeriodRead
from app.services.reservations.service import ACTIVE_LOANS


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime
    meta: PeriodRead

    def contains(self, column: Any) -> ColumnElement[bool]:
        return and_(column >= self.start, column < self.end)

    def grouped(self, column: Any) -> Any:
        return cast(
            func.date_trunc(self.meta.bucket, func.timezone(self.meta.timezone, column)), Date
        )

    def buckets(self) -> list[date]:
        cursor, last = self.meta.date_from, self.meta.date_to
        if self.meta.bucket == "week":
            cursor -= timedelta(days=cursor.weekday())
        elif self.meta.bucket == "month":
            cursor = cursor.replace(day=1)
        result = []
        while cursor <= last:
            result.append(cursor)
            if self.meta.bucket == "month":
                cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
            else:
                cursor += timedelta(days=7 if self.meta.bucket == "week" else 1)
        return result


def period(values: AnalyticsDates, timezone: str) -> Period:
    at = now()
    today = at.astimezone(ZoneInfo(timezone)).date()
    end = values.date_to or today
    if end.year < 1900 or end.year > 9998:
        raise AppError("VALIDATION_ERROR", "Күндер аралығын тексеріңіз.", 422)
    start = values.date_from or end - timedelta(days=29)
    if start > end or start.year < 1900 or end.year > 9998 or (end - start).days > 3659:
        raise AppError("VALIDATION_ERROR", "Күндер аралығын тексеріңіз (ең көбі 10 жыл).", 422)
    days = (end - start).days + 1
    bucket: Literal["day", "week", "month"] = (
        "day" if days <= 60 else "week" if days <= 365 else "month"
    )
    return Period(
        datetime.combine(start, time.min, ZoneInfo(timezone)),
        datetime.combine(end + timedelta(days=1), time.min, ZoneInfo(timezone)),
        PeriodRead(date_from=start, date_to=end, timezone=timezone, bucket=bucket, generated_at=at),
    )


def active_borrowing() -> ColumnElement[bool]:
    return and_(
        Borrowing.status.in_(ACTIVE_LOANS),
        Borrowing.returned_at.is_(None),
        Borrowing.lost_at.is_(None),
    )


def overdue_borrowing(at: datetime) -> ColumnElement[bool]:
    return and_(active_borrowing(), Borrowing.due_at < at)


def percentage(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 4) if denominator else None


def count(db: Session, model: Any, *conditions: Any) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0


def series(
    db: Session, model: Any, column: Any, window: Period, *conditions: Any
) -> list[CountPoint]:
    bucket = window.grouped(column)
    values: dict[date, int] = dict(
        db.execute(
            select(bucket, func.count())
            .select_from(model)
            .where(window.contains(column), *conditions)
            .group_by(bucket)
        )
        .tuples()
        .all()
    )
    return [CountPoint(date=day, count=values.get(day, 0)) for day in window.buckets()]
