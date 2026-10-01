from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.circulation import ReaderOption
from app.schemas.reservations import ReservationRead


class ManualVerifyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reservation_number: str = Field(min_length=3, max_length=80)


class ReaderOperations(BaseModel):
    reader: ReaderOption
    phone: str | None
    active_borrowings: int
    overdue_borrowings: int
    borrowing_limit: int
    borrow_period_days: int
    prospective_due_at: datetime
    can_borrow: bool
    restriction_code: str | None


class StaffReservation(ReservationRead):
    reader_id: UUID
    reader_name: str


class RecentOperation(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID | None
    created_at: datetime


class LibrarianSummary(BaseModel):
    issued_today: int
    returned_today: int
    new_reservations_today: int
    active_reservations: int
    overdue_borrowings: int
    day_start: datetime
    day_end: datetime
    timezone: str
    recent_operations: list[RecentOperation]
