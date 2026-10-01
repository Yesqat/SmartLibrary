from datetime import timedelta
from math import ceil
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import AppError
from app.core.security import now
from app.db.enums import BorrowingStatus, UserRole, UserStatus
from app.db.models import Book, BookCopy, Borrowing, User
from app.schemas.catalog import CopyRead, Page
from app.schemas.circulation import BorrowingRead, BorrowingView, InventoryLookup, ReaderOption
from app.services.reservations.service import ACTIVE_LOANS


def borrowing_query() -> Select[tuple[Borrowing, BookCopy, Book, User]]:
    return (
        select(Borrowing, BookCopy, Book, User)
        .join(BookCopy, Borrowing.book_copy_id == BookCopy.id)
        .join(Book, BookCopy.book_id == Book.id)
        .join(User, Borrowing.user_id == User.id)
    )


def serialize(row: Borrowing, copy: BookCopy, book: Book, reader: User) -> BorrowingView:
    return BorrowingView(
        **BorrowingRead.model_validate(row).model_dump(),
        book_id=book.id,
        book_title=book.title,
        cover_url=book.cover_url,
        inventory_number=copy.inventory_number,
        reader_name=f"{reader.first_name} {reader.last_name}",
        is_overdue=row.status in ACTIVE_LOANS and row.due_at < now(),
    )


def borrowing_page(
    db: Session,
    page: int,
    size: int,
    *,
    user_id: UUID | None = None,
    active: bool | None = None,
    overdue: bool = False,
    status: BorrowingStatus | None = None,
    q: str = "",
    minimum_days: int = 0,
    order: Literal["oldest", "newest", "reader"] | None = None,
) -> Page[BorrowingView]:
    query = borrowing_query()
    if status:
        query = query.where(Borrowing.status == status)
    if user_id:
        query = query.where(Borrowing.user_id == user_id)
    if active is not None:
        query = query.where(
            Borrowing.status.in_(ACTIVE_LOANS) if active else Borrowing.status.not_in(ACTIVE_LOANS)
        )
    if overdue:
        query = query.where(
            Borrowing.status.in_(ACTIVE_LOANS),
            Borrowing.due_at < now() - timedelta(days=minimum_days),
        )
    if q.strip():
        query = query.where(
            Book.title.icontains(q.strip(), autoescape=True)
            | BookCopy.inventory_number.icontains(q.strip(), autoescape=True)
            | (User.first_name + " " + User.last_name).icontains(q.strip(), autoescape=True)
        )
    orderings: dict[str, ColumnElement[Any]] = {
        "oldest": Borrowing.due_at.asc(),
        "newest": Borrowing.due_at.desc(),
        "reader": User.last_name.asc(),
    }
    ordering = orderings.get(
        order or "", Borrowing.due_at.asc() if active else Borrowing.borrowed_at.desc()
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(ordering, Borrowing.id.desc()).offset((page - 1) * size).limit(size)
    )
    return Page(
        items=[serialize(*row) for row in rows],
        total=total,
        page=page,
        page_size=size,
        pages=ceil(total / size),
    )


def inventory_lookup(db: Session, number: str) -> InventoryLookup:
    result = db.execute(
        select(BookCopy, Book)
        .join(Book, BookCopy.book_id == Book.id)
        .where(BookCopy.inventory_number == number.strip())
    ).one_or_none()
    if not result:
        raise AppError("COPY_NOT_FOUND", "Дана табылмады.", 404)
    copy, book = result
    active = db.execute(
        borrowing_query().where(
            Borrowing.book_copy_id == copy.id, Borrowing.status.in_(ACTIVE_LOANS)
        )
    ).one_or_none()
    return InventoryLookup(
        book_id=book.id,
        book_title=book.title,
        physical_copy=CopyRead.model_validate(copy),
        active_borrowing=serialize(*active) if active else None,
    )


def reader_options(
    db: Session, q: str, page: int, size: int, status: UserStatus | None = None
) -> Page[ReaderOption]:
    query = select(User).where(User.role == UserRole.READER)
    if q.strip():
        name = User.first_name + " " + User.last_name
        try:
            identity = UUID(q.strip())
        except ValueError:
            identity = None
        query = query.where(
            name.icontains(q.strip(), autoescape=True)
            | User.email.icontains(q.strip(), autoescape=True)
            | (User.id == identity if identity else False)
        )
    if status:
        query = query.where(User.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(User.last_name, User.first_name, User.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return Page(
        items=[ReaderOption.model_validate(row, from_attributes=True) for row in rows],
        total=total,
        page=page,
        page_size=size,
        pages=ceil(total / size),
    )
