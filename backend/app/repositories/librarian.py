"""Bounded operational views with no authentication secrets or AI history."""

from datetime import timedelta
from math import ceil
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import now
from app.db.enums import ReservationStatus, UserRole
from app.db.models import AuditLog, Borrowing, Reservation, User
from app.db.models.catalog import Book
from app.repositories.reservations import reservation_query, serialize
from app.schemas.catalog import Page
from app.schemas.circulation import ReaderOption
from app.schemas.librarian import (
    LibrarianSummary,
    ReaderOperations,
    RecentOperation,
    StaffReservation,
)
from app.services.borrowings.service import borrowing_eligibility
from app.services.reservations.service import ACTIVE_LOANS, ACTIVE_RESERVATIONS
from app.services.settings.policy import circulation_policy


def reader_detail(db: Session, identity: UUID) -> ReaderOperations:
    user = db.scalar(select(User).where(User.id == identity, User.role == UserRole.READER))
    if not user:
        raise AppError("USER_NOT_FOUND", "Оқырман табылмады.", 404)
    at, policy = now(), circulation_policy(db)
    count, overdue = db.execute(
        select(func.count(), func.count().filter(Borrowing.due_at < at)).where(
            Borrowing.user_id == identity, Borrowing.status.in_(ACTIVE_LOANS)
        )
    ).one()
    restriction = None
    try:
        borrowing_eligibility(db, user, policy, at)
    except AppError as exc:
        restriction = exc.code
    return ReaderOperations(
        reader=ReaderOption.model_validate(user, from_attributes=True),
        phone=user.phone,
        active_borrowings=count,
        overdue_borrowings=overdue,
        borrowing_limit=policy.max_books_per_user,
        borrow_period_days=policy.borrow_period_days,
        prospective_due_at=at + timedelta(days=policy.borrow_period_days),
        can_borrow=restriction is None,
        restriction_code=restriction,
    )


def reservations(
    db: Session,
    page: int,
    size: int,
    q: str = "",
    status: ReservationStatus | None = None,
    user_id: UUID | None = None,
) -> Page[StaffReservation]:
    query = (
        reservation_query()
        .add_columns(User.first_name, User.last_name)
        .join(User, User.id == Reservation.user_id)
    )
    if q.strip():
        query = query.where(
            Reservation.reservation_number.icontains(q.strip(), autoescape=True)
            | Book.title.icontains(q.strip(), autoescape=True)
            | (User.first_name + " " + User.last_name).icontains(q.strip(), autoescape=True)
        )
    if status:
        query = query.where(Reservation.status == status)
    if user_id:
        query = query.where(Reservation.user_id == user_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(Reservation.reserved_at.desc(), Reservation.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    items = [
        StaffReservation(
            **serialize(row, title, position).model_dump(),
            reader_id=row.user_id,
            reader_name=f"{first} {last}",
        )
        for row, title, position, first, last in rows
    ]
    return Page(items=items, total=total, page=page, page_size=size, pages=ceil(total / size))


def dashboard(db: Session, timezone: str) -> LibrarianSummary:
    at = now()
    start = at.astimezone(ZoneInfo(timezone)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    row = db.execute(
        select(
            select(func.count())
            .select_from(Borrowing)
            .where(Borrowing.borrowed_at >= start, Borrowing.borrowed_at < end)
            .scalar_subquery(),
            select(func.count())
            .select_from(Borrowing)
            .where(Borrowing.returned_at >= start, Borrowing.returned_at < end)
            .scalar_subquery(),
            select(func.count())
            .select_from(Reservation)
            .where(Reservation.reserved_at >= start, Reservation.reserved_at < end)
            .scalar_subquery(),
            select(func.count())
            .select_from(Reservation)
            .where(Reservation.status.in_(ACTIVE_RESERVATIONS))
            .scalar_subquery(),
            select(func.count())
            .select_from(Borrowing)
            .where(Borrowing.status.in_(ACTIVE_LOANS), Borrowing.due_at < at)
            .scalar_subquery(),
        )
    ).one()
    operations = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.action.in_(
                ["BOOK_ISSUED", "BOOK_RETURNED", "BOOK_LOST", "COPY_MARKED_DAMAGED"]
            )
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(10)
    )
    return LibrarianSummary(
        issued_today=row[0],
        returned_today=row[1],
        new_reservations_today=row[2],
        active_reservations=row[3],
        overdue_borrowings=row[4],
        day_start=start,
        day_end=end,
        timezone=timezone,
        recent_operations=[
            RecentOperation.model_validate(item, from_attributes=True) for item in operations
        ],
    )
