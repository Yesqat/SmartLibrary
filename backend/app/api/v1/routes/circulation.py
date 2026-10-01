from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.dependencies import Principal, require_permission
from app.api.v1.routes.catalog import PageNumber, PageSize, SearchText, mutations
from app.core.auth_http import audit_context, client_ip
from app.core.permissions import Permission
from app.core.rate_limit import consume
from app.db.enums import UserStatus
from app.repositories.borrowings import borrowing_page, inventory_lookup, reader_options
from app.schemas.auth import ErrorResponse
from app.schemas.catalog import Page
from app.schemas.circulation import (
    BorrowingRead,
    BorrowingView,
    DirectIssueInput,
    InventoryLookup,
    PickupPreview,
    QRVerifyInput,
    ReaderOption,
    ReservedIssueInput,
    ReturnInput,
)
from app.services.borrowings.service import CirculationService

Librarian = Annotated[Principal, Depends(require_permission(Permission.CIRCULATE))]
router = APIRouter(
    prefix="/api/v1/librarian",
    tags=["Circulation"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 429, 503)},
)


def service(request: Request, principal: Principal) -> CirculationService:
    return CirculationService(
        request.app.state.db, request.app.state.settings, audit_context(request), principal
    )


@router.post("/qr/verify", response_model=PickupPreview, dependencies=mutations)
def verify(data: QRVerifyInput, request: Request, principal: Librarian) -> PickupPreview:
    consume(request, "qr-verify-user", str(principal.user.id), 60, 60)
    consume(request, "qr-verify-ip", client_ip(request), 120, 60)
    return service(request, principal).verify(data.token.get_secret_value())


@router.post("/reservations/{identity}/issue", response_model=BorrowingRead, dependencies=mutations)
def issue(
    identity: UUID, data: ReservedIssueInput, request: Request, principal: Librarian
) -> BorrowingRead:
    consume(request, "reserved-issue", str(principal.user.id), 60, 60)
    return service(request, principal).issue_reserved(
        identity, data.verification_token.get_secret_value()
    )


@router.post("/borrowings", response_model=BorrowingRead, dependencies=mutations)
def direct_issue(data: DirectIssueInput, request: Request, principal: Librarian) -> BorrowingRead:
    consume(request, "direct-issue", str(principal.user.id), 60, 60)
    return service(request, principal).issue_direct(data)


@router.post("/borrowings/{identity}/return", response_model=BorrowingRead, dependencies=mutations)
def return_book(
    identity: UUID, data: ReturnInput, request: Request, principal: Librarian
) -> BorrowingRead:
    consume(request, "book-return", str(principal.user.id), 60, 60)
    return service(request, principal).close_loan(identity, condition=data.condition)


@router.post("/borrowings/{identity}/lost", response_model=BorrowingRead, dependencies=mutations)
def lost_book(identity: UUID, request: Request, principal: Librarian) -> BorrowingRead:
    consume(request, "book-lost", str(principal.user.id), 60, 60)
    return service(request, principal).close_loan(identity, lost=True)


@router.get("/borrowings/by-inventory/{inventory_number:path}", response_model=InventoryLookup)
def lookup(inventory_number: str, request: Request, principal: Librarian) -> InventoryLookup:
    from app.core.errors import AppError

    if not inventory_number.strip() or len(inventory_number) > 100:
        raise AppError("VALIDATION_ERROR", "Түгендеу нөмірін тексеріңіз.", 422)
    with Session(request.app.state.db) as db:
        return inventory_lookup(db, inventory_number)


@router.get("/borrowings/overdue", response_model=Page[BorrowingView])
def overdue(
    request: Request,
    principal: Librarian,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: SearchText = "",
    minimum_days: Annotated[int, Query(ge=0, le=36500)] = 0,
    order: Literal["oldest", "newest", "reader"] = "oldest",
) -> Page[BorrowingView]:
    with Session(request.app.state.db) as db:
        return borrowing_page(
            db, page, page_size, overdue=True, q=q, minimum_days=minimum_days, order=order
        )


@router.get("/readers", response_model=Page[ReaderOption])
def readers(
    request: Request,
    principal: Librarian,
    q: SearchText = "",
    page: PageNumber = 1,
    page_size: PageSize = 20,
    status: UserStatus | None = None,
) -> Page[ReaderOption]:
    with Session(request.app.state.db) as db:
        return reader_options(db, q, page, page_size, status)
