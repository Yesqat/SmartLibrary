from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import Principal, require_permission
from app.api.v1.routes.catalog import PageNumber, PageSize, SearchText, mutations
from app.core.auth_http import audit_context
from app.core.permissions import Permission
from app.core.rate_limit import consume
from app.db.enums import BorrowingStatus, CopyStatus, ReservationStatus, UserRole, UserStatus
from app.repositories import admin as repository
from app.repositories.borrowings import borrowing_page
from app.repositories.librarian import reservations as reservation_page
from app.schemas.admin import (
    AdminSummary,
    AuditRead,
    InventoryRow,
    RoleChange,
    SettingRead,
    SettingsChange,
    StatusChange,
)
from app.schemas.auth import ErrorResponse, UserResponse
from app.schemas.catalog import Page
from app.schemas.circulation import BorrowingView
from app.schemas.librarian import StaffReservation
from app.services.administration.service import AdminService

Admin = Annotated[Principal, Depends(require_permission(Permission.MANAGE_USERS))]
SettingsAdmin = Annotated[Principal, Depends(require_permission(Permission.MANAGE_SETTINGS))]
AuditAdmin = Annotated[Principal, Depends(require_permission(Permission.VIEW_AUDIT))]
MonitoringAdmin = Annotated[Principal, Depends(require_permission(Permission.VIEW_ANALYTICS))]
router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Administration"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 429, 503)},
)


def service(request: Request, principal: Principal) -> AdminService:
    consume(request, "admin-write", str(principal.user.id), 60, 60)
    return AdminService(
        request.app.state.db, request.app.state.settings, audit_context(request), principal
    )


@router.get("/users", response_model=Page[UserResponse])
def users(
    request: Request,
    principal: Admin,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: SearchText = "",
    role: UserRole | None = None,
    status: UserStatus | None = None,
) -> Page[UserResponse]:
    with Session(request.app.state.db) as db:
        return repository.users(db, page, page_size, q, role, status)


@router.get("/librarians", response_model=Page[UserResponse])
def librarians(
    request: Request,
    principal: Admin,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: SearchText = "",
    status: UserStatus | None = None,
) -> Page[UserResponse]:
    with Session(request.app.state.db) as db:
        return repository.users(db, page, page_size, q, UserRole.LIBRARIAN, status)


@router.get("/users/{identity}", response_model=UserResponse)
def user(identity: UUID, request: Request, principal: Admin) -> UserResponse:
    with Session(request.app.state.db) as db:
        return repository.user_detail(db, identity)


@router.patch("/users/{identity}/role", response_model=UserResponse, dependencies=mutations)
def change_role(
    identity: UUID, data: RoleChange, request: Request, principal: Admin
) -> UserResponse:
    return service(request, principal).change_user(identity, role=data.role)


@router.patch("/users/{identity}/status", response_model=UserResponse, dependencies=mutations)
def change_status(
    identity: UUID, data: StatusChange, request: Request, principal: Admin
) -> UserResponse:
    return service(request, principal).change_user(identity, status=data.status)


@router.get("/settings", response_model=list[SettingRead])
def settings(request: Request, principal: SettingsAdmin) -> list[SettingRead]:
    with Session(request.app.state.db) as db:
        return repository.settings(db)


@router.patch("/settings", response_model=list[SettingRead], dependencies=mutations)
def change_settings(
    data: SettingsChange, request: Request, principal: SettingsAdmin
) -> list[SettingRead]:
    return service(request, principal).change_settings(data)


@router.get("/audit-logs", response_model=Page[AuditRead])
def audit(
    request: Request,
    principal: AuditAdmin,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    date_from: date | None = None,
    date_to: date | None = None,
    actor: UUID | None = None,
    action: SearchText = "",
    entity_type: SearchText = "",
    q: SearchText = "",
) -> Page[AuditRead]:
    with Session(request.app.state.db) as db:
        return repository.audit_page(
            db,
            page,
            page_size,
            timezone=request.app.state.settings.library_timezone,
            date_from=date_from,
            date_to=date_to,
            actor=actor,
            action=action,
            entity_type=entity_type,
            q=q,
        )


@router.get("/dashboard", response_model=AdminSummary)
def dashboard(request: Request, principal: MonitoringAdmin) -> AdminSummary:
    with Session(request.app.state.db) as db:
        return repository.dashboard(db)


@router.get("/inventory", response_model=Page[InventoryRow])
def inventory(
    request: Request,
    principal: MonitoringAdmin,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: SearchText = "",
    status: CopyStatus | None = None,
    include_archived: bool = False,
) -> Page[InventoryRow]:
    with Session(request.app.state.db) as db:
        return repository.inventory(db, page, page_size, q, status, include_archived)


@router.get("/borrowings", response_model=Page[BorrowingView])
def borrowings(
    request: Request,
    principal: MonitoringAdmin,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: SearchText = "",
    status: BorrowingStatus | None = None,
    overdue: bool = False,
    user_id: UUID | None = None,
) -> Page[BorrowingView]:
    with Session(request.app.state.db) as db:
        return borrowing_page(
            db, page, page_size, q=q, status=status, overdue=overdue, user_id=user_id
        )


@router.get("/reservations", response_model=Page[StaffReservation])
def reservations(
    request: Request,
    principal: MonitoringAdmin,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: SearchText = "",
    status: ReservationStatus | None = None,
    user_id: UUID | None = None,
) -> Page[StaffReservation]:
    with Session(request.app.state.db) as db:
        return reservation_page(db, page, page_size, q, status, user_id)
