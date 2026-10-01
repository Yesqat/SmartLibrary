"""Bounded durable jobs. Every item uses the same Book -> User lock order as requests."""

import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Engine, String, cast, exists, func, literal, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import now
from app.db.enums import (
    BorrowingStatus,
    CopyCondition,
    CopyStatus,
    NotificationType,
    RelatedEntity,
    ReservationStatus,
    UserRole,
    UserStatus,
)
from app.db.models import Book, BookCopy, Borrowing, Notification, Reservation, User
from app.services.analytics.definitions import active_borrowing
from app.services.audit.events import AuditContext, record
from app.services.reservations.service import (
    ACTIVE_LOANS,
    advance_queue,
    expire_ready,
    lock_book,
    lock_participants,
    notify,
)
from app.services.settings.policy import circulation_policy


def not_notified(kind: NotificationType, identity: Any) -> ColumnElement[bool]:
    reference = (
        Notification.borrowing_id
        if kind in {NotificationType.DUE_SOON, NotificationType.OVERDUE}
        else Notification.reservation_id
    )
    return ~exists(
        select(Notification.id).where(
            reference == identity,
            Notification.event_key == literal(kind.value + ":") + cast(identity, String),
        )
    )


def timeouts(db: Session) -> None:
    db.execute(text("SET LOCAL lock_timeout = '3s'"))
    db.execute(text("SET LOCAL statement_timeout = '15s'"))


