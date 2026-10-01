"""Catalog transactions, historical lifecycle and explicit staff authorization."""

from collections.abc import Iterator
from contextlib import contextmanager
from math import ceil
from typing import Literal, cast
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.embeddings.dispatch import request_generation
from app.ai.embeddings.pipeline import invalidate
from app.ai.embeddings.source import book_source, source_hash
from app.api.dependencies import Principal
from app.core.config import Settings
from app.core.errors import AppError
from app.core.permissions import Permission, authorize
from app.core.security import now
from app.db.enums import (
    BorrowingStatus,
    CopyCondition,
    CopyStatus,
    InteractionSource,
    InteractionType,
    ReservationStatus,
)
from app.db.models.catalog import (
    Author,
    Book,
    BookAuthor,
    BookCategory,
    BookCopy,
    Category,
    Publisher,
)
from app.db.models.circulation import Borrowing, Reservation
from app.db.models.engagement import UserInteraction
from app.db.models.users import User
from app.repositories.catalog import get_book
from app.schemas.catalog import (
    BookCreate,
    BookPatch,
    BookRead,
    CopyCreate,
    CopyPatch,
    CopyRead,
    Page,
)
from app.services.audit.events import AuditContext, record
from app.services.auth.service import AuthService
from app.services.copies.state import validate_maintenance
from app.services.reservations.service import advance_queue, lock_participants
from app.services.settings.policy import circulation_policy
from app.services.storage.images import ImageStorage

Taxonomy = Literal["authors", "categories", "publishers"]
type ReferenceModel = type[Author] | type[Category] | type[Publisher]
MODELS: dict[Taxonomy, ReferenceModel] = {
    "authors": Author,
    "categories": Category,
    "publishers": Publisher,
}
CODES = {
    "authors": "AUTHOR_NOT_FOUND",
    "categories": "CATEGORY_NOT_FOUND",
    "publishers": "PUBLISHER_NOT_FOUND",
}
type Reference = Author | Category | Publisher


@contextmanager
def transaction(engine: Engine) -> Iterator[Session]:
    try:
        with Session(engine, expire_on_commit=False) as db, db.begin():
            yield db
    except IntegrityError as exc:
        code = getattr(exc.orig, "sqlstate", None)
        if code == "23505":
            raise AppError(
                "CATALOG_CONFLICT", "ISBN, түгендеу нөмірі немесе санат атауы бұрын тіркелген.", 409
            ) from None
        if code == "23503":
            raise AppError(
                "CATALOG_REFERENCE_CONFLICT",
                "Байланысты жазба табылмады немесе әлі қолданылуда.",
                409,
            ) from None
        raise


def taxonomy_page[T: BaseModel](
    db: Session,
    kind: Taxonomy,
    schema: type[T],
    page: int,
    page_size: int,
    q: str,
    include_archived: bool,
) -> Page[T]:
    model = MODELS[kind]
    name = getattr(model, "full_name" if kind == "authors" else "name")
    query = select(model)
    if not include_archived:
        query = query.where(model.archived_at.is_(None))
    if q:
        query = query.where(name.icontains(q, autoescape=True))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(name, model.id).offset((page - 1) * page_size).limit(page_size)
    )
    return Page(
        items=[schema.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size),
    )


