"""Admin read models: bounded SQL queries and safe explicit projections."""

from datetime import date, datetime, time, timedelta
from math import ceil
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import now
from app.db.enums import CopyStatus, UserRole, UserStatus
from app.db.models import AuditLog, Book, BookCopy, Borrowing, Reservation, SystemSetting, User
from app.schemas.admin import AdminSummary, AuditRead, InventoryRow, SettingRead
from app.schemas.auth import UserResponse
from app.schemas.catalog import CopyRead, Page
from app.services.reservations.service import ACTIVE_LOANS, ACTIVE_RESERVATIONS
from app.services.settings.policy import CirculationPolicy


def user_detail(db: Session, identity: UUID) -> UserResponse:
    row = db.get(User, identity)
    if not row:
        raise AppError("USER_NOT_FOUND", "Пайдаланушы табылмады.", 404)
    return UserResponse.model_validate(row)


def users(
    db: Session, page: int, size: int, q: str, role: UserRole | None, status: UserStatus | None
) -> Page[UserResponse]:
    query = select(User)
    if q.strip():
        try:
            identity = UUID(q.strip())
        except ValueError:
            identity = None
        query = query.where(
            (User.first_name + " " + User.last_name).icontains(q.strip(), autoescape=True)
            | User.email.icontains(q.strip(), autoescape=True)
            | (User.id == identity if identity else False)
        )
    if role:
        query = query.where(User.role == role)
    if status:
        query = query.where(User.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(User.created_at.desc(), User.id).offset((page - 1) * size).limit(size)
    )
    return Page(
        items=[UserResponse.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=size,
        pages=ceil(total / size),
    )


def settings(db: Session) -> list[SettingRead]:
    rows = db.scalars(
        select(SystemSetting)
        .where(SystemSetting.key.in_(CirculationPolicy.__annotations__))
        .order_by(SystemSetting.key)
    )
    return [SettingRead.model_validate(row) for row in rows]


def audit_page(
    db: Session,
    page: int,
    size: int,
    *,
    timezone: str,
    date_from: date | None,
    date_to: date | None,
    actor: UUID | None,
    action: str,
    entity_type: str,
    q: str,
) -> Page[AuditRead]:
    if date_from and date_to and date_from > date_to:
        raise AppError("VALIDATION_ERROR", "Күндер аралығын тексеріңіз.", 422)
    query = select(AuditLog, User.first_name, User.last_name).outerjoin(
        User, User.id == AuditLog.user_id
    )
    if date_from:
        query = query.where(
            AuditLog.created_at >= datetime.combine(date_from, time.min, ZoneInfo(timezone))
        )
    if date_to:
        if date_to == date.max:
            raise AppError("VALIDATION_ERROR", "Аяқталу күнін тексеріңіз.", 422)
        query = query.where(
            AuditLog.created_at
            < datetime.combine(date_to + timedelta(days=1), time.min, ZoneInfo(timezone))
        )
    if actor:
        query = query.where(AuditLog.user_id == actor)
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if q.strip():
        query = query.where(
            AuditLog.action.icontains(q.strip(), autoescape=True)
            | AuditLog.entity_type.icontains(q.strip(), autoescape=True)
            | (User.first_name + " " + User.last_name).icontains(q.strip(), autoescape=True)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = []
    for row, first, last in rows:
        # Expose only the structured reason written by our domain services. Never
        # return arbitrary JSON payloads, IP addresses or authentication records.
        reason = (row.details or {}).get("reason")
        details = {"reason": reason[:300]} if isinstance(reason, str) else {}
        items.append(
            AuditRead(
                id=row.id,
                user_id=row.user_id,
                actor_name=f"{first} {last}" if first else None,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                details=details,
                created_at=row.created_at,
            )
        )
    return Page(items=items, total=total, page=page, page_size=size, pages=ceil(total / size))


def inventory(
    db: Session, page: int, size: int, q: str, status: CopyStatus | None, include_archived: bool
) -> Page[InventoryRow]:
    query = select(BookCopy, Book.title, Book.archived_at).join(Book)
    if not include_archived:
        query = query.where(BookCopy.archived_at.is_(None), Book.archived_at.is_(None))
    if status:
        query = query.where(BookCopy.status == status)
    if q.strip():
        query = query.where(
            BookCopy.inventory_number.icontains(q.strip(), autoescape=True)
            | Book.title.icontains(q.strip(), autoescape=True)
            | BookCopy.shelf_location.icontains(q.strip(), autoescape=True)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(BookCopy.inventory_number, BookCopy.id).offset((page - 1) * size).limit(size)
    )
    return Page(
        items=[
            InventoryRow(
                **CopyRead.model_validate(row).model_dump(),
                book_title=title,
                book_archived=archived is not None,
            )
            for row, title, archived in rows
        ],
        total=total,
        page=page,
        page_size=size,
        pages=ceil(total / size),
    )


def dashboard(db: Session) -> AdminSummary:
    copies = (
        select(BookCopy)
        .join(Book)
        .where(BookCopy.archived_at.is_(None), Book.archived_at.is_(None))
        .subquery()
    )
    counts = db.execute(
        select(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.READER)
            .scalar_subquery(),
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.READER, User.status == UserStatus.ACTIVE)
            .scalar_subquery(),
            select(func.count())
            .select_from(Book)
            .where(Book.archived_at.is_(None))
            .scalar_subquery(),
            select(func.count()).select_from(copies).scalar_subquery(),
            *[
                select(func.count())
                .select_from(copies)
                .where(copies.c.status == status)
                .scalar_subquery()
                for status in [
                    CopyStatus.AVAILABLE,
                    CopyStatus.BORROWED,
                    CopyStatus.RESERVED,
                    CopyStatus.DAMAGED,
                    CopyStatus.LOST,
                ]
            ],
            select(func.count())
            .select_from(Reservation)
            .where(Reservation.status.in_(ACTIVE_RESERVATIONS))
            .scalar_subquery(),
            select(func.count())
            .select_from(Borrowing)
            .where(Borrowing.status.in_(ACTIVE_LOANS), Borrowing.due_at < now())
            .scalar_subquery(),
        )
    ).one()
    return AdminSummary(**dict(zip(AdminSummary.model_fields, counts, strict=True)))
