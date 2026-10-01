"""Catalog input allowlists; physical circulation is never a metadata mutation."""

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.enums import CopyCondition, CopyStatus

Name = Annotated[str, Field(min_length=1, max_length=300)]


class Page[T](BaseModel):
    items: list[T]
    page: int
    page_size: int
    total: int
    pages: int


class CatalogInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def required_values(self) -> "CatalogInput":
        # PATCH permits omission, never nulling mandatory database values.
        required = {
            "title",
            "language",
            "author_ids",
            "category_ids",
            "name",
            "full_name",
            "inventory_number",
            "status",
            "condition",
            "archived",
        }
        for name in self.model_fields_set & required:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


def normalized_isbn(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.replace("-", "").replace(" ", "").upper()
    if (
        len(cleaned) == 13
        and cleaned.isascii()
        and cleaned.isdigit()
        and sum(int(n) * (1 if i % 2 == 0 else 3) for i, n in enumerate(cleaned)) % 10 == 0
    ):
        return cleaned
    if (
        len(cleaned) == 10
        and cleaned[:9].isascii()
        and cleaned[:9].isdigit()
        and cleaned[-1] in "0123456789X"
    ):
        values = [int(n) for n in cleaned[:9]] + [10 if cleaned[-1] == "X" else int(cleaned[-1])]
        if sum(n * (10 - i) for i, n in enumerate(values)) % 11 == 0:
            return cleaned
    raise ValueError("Invalid ISBN checksum or format")


class BookPatch(CatalogInput):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    isbn: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=20000)
    publication_year: int | None = Field(default=None, ge=1, le=9999)
    publisher_id: UUID | None = None
    language: str | None = Field(
        default=None, pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", max_length=35
    )
    page_count: int | None = Field(default=None, ge=1, le=100000)
    author_ids: list[UUID] = Field(default_factory=list, max_length=50)
    category_ids: list[UUID] = Field(default_factory=list, max_length=50)

    @field_validator("isbn")
    @classmethod
    def isbn_checksum(cls, value: str | None) -> str | None:
        return normalized_isbn(value)

    @field_validator("author_ids", "category_ids")
    @classmethod
    def unique_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Duplicate relation")
        return value


class BookCreate(BookPatch):
    title: str = Field(min_length=1, max_length=500)
    language: str = Field(pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", max_length=35)


class ArchiveInput(CatalogInput):
    archived: bool


class BookViewInput(CatalogInput):
    event_id: UUID


class AuthorPatch(CatalogInput):
    full_name: Name | None = None
    biography: str | None = Field(default=None, max_length=20000)


class AuthorCreate(AuthorPatch):
    full_name: Name


class CategoryPatch(CatalogInput):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=20000)


class CategoryCreate(CategoryPatch):
    name: str = Field(min_length=1, max_length=150)


class PublisherPatch(CatalogInput):
    name: str | None = Field(default=None, min_length=1, max_length=250)
    country: str | None = Field(default=None, max_length=100)


class PublisherCreate(PublisherPatch):
    name: str = Field(min_length=1, max_length=250)


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    archived_at: datetime | None


class AuthorRead(ReadModel):
    full_name: str
    biography: str | None


class CategoryRead(ReadModel):
    name: str
    description: str | None


class PublisherRead(ReadModel):
    name: str
    country: str | None


class BookRead(ReadModel):
    title: str
    isbn: str | None
    description: str | None
    publication_year: int | None
    language: str
    page_count: int | None
    cover_url: str | None
    publisher: PublisherRead | None
    authors: list[AuthorRead]
    categories: list[CategoryRead]
    created_at: datetime
    updated_at: datetime
    total_copies: int
    available_copies: int
    shelf_locations: list[str]


class CopyCreate(CatalogInput):
    inventory_number: str = Field(min_length=1, max_length=100, pattern=r"^[^\x00-\x1f/\\]+$")
    shelf_location: str | None = Field(default=None, max_length=150)
    condition: CopyCondition = CopyCondition.GOOD
    acquired_at: date | None = None


class CopyPatch(CatalogInput):
    inventory_number: str | None = Field(
        default=None, min_length=1, max_length=100, pattern=r"^[^\x00-\x1f/\\]+$"
    )
    shelf_location: str | None = Field(default=None, max_length=150)
    status: CopyStatus | None = None
    condition: CopyCondition | None = None
    acquired_at: date | None = None


class CopyRead(ReadModel):
    book_id: UUID
    inventory_number: str
    shelf_location: str | None
    status: CopyStatus
    condition: CopyCondition
    acquired_at: date | None
    created_at: datetime
    updated_at: datetime
