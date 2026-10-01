"""Identity and hashed refresh credentials used by the authentication service."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Created, Identity, Updated
from app.db.enums import UserRole, UserStatus


class User(Identity, Updated, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(first_name)) > 0 AND length(btrim(last_name)) > 0", name="names"
        ),
        CheckConstraint("email = lower(btrim(email)) AND position('@' in email) > 1", name="email"),
        CheckConstraint("password_hash LIKE '$argon2id$%'", name="password_algorithm"),
        Index("ix_users_role_status_created", "role", "status", "created_at"),
        Index("ix_users_status", "status"),
        Index("ix_users_name", "last_name", "first_name"),
    )
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(Text, deferred=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), server_default="READER"
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), server_default="ACTIVE"
    )


class RefreshSession(Identity, Created, Base):
    __tablename__ = "refresh_sessions"
    __table_args__ = (
        UniqueConstraint("id", "user_id", "family_id", name="uq_refresh_sessions_identity_family"),
        ForeignKeyConstraint(
            ["parent_id", "user_id", "family_id"],
            ["refresh_sessions.id", "refresh_sessions.user_id", "refresh_sessions.family_id"],
            ondelete="RESTRICT",
            name="fk_refresh_sessions_parent_family",
        ),
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="token_hash"),
        CheckConstraint("expires_at > created_at", name="expiry"),
        CheckConstraint("revoked_at IS NULL OR revoked_at >= created_at", name="revocation"),
        CheckConstraint("consumed_at IS NULL OR consumed_at >= created_at", name="consumption"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="no_self_parent"),
        Index("ix_refresh_sessions_user_family", "user_id", "family_id"),
        Index("ix_refresh_sessions_expiry", "expires_at"),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    family_id: Mapped[UUID]
    parent_id: Mapped[UUID | None] = mapped_column(unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, deferred=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(lazy="raise", foreign_keys=[user_id])
