"""SQL pagination and aggregates; identity always comes from authentication."""

from math import ceil
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import now
from app.db.enums import BorrowingStatus, ReservationStatus
from app.db.models.catalog import Book, Category
from app.db.models.circulation import Borrowing, Reservation
from app.db.models.engagement import Favorite, Notification, UserCategoryPreference
from app.repositories.catalog import book_query, serialize
from app.schemas.catalog import BookRead, CategoryRead, Page
from app.schemas.reader import NotificationRead, Preferences, ReaderSummary


def favorite_page(db: Session, user_id: UUID, page: int, size: int) -> Page[BookRead]:
    # Retain archived favorites as visible history, with zero reservable availability.
    condition = Favorite.user_id == user_id
    total = db.scalar(select(func.count()).select_from(Favorite).where(condition)) or 0
    rows = db.execute(
        book_query()
        .join(Favorite, Favorite.book_id == Book.id)
        .where(condition)
        .order_by(Favorite.created_at.desc(), Favorite.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return Page(
        items=[serialize(*row) for row in rows],
        page=page,
        page_size=size,
        total=total,
        pages=ceil(total / size),
    )


def notification_page(
    db: Session, user_id: UUID, page: int, size: int, unread: bool
) -> Page[NotificationRead]:
    query = select(Notification).where(Notification.user_id == user_id)
    if unread:
        query = query.where(Notification.is_read.is_(False))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(Notification.created_at.desc(), Notification.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return Page(
        items=[NotificationRead.model_validate(row) for row in rows],
        page=page,
        page_size=size,
        total=total,
        pages=ceil(total / size),
    )


def preferences(db: Session, user_id: UUID) -> Preferences:
    rows = db.scalars(
        select(Category)
        .join(UserCategoryPreference)
        .where(UserCategoryPreference.user_id == user_id, Category.archived_at.is_(None))
        .order_by(Category.name, Category.id)
    )
    return Preferences(categories=[CategoryRead.model_validate(row) for row in rows])


def summary(db: Session, user_id: UUID) -> ReaderSummary:
    at = now()
    loans = (
        select(Borrowing)
        .where(
            Borrowing.user_id == user_id,
            Borrowing.status.in_([BorrowingStatus.BORROWED, BorrowingStatus.OVERDUE]),
        )
        .subquery()
    )
    reservations = (
        select(Reservation)
        .where(
            Reservation.user_id == user_id,
            Reservation.status.in_([ReservationStatus.WAITING, ReservationStatus.READY]),
        )
        .subquery()
    )
    # Single statement gives a consistent snapshot and never materializes whole tables.
    result = db.execute(
        select(
            select(func.count()).select_from(loans).scalar_subquery(),
            select(func.count()).select_from(loans).where(loans.c.due_at < at).scalar_subquery(),
            select(func.min(loans.c.due_at)).scalar_subquery(),
            select(func.count()).select_from(reservations).scalar_subquery(),
            select(func.count())
            .select_from(reservations)
            .where(reservations.c.status == ReservationStatus.READY, reservations.c.expires_at > at)
            .scalar_subquery(),
            select(func.count())
            .select_from(Favorite)
            .where(Favorite.user_id == user_id)
            .scalar_subquery(),
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .scalar_subquery(),
        )
    ).one()
    return ReaderSummary(**dict(zip(ReaderSummary.model_fields, result, strict=True)))
