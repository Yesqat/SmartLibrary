from typing import Any

from sqlalchemy import Select, func, select, union_all
from sqlalchemy.orm import Session
from sqlalchemy.sql import Subquery

from app.db.enums import CopyStatus, MessageRole, UserRole, UserStatus
from app.db.models import (
    AIConversation,
    AIMessage,
    Book,
    BookCopy,
    Borrowing,
    Reservation,
    SearchEvent,
    User,
    UserInteraction,
)
from app.schemas.analytics import InventoryAnalytics, NamedCount, ReaderAnalytics
from app.services.analytics.definitions import Period, count, series


def inventory(db: Session, window: Period) -> InventoryAnalytics:
    collection = (
        select(BookCopy.id, BookCopy.status)
        .join(Book)
        .where(BookCopy.archived_at.is_(None), Book.archived_at.is_(None))
        .subquery()
    )
    states: dict[CopyStatus, int] = dict(
        db.execute(select(collection.c.status, func.count()).group_by(collection.c.status))
        .tuples()
        .all()
    )
    return InventoryAnalytics(
        period=window.meta,
        book_titles=count(db, Book, Book.archived_at.is_(None)),
        physical_copies=sum(states.values()),
        status=[NamedCount(key=state.value, count=states.get(state, 0)) for state in CopyStatus],
        added_titles=count(db, Book, window.contains(Book.created_at)),
        added_copies=count(db, BookCopy, window.contains(BookCopy.created_at)),
        additions=series(db, BookCopy, BookCopy.created_at, window),
    )


def active_reader_ids(window: Period) -> Subquery:
    events: list[Select[Any]] = [
        select(user_id).where(window.contains(column))
        for user_id, column in [
            (UserInteraction.user_id, UserInteraction.created_at),
            (SearchEvent.user_id, SearchEvent.created_at),
            (Borrowing.user_id, Borrowing.borrowed_at),
            (Borrowing.user_id, Borrowing.returned_at),
            (Reservation.user_id, Reservation.reserved_at),
            (Reservation.user_id, Reservation.cancelled_at),
            (Reservation.user_id, Reservation.completed_at),
        ]
    ]
    events.append(
        select(AIConversation.user_id)
        .join(AIMessage)
        .where(AIMessage.role == MessageRole.USER, window.contains(AIMessage.created_at))
    )
    return union_all(*events).subquery()


def readers(db: Session, window: Period) -> ReaderAnalytics:
    active = active_reader_ids(window)
    return ReaderAnalytics(
        period=window.meta,
        total_readers=count(db, User, User.role == UserRole.READER),
        active_reader_accounts=count(
            db, User, User.role == UserRole.READER, User.status == UserStatus.ACTIVE
        ),
        active_readers=db.scalar(
            select(func.count(func.distinct(User.id)))
            .join(active, active.c.user_id == User.id)
            .where(User.role == UserRole.READER)
        )
        or 0,
        new_readers=count(db, User, User.role == UserRole.READER, window.contains(User.created_at)),
        registrations=series(db, User, User.created_at, window, User.role == UserRole.READER),
    )
