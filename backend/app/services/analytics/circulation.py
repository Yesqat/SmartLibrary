from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.enums import ReservationStatus
from app.db.models import Book, BookCategory, BookCopy, Borrowing, Category, Reservation
from app.schemas.analytics import CirculationAnalytics, NamedCount, RankedCount
from app.services.analytics.definitions import (
    Period,
    active_borrowing,
    count,
    overdue_borrowing,
    percentage,
    series,
)
from app.services.reservations.service import ACTIVE_RESERVATIONS


def circulation(db: Session, window: Period) -> CirculationAnalytics:
    completed = count(db, Reservation, window.contains(Reservation.completed_at))
    cancelled = count(db, Reservation, window.contains(Reservation.cancelled_at))
    expired = count(
        db,
        Reservation,
        Reservation.status == ReservationStatus.EXPIRED,
        window.contains(Reservation.expires_at),
    )
    cohort: dict[ReservationStatus, int] = dict(
        db.execute(
            select(Reservation.status, func.count())
            .where(window.contains(Reservation.reserved_at))
            .group_by(Reservation.status)
        )
        .tuples()
        .all()
    )
    popularity = (
        select(Book.id, Book.title, func.count(Borrowing.id).label("loans"))
        .join(BookCopy, BookCopy.book_id == Book.id)
        .join(Borrowing, Borrowing.book_copy_id == BookCopy.id)
        .where(window.contains(Borrowing.borrowed_at))
        .group_by(Book.id, Book.title)
        .order_by(func.count(Borrowing.id).desc(), Book.id)
        .limit(10)
    )
    categories = (
        select(Category.id, Category.name, func.count(Borrowing.id))
        .join(BookCategory, BookCategory.category_id == Category.id)
        .join(BookCopy, BookCopy.book_id == BookCategory.book_id)
        .join(Borrowing, Borrowing.book_copy_id == BookCopy.id)
        .where(window.contains(Borrowing.borrowed_at))
        .group_by(Category.id, Category.name)
        .order_by(func.count(Borrowing.id).desc(), Category.id)
        .limit(10)
    )
    return CirculationAnalytics(
        period=window.meta,
        active_borrowings=count(db, Borrowing, active_borrowing()),
        overdue_borrowings=count(db, Borrowing, overdue_borrowing(window.meta.generated_at)),
        active_reservations=count(db, Reservation, Reservation.status.in_(ACTIVE_RESERVATIONS)),
        waiting_reservations=count(
            db, Reservation, Reservation.status == ReservationStatus.WAITING
        ),
        ready_reservations=count(db, Reservation, Reservation.status == ReservationStatus.READY),
        issued=count(db, Borrowing, window.contains(Borrowing.borrowed_at)),
        returned=count(db, Borrowing, window.contains(Borrowing.returned_at)),
        lost=count(db, Borrowing, window.contains(Borrowing.lost_at)),
        reservations_created=count(db, Reservation, window.contains(Reservation.reserved_at)),
        reservations_completed=completed,
        reservations_cancelled=cancelled,
        reservations_expired=expired,
        reservation_completion_rate=percentage(completed, completed + cancelled + expired),
        reservation_cohort_status=[
            NamedCount(key=status.value, count=cohort.get(status, 0))
            for status in ReservationStatus
        ],
        borrowing_trend=series(db, Borrowing, Borrowing.borrowed_at, window),
        return_trend=series(db, Borrowing, Borrowing.returned_at, window),
        reservation_trend=series(db, Reservation, Reservation.reserved_at, window),
        popular_books=[
            RankedCount(id=identity, label=label, count=value)
            for identity, label, value in db.execute(popularity)
        ],
        popular_categories=[
            RankedCount(id=identity, label=label, count=value)
            for identity, label, value in db.execute(categories)
        ],
    )
