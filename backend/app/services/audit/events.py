"""Write only caller-selected safe metadata in the enclosing domain transaction."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.administration import AuditLog


@dataclass(frozen=True)
class AuditContext:
    request_id: UUID | None = None
    ip_address: str | None = None


def record(
    db: Session,
    action: str,
    context: AuditContext,
    user_id: UUID | None = None,
    entity_id: UUID | None = None,
    reason: str | None = None,
    *,
    entity_type: str = "AUTH",
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details={"reason": reason} if reason else {},
            ip_address=context.ip_address,
            request_id=context.request_id,
        )
    )
