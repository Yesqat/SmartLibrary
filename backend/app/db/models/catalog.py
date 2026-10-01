"""Bibliographic titles and physical inventory remain separate entities."""

from datetime import date
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Archived, Base, Created, Identity, Updated
from app.db.enums import CopyCondition, CopyStatus


class Author(Identity, Created, Archived, Base):
    __tablename__ = "authors"
    __table_args__ = (
        CheckConstraint("length(btrim(full_name)) > 0", name="name"),
        Index(
            "ix_authors_name_trgm",
            "full_name",
            postgresql_using="gin",
            postgresql_ops={"full_name": "gin_trgm_ops"},
        ),
    )
    full_name: Mapped[str] = mapped_column(String(300))
    biography: Mapped[str | None] = mapped_column(Text)


class Category(Identity, Created, Archived, Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="name"),
        Index(
            "ix_categories_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )
    name: Mapped[str] = mapped_column(String(150), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class Publisher(Identity, Created, Archived, Base):
    __tablename__ = "publishers"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="name"),
        Index(
            "ix_publishers_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )
    name: Mapped[str] = mapped_column(String(250))
    country: Mapped[str | None] = mapped_column(String(100))


class Book(Identity, Updated, Archived, Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("length(btrim(title)) > 0", name="title"),
        CheckConstraint("page_count IS NULL OR page_count > 0", name="page_count"),
        CheckConstraint(
            "publication_year IS NULL OR publication_year BETWEEN 1 AND 9999",
            name="publication_year",
        ),
        CheckConstraint("isbn IS NULL OR isbn ~ '^([0-9]{13}|[0-9]{9}[0-9X])$'", name="isbn"),
        CheckConstraint("language ~ '^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$'", name="language"),
        Index("ix_books_title", "title"),
        Index(
            "ix_books_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index(
            "ix_books_description_trgm",
            "description",
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
        Index("ix_books_language_year", "language", "publication_year"),
        Index("ix_books_publication_year", "publication_year"),
        Index("ix_books_created", "created_at", "id"),
    )
    title: Mapped[str] = mapped_column(String(500))
    isbn: Mapped[str | None] = mapped_column(String(13), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    publication_year: Mapped[int | None]
    publisher_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("publishers.id", ondelete="RESTRICT"), index=True
    )
    language: Mapped[str] = mapped_column(String(35))
    page_count: Mapped[int | None]
    cover_url: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[Publisher | None] = relationship(lazy="raise")
    authors: Mapped[list[Author]] = relationship(
        secondary="book_authors", lazy="raise", viewonly=True
    )
    categories: Mapped[list[Category]] = relationship(
        secondary="book_categories", lazy="raise", viewonly=True
    )
    copies: Mapped[list["BookCopy"]] = relationship(
        back_populates="book", lazy="raise", passive_deletes="all"
    )


class BookAuthor(Identity, Base):
    __tablename__ = "book_authors"
    __table_args__ = (UniqueConstraint("book_id", "author_id"),)
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("authors.id", ondelete="RESTRICT"), index=True
    )


class BookCategory(Identity, Base):
    __tablename__ = "book_categories"
    __table_args__ = (UniqueConstraint("book_id", "category_id"),)
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )


class BookCopy(Identity, Updated, Archived, Base):
    __tablename__ = "book_copies"
    __table_args__ = (
        UniqueConstraint("id", "book_id", name="uq_book_copies_identity_book"),
        CheckConstraint("length(btrim(inventory_number)) > 0", name="inventory_number"),
        CheckConstraint(
            "condition <> 'DAMAGED' OR status IN ('DAMAGED','MAINTENANCE','LOST')",
            name="damaged_not_circulating",
        ),
        CheckConstraint(
            "archived_at IS NULL OR status NOT IN ('RESERVED','BORROWED')",
            name="archive_not_circulating",
        ),
        Index("ix_book_copies_allocation", "book_id", "status", "acquired_at", "created_at", "id"),
        Index("ix_book_copies_status", "status"),
    )
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="RESTRICT"))
    inventory_number: Mapped[str] = mapped_column(String(100), unique=True)
    shelf_location: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[CopyStatus] = mapped_column(
        Enum(CopyStatus, name="copy_status"), server_default="AVAILABLE"
    )
    condition: Mapped[CopyCondition] = mapped_column(
        Enum(CopyCondition, name="copy_condition"), server_default="GOOD"
    )
    acquired_at: Mapped[date | None] = mapped_column(Date)
    book: Mapped[Book] = relationship(back_populates="copies", lazy="raise")