class CatalogService:
    def __init__(
        self, engine: Engine, settings: Settings, context: AuditContext, principal: Principal
    ):
        self.engine, self.context, self.principal = engine, context, principal
        self.settings = settings
        self.auth = AuthService(engine, settings, context)

    def authorize(self, db: Session) -> None:
        user = self.auth.require_live(db, self.principal.user.id, self.principal.family_id)
        authorize(user.role, Permission.MANAGE_CATALOG)

    def audit(self, db: Session, action: str, entity: str, identity: UUID) -> None:
        record(db, action, self.context, self.principal.user.id, identity, entity_type=entity)

    def lock_book(self, db: Session, identity: UUID, archived: bool = False) -> Book:
        book = db.scalar(select(Book).where(Book.id == identity).with_for_update())
        if book is None or (book.archived_at and not archived):
            raise AppError("BOOK_NOT_FOUND", "Кітап табылмады.", 404)
        return book

    def references(self, db: Session, values: dict[str, object]) -> None:
        references: tuple[tuple[str, ReferenceModel, str], ...] = (
            ("author_ids", Author, "AUTHOR_NOT_FOUND"),
            ("category_ids", Category, "CATEGORY_NOT_FOUND"),
            ("publisher_id", Publisher, "PUBLISHER_NOT_FOUND"),
        )
        for field, model, code in references:
            if field not in values:
                continue
            raw = values[field]
            identities = raw if isinstance(raw, list) else [raw] if raw is not None else []
            rows = cast(
                list[Reference],
                list(
                    db.scalars(
                        select(model)
                        .where(model.id.in_(identities))
                        .order_by(model.id)
                        .with_for_update(read=True)
                    )
                ),
            )
            if len(rows) != len(identities) or any(row.archived_at for row in rows):
                raise AppError(code, "Таңдалған анықтамалық жазба табылмады немесе мұрағатта.", 404)

    def book_write(self, data: BookCreate | BookPatch, identity: UUID | None = None) -> BookRead:
        values = data.model_dump(exclude_unset=identity is not None)
        with transaction(self.engine) as db:
            book = self.lock_book(db, identity) if identity else Book()
            previous_hash = source_hash(book_source(get_book(db, identity))) if identity else None
            self.references(db, values)
            self.authorize(db)
            for field, value in values.items():
                if field not in {"author_ids", "category_ids"}:
                    setattr(book, field, value)
            db.add(book)
            if identity:
                book.updated_at = now()
            db.flush()
            for field, model, related in (
                ("author_ids", BookAuthor, "author_id"),
                ("category_ids", BookCategory, "category_id"),
            ):
                if field in values:
                    db.execute(delete(model).where(model.book_id == book.id))
                    for related_id in values[field]:
                        db.add(model(book_id=book.id, **{related: related_id}))
            self.audit(db, "BOOK_UPDATED" if identity else "BOOK_CREATED", "BOOK", book.id)
            db.flush()
            db.expire(book, ["authors", "categories", "publisher"])
            result = get_book(db, book.id)
            changed = previous_hash != source_hash(book_source(result))
            if changed:
                invalidate(db, [book.id])
        if changed:
            request_generation(self.settings)
        return result

    def cover_write(self, identity: UUID, content: bytes | None, storage: ImageStorage) -> BookRead:
        saved: str | None = None
        previous: str | None = None
        try:
            with transaction(self.engine) as db:
                book = self.lock_book(db, identity)
                self.authorize(db)
                if content is not None:
                    saved = storage.save(content)
                previous, book.cover_url = book.cover_url, saved
                self.audit(db, "BOOK_COVER_UPDATED", "BOOK", identity)
                db.flush()
                result = get_book(db, identity)
        except Exception:
            storage.delete(saved)
            raise
        if previous:
            with Session(self.engine) as db:
                shared = db.scalar(
                    select(Book.id).where(Book.cover_url == previous).limit(1)
                ) or db.scalar(select(User.id).where(User.avatar_url == previous).limit(1))
            if not shared:
                storage.delete(previous)
        return result

    def record_view(self, identity: UUID, event_id: UUID) -> None:
        with transaction(self.engine) as db:
            self.lock_book(db, identity)
            user = self.auth.require_live(db, self.principal.user.id, self.principal.family_id)
            authorize(user.role, Permission.READ_PERSONAL)
            db.execute(
                insert(UserInteraction)
                .values(
                    user_id=user.id,
                    book_id=identity,
                    interaction_type=InteractionType.VIEW,
                    source=InteractionSource.CATALOG,
                    event_key=f"view:{user.id}:{event_id}",
                )
                .on_conflict_do_nothing(index_elements=["event_key"])
            )

    def book_archive(self, identity: UUID, archived: bool) -> BookRead:
        with transaction(self.engine) as db:
            book = self.lock_book(db, identity, True)
            if not archived:
                self.references(
                    db,
                    {
                        "publisher_id": book.publisher_id,
                        "author_ids": list(
                            db.scalars(
                                select(BookAuthor.author_id).where(BookAuthor.book_id == identity)
                            )
                        ),
                        "category_ids": list(
                            db.scalars(
                                select(BookCategory.category_id).where(
                                    BookCategory.book_id == identity
                                )
                            )
                        ),
                    },
                )
            self.authorize(db)
            if archived and (
                db.scalar(
                    select(Reservation.id)
                    .where(
                        Reservation.book_id == identity,
                        Reservation.status.in_(
                            [ReservationStatus.WAITING, ReservationStatus.READY]
                        ),
                    )
                    .limit(1)
                )
                or db.scalar(
                    select(BookCopy.id)
                    .where(
                        BookCopy.book_id == identity,
                        BookCopy.status.in_([CopyStatus.BORROWED, CopyStatus.RESERVED]),
                    )
                    .limit(1)
                )
                or db.scalar(
                    select(Borrowing.id)
                    .join(BookCopy, BookCopy.id == Borrowing.book_copy_id)
                    .where(
                        BookCopy.book_id == identity,
                        Borrowing.status.in_([BorrowingStatus.BORROWED, BorrowingStatus.OVERDUE]),
                    )
                    .limit(1)
                )
            ):
                raise AppError(
                    "CATALOG_IN_USE", "Кітаптың белсенді броні немесе берілген данасы бар.", 409
                )
            book.archived_at = (book.archived_at or now()) if archived else None
            self.audit(db, "BOOK_ARCHIVED" if archived else "BOOK_RESTORED", "BOOK", identity)
            db.flush()
            return get_book(db, identity, True)

    def copy_write(
        self,
        data: CopyCreate | CopyPatch,
        book_id: UUID | None = None,
        identity: UUID | None = None,
        archive: bool | None = None,
    ) -> CopyRead:
        with transaction(self.engine) as db:
            if identity:
                book_id = db.scalar(select(BookCopy.book_id).where(BookCopy.id == identity))
            if book_id is None:
                raise AppError("COPY_NOT_FOUND", "Дана табылмады.", 404)
            self.lock_book(db, book_id, archive is True)
            participants = lock_participants(db, book_id, self.principal.user.id)
            self.authorize(db)
            copy = (
                db.scalar(select(BookCopy).where(BookCopy.id == identity).with_for_update())
                if identity
                else BookCopy(book_id=book_id, status=CopyStatus.AVAILABLE)
            )
            if copy is None:
                raise AppError("COPY_NOT_FOUND", "Дана табылмады.", 404)
            if identity and (
                db.scalar(
                    select(Borrowing.id)
                    .where(
                        Borrowing.book_copy_id == identity,
                        Borrowing.status.in_([BorrowingStatus.BORROWED, BorrowingStatus.OVERDUE]),
                    )
                    .limit(1)
                )
                or db.scalar(
                    select(Reservation.id)
                    .where(
                        Reservation.book_copy_id == identity,
                        Reservation.status == ReservationStatus.READY,
                    )
                    .limit(1)
                )
                or copy.status in {CopyStatus.RESERVED, CopyStatus.BORROWED}
            ):
                raise AppError("CATALOG_IN_USE", "Бұл дананы айналым әрекеті арқылы өңдеңіз.", 409)
            if archive is not None:
                copy.archived_at = (copy.archived_at or now()) if archive else None
            else:
                if copy.archived_at:
                    raise AppError("COPY_NOT_FOUND", "Дана мұрағатта.", 404)
                values = data.model_dump(exclude_unset=identity is not None)
                condition = values.get("condition", copy.condition or CopyCondition.GOOD)
                status = values.get("status", copy.status)
                if not identity and condition == CopyCondition.DAMAGED:
                    status = CopyStatus.DAMAGED
                validate_maintenance(copy.status, status, condition)
                for field, value in values.items():
                    setattr(copy, field, value)
                copy.status, copy.condition = status, condition
            db.add(copy)
            db.flush()
            action = "COPY_CREATED" if not identity else "COPY_UPDATED"
            if copy.status in {CopyStatus.DAMAGED, CopyStatus.LOST}:
                action = "COPY_MARKED_" + copy.status.value
            self.audit(db, action, "BOOK_COPY", copy.id)
            if copy.status == CopyStatus.AVAILABLE and copy.archived_at is None:
                advance_queue(
                    db,
                    book_id,
                    participants,
                    circulation_policy(db),
                    self.settings,
                    now(),
                    context=self.context,
                )
            return CopyRead.model_validate(copy)

    def taxonomy_write(
        self,
        kind: Taxonomy,
        data: BaseModel,
        identity: UUID | None = None,
        archive: bool | None = None,
    ) -> object:
        model = MODELS[kind]
        with transaction(self.engine) as db:
            row = cast(
                Reference | None,
                (
                    db.scalar(select(model).where(model.id == identity).with_for_update())
                    if identity
                    else model()
                ),
            )
            if row is None:
                raise AppError(CODES[kind], "Жазба табылмады.", 404)
            prior_name = (
                getattr(row, "full_name", None) or getattr(row, "name", None),
                row.archived_at,
            )
            self.authorize(db)
            if archive is not None:
                if archive:
                    query = select(Book.id).where(Book.archived_at.is_(None))
                    if kind == "authors":
                        query = query.join(BookAuthor).where(BookAuthor.author_id == identity)
                    elif kind == "categories":
                        query = query.join(BookCategory).where(BookCategory.category_id == identity)
                    else:
                        query = query.where(Book.publisher_id == identity)
                    if db.scalar(query.limit(1)):
                        raise AppError(
                            "CATALOG_IN_USE", "Жазба белсенді каталогта қолданылуда.", 409
                        )
                row.archived_at = (row.archived_at or now()) if archive else None
            else:
                if row.archived_at:
                    raise AppError(CODES[kind], "Жазба мұрағатта.", 404)
                for field, value in data.model_dump(exclude_unset=identity is not None).items():
                    setattr(row, field, value)
            db.add(row)
            db.flush()
            self.audit(
                db,
                "CATALOG_REFERENCE_UPDATED" if identity else "CATALOG_REFERENCE_CREATED",
                kind.upper(),
                row.id,
            )
            changed = identity is not None and prior_name != (
                getattr(row, "full_name", None) or getattr(row, "name", None),
                row.archived_at,
            )
            if changed:
                affected = select(Book.id)
                if kind == "authors":
                    affected = affected.join(BookAuthor).where(BookAuthor.author_id == identity)
                elif kind == "categories":
                    affected = affected.join(BookCategory).where(
                        BookCategory.category_id == identity
                    )
                else:
                    affected = affected.where(Book.publisher_id == identity)
                invalidate(db, affected)
        if changed:
            request_generation(self.settings)
        return row
