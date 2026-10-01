"""Librarian-only circulation; verification never calls the issue transaction."""

from datetime import datetime, timedelta
from uuid import UUID, uuid5

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

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
    ReservationStatus,
    UserRole,
)
from app.db.models import BookCopy, Borrowing, Reservation, User, UserInteraction
from app.schemas.circulation import BorrowingRead, DirectIssueInput, PickupPreview
from app.services.audit.events import AuditContext, record
from app.services.auth.service import AuthService, account_error
from app.services.borrowings.proof import decode_proof, sign_proof
from app.services.reservations.qr import digest
from app.services.reservations.service import (
    ACTIVE_LOANS,
    advance_queue,
    clear_qr,
    eligible,
    expire_ready,
    lock_book,
    lock_participants,
    overdue_users,
)
from app.services.settings.policy import CirculationPolicy, circulation_policy

DIRECT_ISSUE_NAMESPACE = UUID("2e22f60c-e5c8-46e9-a693-3e3d3ec7c35e")


def validate_reader(user: User) -> None:
    if user.role != UserRole.READER:
        raise AppError("USER_NOT_FOUND", "Оқырман табылмады.", 404)
    if failure := account_error(user):
        raise failure


def borrowing_eligibility(db: Session, user: User, policy: CirculationPolicy, at: datetime) -> None:
    validate_reader(user)
    count, overdue = db.execute(
        select(func.count(), func.bool_or(Borrowing.due_at < at)).where(
            Borrowing.user_id == user.id, Borrowing.status.in_(ACTIVE_LOANS)
        )
    ).one()
    if policy.block_borrowing_if_overdue and overdue:
        raise AppError("USER_HAS_OVERDUE_BOOKS", "Мерзімі өткен кітаптарды қайтару қажет.", 409)
    if count >= policy.max_books_per_user:
        raise AppError("BOOK_LIMIT_REACHED", "Оқырман кітап алу лимитіне жеткен.", 409)


def validate_pickup(row: Reservation, copy: BookCopy | None, at: datetime) -> None:
    if row.status == ReservationStatus.EXPIRED or (row.expires_at and row.expires_at <= at):
        raise AppError("RESERVATION_EXPIRED", "Бронь мерзімі аяқталған.", 409)
    if row.status != ReservationStatus.READY:
        raise AppError("RESERVATION_NOT_READY", "Бронь кітап алуға дайын емес.", 409)
    if (
        not copy
        or copy.id != row.book_copy_id
        or copy.book_id != row.book_id
        or copy.status != CopyStatus.RESERVED
        or copy.archived_at
    ):
        raise AppError("RESERVATION_QUEUE_CONFLICT", "Бронь мен дана күйін тексеріңіз.", 409)


