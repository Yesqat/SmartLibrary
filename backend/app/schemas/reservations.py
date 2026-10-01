from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.enums import ReservationStatus


class ReservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    book_id: UUID


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    reservation_number: str
    book_id: UUID
    book_title: str
    book_copy_id: UUID | None
    status: ReservationStatus
    reserved_at: datetime
    ready_at: datetime | None
    expires_at: datetime | None
    cancelled_at: datetime | None
    completed_at: datetime | None
    queue_position: int | None
    qr_available: bool


class ReservationCredential(BaseModel):
    token: str
    image_data_url: str
    expires_at: datetime
