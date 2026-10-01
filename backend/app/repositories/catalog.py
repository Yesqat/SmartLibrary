"""Bounded catalog reads with one aggregate for all copy availability on a page."""

from math import ceil
from uuid import UUID

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import AppError
from app.db.enums import CopyStatus
from app.db.models.catalog import Book, BookCopy
from app.schemas.catalog import BookRead, CopyRead, Page


def book_query() -> Select[tuple[Book, int, int, list[str]]]:
    counts = (
        select(
            BookCopy.book_id,
            func.count().label("total"),
            func.count().filter(BookCopy.status == CopyStatus.AVAILABLE).label("available"),
            func.array_agg(distinct(BookCopy.shelf_location))
            .filter(
                (BookCopy.status == CopyStatus.AVAILABLE) & BookCopy.shelf_location.is_not(None)
            )
            .label("shelves"),
        )
        .where(BookCopy.archived_at.is_(None))
        .group_by(BookCopy.book_id)
        .subquery()
    )
    return (
        select(
            Book,
            func.coalesce(counts.c.total, 0),
            func.coalesce(counts.c.available, 0),
            counts.c.shelves,
        )
        .outerjoin(counts, Book.id == counts.c.book_id)
        .options(
            joinedload(Book.publisher), selectinload(Book.authors), selectinload(Book.categories)
        )
    )


def serialize(book: Book, total: int, available: int, shelves: list[str] | None) -> BookRead:
    fields = {
        name: getattr(book, name)
        for name in BookRead.model_fields
        if name not in {"total_copies", "available_copies", "shelf_locations"}
    }
    return BookRead.model_validate(
        {
            **fields,
            "total_copies": total,
            "available_copies": 0 if book.archived_at else available,
            "shelf_locations": sorted(shelves or []) if not book.archived_at else [],
        }
    )


def get_book(db: Session, identity: UUID, include_archived: bool = False) -> BookRead:
    query = book_query().where(Book.id == identity)
    if not include_archived:
        query = query.where(Book.archived_at.is_(None))
    row = db.execute(query).one_or_none()
    if row is None:
        raise AppError("BOOK_NOT_FOUND", "Кітап табылмады.", 404)
    return serialize(*row)


def list_books(
    db: Session, page: int, page_size: int, q: str, include_archived: bool
) -> Page[BookRead]:
    query = book_query()
    if not include_archived:
        query = query.where(Book.archived_at.is_(None))
    if q:
        query = query.where(Book.title.icontains(q, autoescape=True))
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = db.execute(
        query.order_by(Book.created_at.desc(), Book.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page(
        items=[serialize(*row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size),
    )


def list_copies(
    db: Session, book_id: UUID, page: int, page_size: int, include_archived: bool
) -> Page[CopyRead]:
    get_book(db, book_id, include_archived)
    query = select(BookCopy).where(BookCopy.book_id == book_id)
    if not include_archived:
        query = query.where(BookCopy.archived_at.is_(None))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    copies = db.scalars(
        query.order_by(BookCopy.inventory_number, BookCopy.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page(
        items=[CopyRead.model_validate(copy) for copy in copies],
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size),
    )
