"""Circulation records and database defenses, without implementing workflows."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Identity, Updated
from app.db.enums import BorrowingStatus, ReservationStatus
from app.db.models.catalog import Book, BookCopy
from app.db.models.users import User

reservation_number_sequence = Sequence("reservation_number_seq", metadata=Base.metadata)


class Reservation(Identity, Updated, Base):
    __tablename__ = "reservations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["book_copy_id", "book_id"],
            ["book_copies.id", "book_copies.book_id"],
            ondelete="RESTRICT",
            name="fk_reservations_copy_book",
        ),
        UniqueConstraint("id", "user_id", name="uq_reservations_identity_user"),
        UniqueConstraint(
            "id", "user_id", "book_copy_id", name="uq_reservations_identity_assignment"
        ),
        CheckConstraint("length(btrim(reservation_number)) > 0", name="number"),
        CheckConstraint(
            "qr_token_hash IS NULL OR qr_token_hash ~ '^[0-9a-f]{64}$'", name="qr_hash"
        ),
        CheckConstraint(
            "(status = 'READY' AND qr_token_hash IS NOT NULL "
            "AND qr_token_ciphertext IS NOT NULL AND qr_key_id IS NOT NULL) OR "
            "(status <> 'READY' AND qr_token_hash IS NULL "
            "AND qr_token_ciphertext IS NULL AND qr_key_id IS NULL)",
            name="qr_lifecycle",
        ),
        CheckConstraint(
            "(status = 'WAITING' AND book_copy_id IS NULL AND ready_at IS NULL "
            "AND expires_at IS NULL AND completed_at IS NULL AND cancelled_at IS NULL) OR "
            "(status = 'READY' AND book_copy_id IS NOT NULL AND ready_at IS NOT NULL "
            "AND expires_at IS NOT NULL AND completed_at IS NULL AND cancelled_at IS NULL) OR "
            "(status = 'COMPLETED' AND book_copy_id IS NOT NULL AND ready_at IS NOT NULL "
            "AND expires_at IS NOT NULL AND completed_at IS NOT NULL AND cancelled_at IS NULL) OR "
            "(status = 'CANCELLED' AND cancelled_at IS NOT NULL AND completed_at IS NULL) OR "
            "(status = 'EXPIRED' AND book_copy_id IS NOT NULL AND ready_at IS NOT NULL "
            "AND expires_at IS NOT NULL AND completed_at IS NULL AND cancelled_at IS NULL)",
            name="state_fields",
        ),
        CheckConstraint(
            "(ready_at IS NULL AND book_copy_id IS NULL AND expires_at IS NULL) OR "
            "(ready_at IS NOT NULL AND book_copy_id IS NOT NULL AND expires_at IS NOT NULL "
            "AND ready_at >= reserved_at AND expires_at > ready_at)",
            name="hold_dates",
        ),
        CheckConstraint("completed_at IS NULL OR completed_at >= ready_at", name="completed_date"),
        CheckConstraint(
            "cancelled_at IS NULL OR cancelled_at >= reserved_at", name="cancelled_date"
        ),
        Index(
            "uq_reservations_active_user_book",
            "user_id",
            "book_id",
            unique=True,
            postgresql_where=text("status IN ('WAITING','READY')"),
        ),
        Index(
            "uq_reservations_ready_copy",
            "book_copy_id",
            unique=True,
            postgresql_where=text("status = 'READY'"),
        ),
        Index(
            "ix_reservations_fifo",
            "book_id",
            "reserved_at",
            "id",
            postgresql_where=text("status = 'WAITING'"),
        ),
        Index(
            "ix_reservations_expiry", "expires_at", "id", postgresql_where=text("status = 'READY'")
        ),
        Index("ix_reservations_user_history", "user_id", "reserved_at"),
        Index("ix_reservations_book_status", "book_id", "status"),
        Index("ix_reservations_status_time", "status", "reserved_at"),
        Index("ix_reservations_reserved_time", "reserved_at"),
        Index(
            "ix_reservations_completed_time",
            "completed_at",
            postgresql_where=text("completed_at IS NOT NULL"),
        ),
        Index(
            "ix_reservations_cancelled_time",
            "cancelled_at",
            postgresql_where=text("cancelled_at IS NOT NULL"),
        ),
        Index(
            "ix_reservations_expired_time",
            "expires_at",
            postgresql_where=text("status = 'EXPIRED'"),
        ),
        Index("ix_reservations_copy", "book_copy_id"),
    )
    reservation_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        server_default=text("'R-' || nextval('reservation_number_seq')::text"),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="RESTRICT"))
    book_copy_id: Mapped[UUID | None] = mapped_column()
    qr_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, deferred=True)
    qr_token_ciphertext: Mapped[str | None] = mapped_column(Text, deferred=True)
    qr_key_id: Mapped[str | None] = mapped_column(String(50))
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"), server_default="WAITING"
    )
    user: Mapped[User] = relationship(lazy="raise")
    book: Mapped[Book] = relationship(lazy="raise", foreign_keys=[book_id])
    copy: Mapped[BookCopy | None] = relationship(
        lazy="raise", viewonly=True, foreign_keys=[book_copy_id, book_id]
    )


class Borrowing(Identity, Updated, Base):
    __tablename__ = "borrowings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["reservation_id", "user_id", "book_copy_id"],
            ["reservations.id", "reservations.user_id", "reservations.book_copy_id"],
            ondelete="RESTRICT",
            name="fk_borrowings_reservation_assignment",
        ),
        UniqueConstraint("id", "user_id", name="uq_borrowings_identity_user"),
        CheckConstraint("due_at > borrowed_at", name="due_date"),
        CheckConstraint(
            "(status = 'RETURNED' AND returned_at IS NOT NULL AND returned_by IS NOT NULL "
            "AND returned_at >= borrowed_at AND lost_at IS NULL) OR "
            "(status IN ('BORROWED','OVERDUE') AND returned_at IS NULL "
            "AND returned_by IS NULL AND lost_at IS NULL) OR "
            "(status = 'LOST' AND returned_at IS NULL AND returned_by IS NULL "
            "AND lost_at IS NOT NULL AND lost_at >= borrowed_at)",
            name="state_fields",
        ),
        Index(
            "uq_borrowings_active_copy",
            "book_copy_id",
            unique=True,
            postgresql_where=text("status IN ('BORROWED','OVERDUE')"),
        ),
        Index("ix_borrowings_user_status", "user_id", "status", "borrowed_at"),
        Index("ix_borrowings_copy_history", "book_copy_id", "borrowed_at"),
        Index(
            "ix_borrowings_due",
            "due_at",
            "id",
            postgresql_where=text("status IN ('BORROWED','OVERDUE')"),
        ),
        Index("ix_borrowings_status", "status"),
        Index("ix_borrowings_borrowed", "borrowed_at"),
        Index("ix_borrowings_returned", "returned_at"),
        Index("ix_borrowings_lost_time", "lost_at", postgresql_where=text("lost_at IS NOT NULL")),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    book_copy_id: Mapped[UUID] = mapped_column(ForeignKey("book_copies.id", ondelete="RESTRICT"))
    reservation_id: Mapped[UUID | None] = mapped_column(unique=True)
    issued_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    returned_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    borrowed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lost_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[BorrowingStatus] = mapped_column(
        Enum(BorrowingStatus, name="borrowing_status"), server_default="BORROWED"
    )
    user: Mapped[User] = relationship(lazy="raise", foreign_keys=[user_id])
    copy: Mapped[BookCopy] = relationship(lazy="raise", foreign_keys=[book_copy_id])
    reservation: Mapped[Reservation | None] = relationship(
        lazy="raise", viewonly=True, foreign_keys=[reservation_id, user_id, book_copy_id]
    )
    issuer: Mapped[User] = relationship(lazy="raise", foreign_keys=[issued_by])
    returner: Mapped[User | None] = relationship(lazy="raise", foreign_keys=[returned_by])
