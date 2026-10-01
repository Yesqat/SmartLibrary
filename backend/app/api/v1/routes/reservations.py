from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy.orm import Session

from app.api.v1.routes.catalog import Reader, mutations
from app.core.auth_http import audit_context
from app.core.rate_limit import consume
from app.db.enums import ReservationStatus
from app.repositories.reservations import owned_detail, owned_page
from app.schemas.auth import ErrorResponse
from app.schemas.catalog import Page
from app.schemas.reservations import ReservationCreate, ReservationCredential, ReservationRead
from app.services.reservations.service import ReservationService

router = APIRouter(
    prefix="/api/v1/reservations",
    tags=["Reservations"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 429, 503)},
)


def service(request: Request, principal: Reader) -> ReservationService:
    return ReservationService(
        request.app.state.db, request.app.state.settings, audit_context(request), principal
    )


@router.post("", response_model=ReservationRead, status_code=201, dependencies=mutations)
def reserve(data: ReservationCreate, request: Request, principal: Reader) -> ReservationRead:
    consume(request, "reservation-create", str(principal.user.id), 30, 60)
    return service(request, principal).create(data.book_id)


@router.get("/me", response_model=Page[ReservationRead])
def my_reservations(
    request: Request,
    principal: Reader,
    page: Annotated[int, Query(ge=1, le=100000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: ReservationStatus | None = None,
    active: bool | None = None,
) -> Page[ReservationRead]:
    with Session(request.app.state.db) as db:
        return owned_page(db, principal.user.id, page, page_size, status, active)


@router.get("/{identity}", response_model=ReservationRead)
def detail(identity: UUID, request: Request, principal: Reader) -> ReservationRead:
    with Session(request.app.state.db) as db:
        return owned_detail(db, identity, principal.user.id)


@router.post("/{identity}/cancel", response_model=ReservationRead, dependencies=mutations)
def cancel(identity: UUID, request: Request, principal: Reader) -> ReservationRead:
    consume(request, "reservation-cancel", str(principal.user.id), 60, 60)
    return service(request, principal).cancel(identity)


@router.get("/{identity}/qr", response_model=ReservationCredential)
def credential(identity: UUID, request: Request, principal: Reader) -> ReservationCredential:
    consume(request, "reservation-qr", str(principal.user.id), 60, 60)
    return service(request, principal).credential(identity)
