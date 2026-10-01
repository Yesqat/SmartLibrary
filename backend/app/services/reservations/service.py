"""Book -> sorted users -> reservation/copy locks. All transitions share one transaction."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import Engine, case, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, undefer

from app.api.dependencies import Principal
from app.core.config import Settings
from app.core.errors import AppError
from app.core.permissions import Permission, authorize
from app.core.security import now
from app.db.enums import (
    BorrowingStatus,
    CopyCondition,
    CopyStatus,
    InteractionSource,
    InteractionType,
    NotificationType,
    RelatedEntity,
    ReservationStatus,
    UserRole,
    UserStatus,
)
from app.db.models import (
    Book,
    BookCopy,
    Borrowing,
    Notification,
    Reservation,
    User,
    UserInteraction,
)
from app.repositories.reservations import owned_detail
from app.schemas.reservations import ReservationCredential, ReservationRead
from app.services.audit.events import AuditContext, record
from app.services.auth.service import AuthService
from app.services.reservations.qr import ReservationQR, png_data_url
from app.services.settings.policy import CirculationPolicy, circulation_policy

ACTIVE_RESERVATIONS = (ReservationStatus.WAITING, ReservationStatus.READY)
ACTIVE_LOANS = (BorrowingStatus.BORROWED, BorrowingStatus.OVERDUE)


def lock_book(db: Session, book_id: UUID, *, include_archived: bool = False) -> Book:
    book = db.scalar(select(Book).where(Book.id == book_id).with_for_update())
    if book is None or (book.archived_at and not include_archived):
        raise AppError("BOOK_NOT_FOUND", "Кітап табылмады.", 404)
    return book


def lock_participants(db: Session, book_id: UUID, *extra: UUID) -> dict[UUID, User]:
    owners = select(Reservation.user_id).where(
        Reservation.book_id == book_id, Reservation.status.in_(ACTIVE_RESERVATIONS)
    )
    users = db.scalars(
        select(User)
        .where(User.id.in_(owners) | User.id.in_(extra))
        .order_by(User.id)
        .with_for_update()
    )
    return {user.id: user for user in users}


def overdue_users(db: Session, identities: list[UUID], at: datetime) -> set[UUID]:
    return set(
        db.scalars(
            select(Borrowing.user_id)
            .where(
                Borrowing.user_id.in_(identities),
                Borrowing.status.in_(ACTIVE_LOANS),
                Borrowing.due_at < at,
            )
            .distinct()
        )
    )


def eligible(user: User, overdue: set[UUID], policy: CirculationPolicy) -> bool:
    return bool(
        user.role == UserRole.READER
        and user.status == UserStatus.ACTIVE
        and (not policy.block_reservation_if_overdue or user.id not in overdue)
    )


def clear_qr(row: Reservation) -> None:
    row.qr_token_hash = row.qr_token_ciphertext = row.qr_key_id = None


def notify(db: Session, row: Reservation, kind: NotificationType) -> None:
    title, message = {
        NotificationType.RESERVATION_READY: (
            "Кітап алуға дайын",
            "Брондалған кітапты мерзімінде кітапханадан алыңыз.",
        ),
        NotificationType.RESERVATION_EXPIRED: (
            "Бронь мерзімі аяқталды",
            "Кітапты алу мерзімі аяқталды. Қайта брондауға болады.",
        ),
        NotificationType.RESERVATION_EXPIRING: (
            "Бронь мерзімі жақында аяқталады",
            "Броньдегі алу мерзімін тексеріп, кітапханаға уақытында келіңіз.",
        ),
    }[kind]
    db.execute(
        insert(Notification)
        .values(
            user_id=row.user_id,
            type=kind,
            title=title,
            message=message,
            event_key=f"{kind.value}:{row.id}",
            related_entity_type=RelatedEntity.RESERVATION,
            reservation_id=row.id,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "event_key"])
    )


def advance_queue(
    db: Session,
    book_id: UUID,
    users: dict[UUID, User],
    policy: CirculationPolicy,
    settings: Settings,
    at: datetime,
    preferred_copy_ids: tuple[UUID, ...] = (),
    context: AuditContext | None = None,
) -> None:
    """Caller holds book and participant locks. Never skips a locked older waiter."""
    overdue = overdue_users(db, list(users), at) if policy.block_reservation_if_overdue else set()
    waiting = db.scalars(
        select(Reservation)
        .where(Reservation.book_id == book_id, Reservation.status == ReservationStatus.WAITING)
        .order_by(Reservation.reserved_at, Reservation.id)
        .with_for_update()
    ).all()
    copies = iter(
        db.scalars(
            select(BookCopy)
            .where(
                BookCopy.book_id == book_id,
                BookCopy.status == CopyStatus.AVAILABLE,
                BookCopy.archived_at.is_(None),
                BookCopy.condition != CopyCondition.DAMAGED,
            )
            .order_by(
                case((BookCopy.id.in_(preferred_copy_ids), 0), else_=1),
                BookCopy.acquired_at.asc().nulls_last(),
                BookCopy.created_at,
                BookCopy.id,
            )
            .with_for_update()
        ).all()
    )
    for row in waiting:
        user = users.get(row.user_id)
        if not user or not eligible(user, overdue, policy):
            if context is not None:
                record(
                    db,
                    "RESERVATION_QUEUE_SKIPPED",
                    context,
                    entity_id=row.id,
                    reason="USER_HAS_OVERDUE_BOOKS"
                    if row.user_id in overdue
                    else "ACCOUNT_INELIGIBLE",
                    entity_type="RESERVATION",
                )
            continue
        copy = next(copies, None)
        if copy is None:
            break
        row.status = ReservationStatus.READY
        row.book_copy_id = copy.id
        row.ready_at = at
        row.expires_at = at + timedelta(hours=policy.reservation_hold_hours)
        row.qr_token_hash, row.qr_token_ciphertext, row.qr_key_id = ReservationQR(
            settings
        ).generate()
        copy.status = CopyStatus.RESERVED
        db.flush()
        notify(db, row, NotificationType.RESERVATION_READY)


def expire_ready(db: Session, book_id: UUID, at: datetime, context: AuditContext) -> list[UUID]:
    """Shared transition for later scheduled jobs; caller holds book and user locks."""
    rows = db.scalars(
        select(Reservation)
        .where(
            Reservation.book_id == book_id,
            Reservation.status == ReservationStatus.READY,
            Reservation.expires_at <= at,
        )
        .order_by(Reservation.id)
        .with_for_update()
    ).all()
    released = []
    for row in rows:
        copy = db.scalar(select(BookCopy).where(BookCopy.id == row.book_copy_id).with_for_update())
        if copy is None or copy.status != CopyStatus.RESERVED or copy.book_id != book_id:
            raise AppError("RESERVATION_QUEUE_CONFLICT", "Бронь күйін тексеру қажет.", 409)
        row.status = ReservationStatus.EXPIRED
        clear_qr(row)
        copy.status = CopyStatus.AVAILABLE
        released.append(copy.id)
        db.flush()
        notify(db, row, NotificationType.RESERVATION_EXPIRED)
        record(db, "RESERVATION_EXPIRED", context, entity_id=row.id, entity_type="RESERVATION")
    return released


class ReservationService:
    def __init__(
        self, engine: Engine, settings: Settings, context: AuditContext, principal: Principal
    ):
        self.engine, self.settings, self.context, self.principal = (
            engine,
            settings,
            context,
            principal,
        )
        self.auth = AuthService(engine, settings, context)

    def authorize(self, db: Session) -> User:
        user = self.auth.require_live(db, self.principal.user.id, self.principal.family_id)
        authorize(user.role, Permission.RESERVE)
        return user

    def create(self, book_id: UUID) -> ReservationRead:
        with Session(self.engine, expire_on_commit=False) as db, db.begin():
            lock_book(db, book_id)
            users = lock_participants(db, book_id, self.principal.user.id)
            user = self.authorize(db)
            policy, at = circulation_policy(db), now()
            if policy.block_reservation_if_overdue and overdue_users(db, [user.id], at):
                raise AppError(
                    "USER_HAS_OVERDUE_BOOKS", "Мерзімі өткен кітаптарды қайтарыңыз.", 409
                )
            released = expire_ready(db, book_id, at, self.context)
            if db.scalar(
                select(Reservation.id).where(
                    Reservation.book_id == book_id,
                    Reservation.user_id == user.id,
                    Reservation.status.in_(ACTIVE_RESERVATIONS),
                )
            ):
                raise AppError(
                    "RESERVATION_ALREADY_EXISTS", "Бұл кітапқа белсенді броніңіз бар.", 409
                )
            row = Reservation(
                book_id=book_id, user_id=user.id, status=ReservationStatus.WAITING, reserved_at=at
            )
            db.add(row)
            db.flush()
            advance_queue(
                db, book_id, users, policy, self.settings, at, tuple(released), self.context
            )
            db.add(
                UserInteraction(
                    user_id=user.id,
                    book_id=book_id,
                    interaction_type=InteractionType.RESERVE,
                    source=InteractionSource.CATALOG,
                    event_key=f"reservation:{row.id}",
                )
            )
            record(
                db, "RESERVATION_CREATED", self.context, user.id, row.id, entity_type="RESERVATION"
            )
            return owned_detail(db, row.id, user.id)

    def cancel(self, identity: UUID) -> ReservationRead:
        with Session(self.engine, expire_on_commit=False) as db, db.begin():
            book_id = db.scalar(
                select(Reservation.book_id).where(
                    Reservation.id == identity, Reservation.user_id == self.principal.user.id
                )
            )
            if book_id is None:
                raise AppError("RESERVATION_NOT_FOUND", "Бронь табылмады.", 404)
            lock_book(db, book_id, include_archived=True)
            users = lock_participants(db, book_id, self.principal.user.id)
            user = self.authorize(db)
            row = db.scalar(
                select(Reservation)
                .where(Reservation.id == identity, Reservation.user_id == user.id)
                .with_for_update()
            )
            assert row is not None
            if row.status == ReservationStatus.COMPLETED:
                raise AppError(
                    "RESERVATION_ALREADY_COMPLETED", "Кітап берілген, бронь аяқталған.", 409
                )
            if row.status in {ReservationStatus.CANCELLED, ReservationStatus.EXPIRED}:
                return owned_detail(db, identity, user.id)
            policy, at = circulation_policy(db), now()
            released = expire_ready(db, book_id, at, self.context)
            if row.status != ReservationStatus.EXPIRED:
                if row.book_copy_id:
                    copy = db.scalar(
                        select(BookCopy).where(BookCopy.id == row.book_copy_id).with_for_update()
                    )
                    if copy is None or copy.status != CopyStatus.RESERVED:
                        raise AppError(
                            "RESERVATION_QUEUE_CONFLICT", "Бронь күйін тексеру қажет.", 409
                        )
                    copy.status = CopyStatus.AVAILABLE
                    released.append(copy.id)
                row.status, row.cancelled_at = ReservationStatus.CANCELLED, at
                clear_qr(row)
                db.flush()
                record(
                    db,
                    "RESERVATION_CANCELLED",
                    self.context,
                    user.id,
                    row.id,
                    entity_type="RESERVATION",
                )
            advance_queue(
                db, book_id, users, policy, self.settings, at, tuple(released), self.context
            )
            return owned_detail(db, identity, user.id)

    def credential(self, identity: UUID) -> ReservationCredential:
        with Session(self.engine) as db:
            row = db.scalar(
                select(Reservation)
                .options(
                    undefer(Reservation.qr_token_hash), undefer(Reservation.qr_token_ciphertext)
                )
                .where(Reservation.id == identity, Reservation.user_id == self.principal.user.id)
            )
            if row is None:
                raise AppError("RESERVATION_NOT_FOUND", "Бронь табылмады.", 404)
            if row.status == ReservationStatus.EXPIRED or (
                row.expires_at and row.expires_at <= now()
            ):
                raise AppError("RESERVATION_EXPIRED", "Бронь мерзімі аяқталған.", 409)
            if row.status != ReservationStatus.READY:
                raise AppError("RESERVATION_NOT_READY", "Бұл бронь үшін QR қолжетімсіз.", 409)
            copy = db.get(BookCopy, row.book_copy_id)
            if not copy or copy.book_id != row.book_id or copy.status != CopyStatus.RESERVED:
                raise AppError("RESERVATION_QUEUE_CONFLICT", "Бронь күйін тексеру қажет.", 409)
            assert (
                row.qr_token_ciphertext and row.qr_token_hash and row.qr_key_id and row.expires_at
            )
            token = ReservationQR(self.settings).recover(
                row.qr_token_ciphertext, row.qr_token_hash, row.qr_key_id
            )
            return ReservationCredential(
                token=token, image_data_url=png_data_url(token), expires_at=row.expires_at
            )
