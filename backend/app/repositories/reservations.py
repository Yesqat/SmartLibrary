from math import ceil
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.core.errors import AppError
from app.core.security import now
from app.db.enums import ReservationStatus
from app.db.models.catalog import Book
from app.db.models.circulation import Reservation
from app.schemas.catalog import Page
from app.schemas.reservations import ReservationRead


def reservation_query() -> Select[tuple[Reservation, str, int]]:
    earlier = aliased(Reservation)
    position = (
        select(func.count())
        .where(
            earlier.book_id == Reservation.book_id,
            earlier.status == ReservationStatus.WAITING,
            (earlier.reserved_at < Reservation.reserved_at)
            | ((earlier.reserved_at == Reservation.reserved_at) & (earlier.id <= Reservation.id)),
        )
        .correlate(Reservation)
        .scalar_subquery()
    )
    return select(Reservation, Book.title, position).join(Book, Reservation.book_id == Book.id)


def serialize(row: Reservation, title: str, position: int) -> ReservationRead:
    values = {
        name: getattr(row, name)
        for name in ReservationRead.model_fields
        if name not in {"book_title", "queue_position", "qr_available"}
    }
    return ReservationRead(
        **values,
        book_title=title,
        queue_position=position if row.status == ReservationStatus.WAITING else None,
        qr_available=bool(
            row.status == ReservationStatus.READY and row.expires_at and row.expires_at > now()
        ),
    )


def owned_detail(db: Session, identity: UUID, user_id: UUID) -> ReservationRead:
    result = db.execute(
        reservation_query().where(Reservation.id == identity, Reservation.user_id == user_id)
    ).one_or_none()
    if result is None:
        raise AppError("RESERVATION_NOT_FOUND", "Бронь табылмады.", 404)
    return serialize(*result)


def owned_page(
    db: Session,
    user_id: UUID,
    page: int,
    size: int,
    status: ReservationStatus | None,
    active: bool | None = None,
) -> Page[ReservationRead]:
    query = reservation_query().where(Reservation.user_id == user_id)
    if status:
        query = query.where(Reservation.status == status)
    if active is not None:
        states = [ReservationStatus.WAITING, ReservationStatus.READY]
        query = query.where(
            Reservation.status.in_(states) if active else Reservation.status.not_in(states)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(Reservation.reserved_at.desc(), Reservation.id.desc())
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
