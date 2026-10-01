from datetime import datetime
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
)

from app.db.enums import UserRole, UserStatus
from app.schemas.catalog import CopyRead


class RoleChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: UserRole


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: UserStatus


class SettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    value: int | bool
    value_type: str
    minimum: float | None
    maximum: float | None
    description: str
    updated_at: datetime


class SettingChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=100)
    value: StrictInt | StrictBool
    expected_updated_at: AwareDatetime


class SettingsChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    changes: list[SettingChange] = Field(min_length=1, max_length=20)

    @field_validator("changes")
    @classmethod
    def unique(cls, value: list[SettingChange]) -> list[SettingChange]:
        if len({row.key for row in value}) != len(value):
            raise ValueError("Duplicate setting")
        return value


class AuditRead(BaseModel):
    id: UUID
    user_id: UUID | None
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: UUID | None
    details: dict[str, str]
    created_at: datetime


class InventoryRow(CopyRead):
    book_title: str
    book_archived: bool


class AdminSummary(BaseModel):
    total_readers: int
    active_readers: int
    book_titles: int
    physical_copies: int
    available_copies: int
    borrowed_copies: int
    reserved_copies: int
    damaged_copies: int
    lost_copies: int
    active_reservations: int
    overdue_borrowings: int