class CirculationService:
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
        authorize(user.role, Permission.CIRCULATE)
        return user

    def audit(
        self,
        db: Session,
        action: str,
        entity: str,
        identity: UUID | None = None,
        reason: str | None = None,
    ) -> None:
        record(
            db, action, self.context, self.principal.user.id, identity, reason, entity_type=entity
        )

    def verify(self, token: str, *, manual: bool = False) -> PickupPreview:
        match = (
            (Reservation.reservation_number == token)
            if manual
            else (Reservation.qr_token_hash == digest(token))
        )
        try:
            with Session(self.engine) as db, db.begin():
                # Lookup uses a one-way digest. Never log the submitted credential/hash.
                identity = db.execute(
                    select(Reservation.id, Reservation.book_id, Reservation.user_id).where(match)
                ).one_or_none()
                if identity is None:
                    raise AppError("INVALID_QR", "QR коды жарамсыз.", 404)
                reservation_id, book_id, reader_id = identity
                book = lock_book(db, book_id)
                users = lock_participants(db, book_id, reader_id, self.principal.user.id)
                self.authorize(db)
                row = db.scalar(
                    select(Reservation)
                    .where(Reservation.id == reservation_id, match)
                    .with_for_update()
                )
                if row is None:
                    raise AppError("INVALID_QR", "QR коды жарамсыз.", 404)
                reader = users[reader_id]
                validate_reader(reader)
                copy = db.scalar(
                    select(BookCopy).where(BookCopy.id == row.book_copy_id).with_for_update()
                )
                validate_pickup(row, copy, now())
                assert copy and row.expires_at
                proof, deadline = sign_proof(
                    self.settings, self.principal, row.id, reader.id, copy.id, row.expires_at
                )
                self.audit(
                    db,
                    "RESERVATION_MANUALLY_VERIFIED" if manual else "QR_VERIFIED",
                    "RESERVATION",
                    row.id,
                )
                return PickupPreview(
                    reservation_id=row.id,
                    reservation_number=row.reservation_number,
                    reader_id=reader.id,
                    reader_name=f"{reader.first_name} {reader.last_name}",
                    book_id=book.id,
                    book_title=book.title,
                    book_copy_id=copy.id,
                    inventory_number=copy.inventory_number,
                    shelf_location=copy.shelf_location,
                    expires_at=row.expires_at,
                    verification_token=proof,
                    verification_expires_at=deadline,
                )
        except AppError as exc:
            # Failed verification rolls back; commit only its safe audit separately.
            with Session(self.engine) as db, db.begin():
                self.audit(
                    db,
                    "MANUAL_VERIFICATION_FAILED" if manual else "QR_VERIFICATION_FAILED",
                    "RESERVATION",
                    reason=exc.code,
                )
            raise

    def issue_reserved(self, identity: UUID, proof: str) -> BorrowingRead:
        expected_reader, expected_copy = decode_proof(
            self.settings, self.principal, identity, proof
        )
        with Session(self.engine) as db, db.begin():
            book_id = db.scalar(select(Reservation.book_id).where(Reservation.id == identity))
            if book_id is None:
                raise AppError("RESERVATION_NOT_FOUND", "Бронь табылмады.", 404)
            lock_book(db, book_id)
            users = lock_participants(db, book_id, expected_reader, self.principal.user.id)
            librarian = self.authorize(db)
            row = db.scalar(select(Reservation).where(Reservation.id == identity).with_for_update())
            assert row is not None
            if row.user_id != expected_reader or row.book_copy_id != expected_copy:
                raise AppError("PICKUP_VERIFICATION_REQUIRED", "Броньді қайта тексеріңіз.", 409)
            if row.status == ReservationStatus.COMPLETED:
                previous = db.scalar(select(Borrowing).where(Borrowing.reservation_id == identity))
                if previous and previous.issued_by == librarian.id:
                    return BorrowingRead.model_validate(previous)
                raise AppError(
                    "RESERVATION_ALREADY_COMPLETED", "Бұл бронь бойынша кітап берілген.", 409
                )
            copy = db.scalar(select(BookCopy).where(BookCopy.id == expected_copy).with_for_update())
            at, policy = now(), circulation_policy(db)
            validate_pickup(row, copy, at)
            reader = users[expected_reader]
            borrowing_eligibility(db, reader, policy, at)
            assert copy
            borrowing = Borrowing(
                user_id=reader.id,
                book_copy_id=copy.id,
                reservation_id=row.id,
                issued_by=librarian.id,
                borrowed_at=at,
                due_at=at + timedelta(days=policy.borrow_period_days),
            )
            row.status, row.completed_at = ReservationStatus.COMPLETED, at
            clear_qr(row)
            copy.status = CopyStatus.BORROWED
            db.add(borrowing)
            db.flush()
            db.add(
                UserInteraction(
                    user_id=reader.id,
                    book_id=book_id,
                    interaction_type=InteractionType.BORROW,
                    source=InteractionSource.CATALOG,
                    event_key=f"borrowing:{borrowing.id}",
                )
            )
            self.audit(db, "BOOK_ISSUED", "BORROWING", borrowing.id)
            return BorrowingRead.model_validate(borrowing)

    def issue_direct(self, data: DirectIssueInput) -> BorrowingRead:
        identity = uuid5(DIRECT_ISSUE_NAMESPACE, f"{self.principal.user.id}:{data.idempotency_key}")
        with Session(self.engine) as db, db.begin():
            book_id = db.scalar(select(BookCopy.book_id).where(BookCopy.id == data.book_copy_id))
            if book_id is None:
                raise AppError("COPY_NOT_FOUND", "Дана табылмады.", 404)
            book = lock_book(db, book_id, include_archived=True)
            users = lock_participants(db, book_id, data.user_id, self.principal.user.id)
            librarian = self.authorize(db)
            previous = db.get(Borrowing, identity)
            if previous:
                if (
                    previous.user_id != data.user_id
                    or previous.book_copy_id != data.book_copy_id
                    or previous.issued_by != librarian.id
                ):
                    raise AppError(
                        "IDEMPOTENCY_CONFLICT", "Қайталанған сұраныс деректері сәйкес емес.", 409
                    )
                return BorrowingRead.model_validate(previous)
            if book.archived_at:
                raise AppError("BOOK_NOT_FOUND", "Кітап мұрағатта.", 404)
            reader = users.get(data.user_id)
            if reader is None:
                raise AppError("USER_NOT_FOUND", "Оқырман табылмады.", 404)
            copy = db.scalar(
                select(BookCopy).where(BookCopy.id == data.book_copy_id).with_for_update()
            )
            if not copy or copy.book_id != book_id or copy.archived_at:
                raise AppError("COPY_NOT_FOUND", "Дана табылмады.", 404)
            if copy.status != CopyStatus.AVAILABLE or copy.condition == CopyCondition.DAMAGED:
                code = {
                    CopyStatus.RESERVED: "COPY_RESERVED",
                    CopyStatus.BORROWED: "COPY_ALREADY_BORROWED",
                    CopyStatus.DAMAGED: "COPY_DAMAGED",
                    CopyStatus.LOST: "COPY_LOST",
                    CopyStatus.MAINTENANCE: "COPY_MAINTENANCE",
                }.get(copy.status, "COPY_NOT_AVAILABLE")
                raise AppError(code, "Дана кітап беруге қолжетімді емес.", 409)
            at, policy = now(), circulation_policy(db)
            borrowing_eligibility(db, reader, policy, at)
            overdue = (
                overdue_users(db, list(users), at) if policy.block_reservation_if_overdue else set()
            )
            waiters = db.scalars(
                select(Reservation.user_id).where(
                    Reservation.book_id == book_id, Reservation.status == ReservationStatus.WAITING
                )
            )
            if any(owner in users and eligible(users[owner], overdue, policy) for owner in waiters):
                raise AppError(
                    "RESERVATION_QUEUE_CONFLICT",
                    "Алдымен бронь кезегіндегі оқырманға қызмет көрсетіңіз.",
                    409,
                )
            borrowing = Borrowing(
                id=identity,
                user_id=reader.id,
                book_copy_id=copy.id,
                issued_by=librarian.id,
                borrowed_at=at,
                due_at=at + timedelta(days=policy.borrow_period_days),
            )
            copy.status = CopyStatus.BORROWED
            db.add(borrowing)
            db.flush()
            db.add(
                UserInteraction(
                    user_id=reader.id,
                    book_id=book_id,
                    interaction_type=InteractionType.BORROW,
                    source=InteractionSource.CATALOG,
                    event_key=f"borrowing:{borrowing.id}",
                )
            )
            self.audit(db, "BOOK_ISSUED", "BORROWING", borrowing.id)
            return BorrowingRead.model_validate(borrowing)

    def close_loan(
        self, identity: UUID, *, condition: CopyCondition | None = None, lost: bool = False
    ) -> BorrowingRead:
        with Session(self.engine) as db, db.begin():
            reference = db.execute(
                select(BookCopy.book_id, Borrowing.user_id, Borrowing.book_copy_id)
                .join(Borrowing, Borrowing.book_copy_id == BookCopy.id)
                .where(Borrowing.id == identity)
            ).one_or_none()
            if reference is None:
                raise AppError("BORROWING_NOT_FOUND", "Кітап беру жазбасы табылмады.", 404)
            book_id, reader_id, copy_id = reference
            lock_book(db, book_id, include_archived=True)
            users = lock_participants(db, book_id, reader_id, self.principal.user.id)
            librarian = self.authorize(db)
            borrowing = db.scalar(
                select(Borrowing).where(Borrowing.id == identity).with_for_update()
            )
            assert borrowing is not None
            target = BorrowingStatus.LOST if lost else BorrowingStatus.RETURNED
            if borrowing.status == target:
                return BorrowingRead.model_validate(borrowing)
            if borrowing.status not in ACTIVE_LOANS:
                raise AppError(
                    "RETURN_NOT_ALLOWED", "Аяқталған кітап беру күйін өзгертуге болмайды.", 409
                )
            copy = db.scalar(select(BookCopy).where(BookCopy.id == copy_id).with_for_update())
            if not copy or copy.status != CopyStatus.BORROWED or copy.book_id != book_id:
                raise AppError("INVALID_COPY_TRANSITION", "Дана күйін тексеру қажет.", 409)
            at = now()
            borrowing.status = target
            if lost:
                borrowing.lost_at = at
                copy.status = CopyStatus.LOST
                self.audit(db, "BOOK_LOST", "BORROWING", borrowing.id)
            else:
                if condition is None:
                    raise AppError("VALIDATION_ERROR", "Кітап жағдайын көрсетіңіз.", 422)
                borrowing.returned_at, borrowing.returned_by = at, librarian.id
                copy.condition = condition
                copy.status = (
                    CopyStatus.DAMAGED
                    if condition == CopyCondition.DAMAGED
                    else CopyStatus.AVAILABLE
                )
                self.audit(db, "BOOK_RETURNED", "BORROWING", borrowing.id, condition.value)
                if condition == CopyCondition.DAMAGED:
                    self.audit(db, "COPY_MARKED_DAMAGED", "BOOK_COPY", copy.id)
                db.flush()
                policy = circulation_policy(db)
                released = expire_ready(db, book_id, at, self.context)
                advance_queue(
                    db,
                    book_id,
                    users,
                    policy,
                    self.settings,
                    at,
                    (copy.id, *released),
                    self.context,
                )
            db.flush()
            return BorrowingRead.model_validate(borrowing)
