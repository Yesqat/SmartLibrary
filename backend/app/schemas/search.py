"""Search filters shared by lexical and later vector retrieval."""

from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.catalog import BookRead, CatalogInput, Page


class SearchSort(StrEnum):
    RELEVANCE = "relevance"
    POPULARITY = "popularity"
    RECENT = "recent"
    YEAR_DESC = "year_desc"
    YEAR_ASC = "year_asc"
    TITLE_ASC = "title_asc"
    TITLE_DESC = "title_desc"


class SearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    q: str = Field(default="", max_length=500)
    mode: Literal["standard", "semantic", "hybrid"] = "standard"
    category: UUID | None = None
    author: UUID | None = None
    publisher: UUID | None = None
    language: list[str] = Field(default_factory=list, max_length=10)
    year_from: int | None = Field(default=None, ge=1, le=9999)
    year_to: int | None = Field(default=None, ge=1, le=9999)
    available: bool | None = None
    sort: SearchSort = SearchSort.RELEVANCE
    page: int = Field(default=1, ge=1, le=100000)
    page_size: int = Field(default=20, ge=1, le=100)
    include_archived: bool = False

    @field_validator("language")
    @classmethod
    def language_values(cls, values: list[str]) -> list[str]:
        import re

        if any(
            not re.fullmatch(r"[a-z]{2,3}(-[A-Za-z0-9]{2,8})*", value) or len(value) > 35
            for value in values
        ):
            raise ValueError("Use language codes")
        return sorted(set(values))

    @model_validator(mode="after")
    def year_range(self) -> Self:
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValueError("Invalid year range")
        return self


class SearchPage(Page[BookRead]):
    search_event_id: UUID | None = None
    indexing_pending: bool = False


class Suggestion(BaseModel):
    id: UUID
    label: str
    kind: str


class Autocomplete(BaseModel):
    items: list[Suggestion]


class SearchClick(CatalogInput):
    book_id: UUID
    event_id: UUID
