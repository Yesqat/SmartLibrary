from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.db.enums import BorrowingStatus, CopyCondition, UserStatus
from app.schemas.catalog import CopyRead


class QRVerifyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: SecretStr = Field(min_length=32, max_length=256)


class ReservedIssueInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verification_token: SecretStr = Field(min_length=32, max_length=2048)


class PickupPreview(BaseModel):
    reservation_id: UUID
    reservation_number: str
    reader_id: UUID
    reader_name: str
    book_id: UUID
    book_title: str
    book_copy_id: UUID
    inventory_number: str
    shelf_location: str | None
    expires_at: datetime
    verification_token: str
    verification_expires_at: datetime


class BorrowingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    book_copy_id: UUID
    reservation_id: UUID | None
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None
    lost_at: datetime | None
    status: BorrowingStatus


class DirectIssueInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    book_copy_id: UUID
    idempotency_key: UUID


class ReturnInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    condition: CopyCondition


class BorrowingView(BorrowingRead):
    book_id: UUID
    book_title: str
    cover_url: str | None
    inventory_number: str
    reader_name: str
    is_overdue: bool


class InventoryLookup(BaseModel):
    book_id: UUID
    book_title: str
    physical_copy: CopyRead
    active_borrowing: BorrowingView | None


class ReaderOption(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    status: UserStatus
