"""Owned Reader data and explicit profile allowlists."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.enums import NotificationType, RelatedEntity
from app.schemas.auth import RegisterInput
from app.schemas.catalog import CategoryRead


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9 ()\-\.]{7,32}$")

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> object:
        return RegisterInput.clean_name(value)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str | None) -> str | None:
        return RegisterInput.valid_phone(value)


class PreferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category_ids: list[UUID] = Field(max_length=30)

    @field_validator("category_ids")
    @classmethod
    def distinct(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate category")
        return value


class Preferences(BaseModel):
    categories: list[CategoryRead]


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: NotificationType
    title: str
    message: str
    is_read: bool
    related_entity_type: RelatedEntity
    related_entity_id: UUID
    created_at: datetime


class FavoriteState(BaseModel):
    is_favorite: bool


class ReaderSummary(BaseModel):
    active_borrowings: int
    overdue_borrowings: int
    nearest_due_at: datetime | None
    active_reservations: int
    ready_reservations: int
    favorites: int
    unread_notifications: int
