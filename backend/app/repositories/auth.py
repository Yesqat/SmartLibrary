"""Identity/session queries; transaction boundaries belong to AuthService."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, undefer

from app.core.security import now
from app.db.models.users import RefreshSession, User


def user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User)
        .where(User.email == email)
        .options(undefer(User.password_hash))
        .with_for_update()
    )


def lock_user(db: Session, user_id: UUID) -> User | None:
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(undefer(User.password_hash))
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def refresh_by_hash(db: Session, digest: str) -> RefreshSession | None:
    return db.scalar(select(RefreshSession).where(RefreshSession.token_hash == digest))


def revoke(db: Session, user_id: UUID, family_id: UUID | None = None) -> None:
    statement = update(RefreshSession).where(
        RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None)
    )
    if family_id is not None:
        statement = statement.where(RefreshSession.family_id == family_id)
    db.execute(statement.values(revoked_at=now()))


def active_roots(db: Session, user_id: UUID) -> list[RefreshSession]:
    return list(
        db.scalars(
            select(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.parent_id.is_(None),
                RefreshSession.revoked_at.is_(None),
                RefreshSession.expires_at > now(),
            )
            .order_by(RefreshSession.created_at.desc())
        )
    )