class ScheduledCirculation:
    def __init__(self, engine: Engine, settings: Settings):
        self.engine, self.settings = engine, settings
        self.context = AuditContext()

    def reconcile(self, book_id: UUID) -> int:
        with Session(self.engine) as db, db.begin():
            timeouts(db)
            lock_book(db, book_id)
            users = lock_participants(db, book_id)
            count_ready = (
                select(func.count())
                .select_from(Reservation)
                .where(
                    Reservation.book_id == book_id, Reservation.status == ReservationStatus.READY
                )
            )
            before = db.scalar(count_ready) or 0
            advance_queue(
                db,
                book_id,
                users,
                circulation_policy(db),
                self.settings,
                now(),
                context=self.context,
            )
            db.flush()
            return (db.scalar(count_ready) or 0) - before

    def expiration(self, book_id: UUID) -> int:
        with Session(self.engine) as db, db.begin():
            timeouts(db)
            lock_book(db, book_id, include_archived=True)
            users = lock_participants(db, book_id)
            at, policy = now(), circulation_policy(db)
            released = expire_ready(db, book_id, at, self.context)
            if released:
                advance_queue(
                    db, book_id, users, policy, self.settings, at, tuple(released), self.context
                )
            return len(released)

    def upcoming_reservation(self, identity: UUID) -> bool:
        with Session(self.engine) as db, db.begin():
            timeouts(db)
            book_id = db.scalar(select(Reservation.book_id).where(Reservation.id == identity))
            if book_id is None:
                return False
            lock_book(db, book_id, include_archived=True)
            lock_participants(db, book_id)
            row = db.scalar(select(Reservation).where(Reservation.id == identity).with_for_update())
            policy, at = circulation_policy(db), now()
            if (
                row is None
                or row.status != ReservationStatus.READY
                or row.expires_at is None
                or policy.reservation_reminder_hours == 0
                or not at
                < row.expires_at
                <= at + timedelta(hours=policy.reservation_reminder_hours)
            ):
                return False
            if db.scalar(
                select(Notification.id).where(
                    Notification.event_key == f"RESERVATION_EXPIRING:{row.id}"
                )
            ):
                return False
            notify(db, row, NotificationType.RESERVATION_EXPIRING)
            return True

    def borrowing(self, identity: UUID) -> bool:
        with Session(self.engine) as db, db.begin():
            timeouts(db)
            reference = db.execute(
                select(BookCopy.book_id, Borrowing.user_id)
                .join(Borrowing, Borrowing.book_copy_id == BookCopy.id)
                .where(Borrowing.id == identity)
            ).one_or_none()
            if reference is None:
                return False
            book_id, reader_id = reference
            lock_book(db, book_id, include_archived=True)
            lock_participants(db, book_id, reader_id)
            row = db.scalar(select(Borrowing).where(Borrowing.id == identity).with_for_update())
            at, policy = now(), circulation_policy(db)
            if row is None or row.status not in ACTIVE_LOANS or row.returned_at or row.lost_at:
                return False
            if row.due_at < at:
                kind = NotificationType.OVERDUE
                if row.status == BorrowingStatus.BORROWED:
                    row.status = BorrowingStatus.OVERDUE
                    record(
                        db,
                        "BORROWING_OVERDUE",
                        self.context,
                        entity_id=row.id,
                        entity_type="BORROWING",
                    )
                title, message = (
                    "Қайтару мерзімі өтті",
                    "Кітапты кітапханаға қайтарыңыз. Қарыз туралы мәліметті тексеріңіз.",
                )
            elif policy.return_reminder_days and row.due_at <= at + timedelta(
                days=policy.return_reminder_days
            ):
                kind = NotificationType.DUE_SOON
                title, message = (
                    "Қайтару мерзімі жақындады",
                    "Қолдағы кітаптың қайтару мерзімін тексеріңіз.",
                )
            else:
                return False
            added = db.scalar(
                insert(Notification)
                .values(
                    user_id=row.user_id,
                    type=kind,
                    title=title,
                    message=message,
                    event_key=f"{kind.value}:{row.id}",
                    related_entity_type=RelatedEntity.BORROWING,
                    borrowing_id=row.id,
                )
                .on_conflict_do_nothing(index_elements=["user_id", "event_key"])
                .returning(Notification.id)
            )
            return added is not None

    def sweep(self, *, limit: int = 200) -> dict[str, int]:
        if not 1 <= limit <= 1000:
            raise ValueError("Job batch must be between 1 and 1000")
        at = now()
        with Session(self.engine) as db:
            policy = circulation_policy(db)
            eligible = (
                select(Reservation.book_id)
                .join(User)
                .where(
                    Reservation.status == ReservationStatus.WAITING,
                    User.role == UserRole.READER,
                    User.status == UserStatus.ACTIVE,
                )
            )
            if policy.block_reservation_if_overdue:
                eligible = eligible.where(
                    ~exists(
                        select(Borrowing.id).where(
                            Borrowing.user_id == User.id, active_borrowing(), Borrowing.due_at < at
                        )
                    )
                )
            available = select(BookCopy.book_id).where(
                BookCopy.status == CopyStatus.AVAILABLE,
                BookCopy.archived_at.is_(None),
                BookCopy.condition != CopyCondition.DAMAGED,
            )
            waiting_books = list(
                db.scalars(
                    select(Book.id)
                    .where(
                        Book.archived_at.is_(None), Book.id.in_(eligible), Book.id.in_(available)
                    )
                    .order_by(Book.id)
                    .limit(limit)
                )
            )
            expired = list(
                db.scalars(
                    select(Reservation.book_id)
                    .where(
                        Reservation.status == ReservationStatus.READY, Reservation.expires_at <= at
                    )
                    .distinct()
                    .order_by(Reservation.book_id)
                    .limit(limit)
                )
            )
            upcoming = list(
                db.scalars(
                    select(Reservation.id)
                    .where(
                        Reservation.status == ReservationStatus.READY,
                        Reservation.expires_at > at,
                        Reservation.expires_at
                        <= at + timedelta(hours=policy.reservation_reminder_hours),
                        not_notified(NotificationType.RESERVATION_EXPIRING, Reservation.id),
                    )
                    .order_by(Reservation.expires_at, Reservation.id)
                    .limit(limit)
                )
            )
            due = list(
                db.scalars(
                    select(Borrowing.id)
                    .where(
                        active_borrowing(),
                        or_(
                            (Borrowing.due_at < at)
                            & or_(
                                Borrowing.status == BorrowingStatus.BORROWED,
                                not_notified(NotificationType.OVERDUE, Borrowing.id),
                            ),
                            (Borrowing.due_at >= at)
                            & (Borrowing.due_at <= at + timedelta(days=policy.return_reminder_days))
                            & not_notified(NotificationType.DUE_SOON, Borrowing.id),
                        ),
                    )
                    .order_by(Borrowing.due_at, Borrowing.id)
                    .limit(limit)
                )
            )
        totals = {
            "expired": 0,
            "assigned": 0,
            "pickup_reminders": 0,
            "loan_notifications": 0,
            "failed": 0,
        }
        for name, identifiers, operation in [
            ("expired", expired, self.expiration),
            ("assigned", waiting_books, self.reconcile),
            ("pickup_reminders", upcoming, self.upcoming_reservation),
            ("loan_notifications", due, self.borrowing),
        ]:
            for identity in identifiers:
                try:
                    totals[name] += int(operation(identity))
                except (AppError, SQLAlchemyError) as exc:
                    totals["failed"] += 1
                    logging.getLogger("smartlibrary").error(
                        "scheduled_item_failed", extra={"error_type": type(exc).__name__}
                    )
        return totals
