from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.api.v1.routes.catalog import PageNumber, PageSize, SearchText, mutations
from app.api.v1.routes.circulation import Librarian, service
from app.core.auth_http import client_ip
from app.core.rate_limit import consume
from app.db.enums import ReservationStatus
from app.repositories import librarian as repository
from app.repositories.borrowings import borrowing_page
from app.schemas.auth import ErrorResponse
from app.schemas.catalog import Page
from app.schemas.circulation import BorrowingView, PickupPreview
from app.schemas.librarian import (
    LibrarianSummary,
    ManualVerifyInput,
    ReaderOperations,
    StaffReservation,
)

router = APIRouter(
    prefix="/api/v1/librarian",
    tags=["Librarian operations"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 429, 503)},
)


@router.post("/reservations/verify-number", response_model=PickupPreview, dependencies=mutations)
def manual_verify(data: ManualVerifyInput, request: Request, principal: Librarian) -> PickupPreview:
    consume(request, "qr-verify-user", str(principal.user.id), 60, 60)
    consume(request, "qr-verify-ip", client_ip(request), 120, 60)
    return service(request, principal).verify(data.reservation_number, manual=True)


@router.get("/dashboard", response_model=LibrarianSummary)
def dashboard(request: Request, principal: Librarian) -> LibrarianSummary:
    with Session(request.app.state.db) as db:
        return repository.dashboard(db, request.app.state.settings.library_timezone)


@router.get("/readers/{identity}", response_model=ReaderOperations)
def reader(identity: UUID, request: Request, principal: Librarian) -> ReaderOperations:
    with Session(request.app.state.db) as db:
        return repository.reader_detail(db, identity)


@router.get("/readers/{identity}/borrowings", response_model=Page[BorrowingView])
def reader_borrowings(
    identity: UUID,
    request: Request,
    principal: Librarian,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    active: bool = True,
) -> Page[BorrowingView]:
    with Session(request.app.state.db) as db:
        repository.reader_detail(db, identity)
        return borrowing_page(db, page, page_size, user_id=identity, active=active)


@router.get("/reservations", response_model=Page[StaffReservation])
def reservations(
    request: Request,
    principal: Librarian,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: SearchText = "",
    status: ReservationStatus | None = None,
    reader_id: UUID | None = None,
) -> Page[StaffReservation]:
    with Session(request.app.state.db) as db:
        return repository.reservations(db, page, page_size, q, status, reader_id)
