"""Validated persistent settings and append-only operational audit history."""

from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Created, Identity, Updated
from app.db.enums import SettingType


class SystemSetting(Identity, Updated, Base):
    __tablename__ = "system_settings"
    __table_args__ = (
        CheckConstraint("key ~ '^[a-z][a-z0-9_]+$'", name="key"),
        CheckConstraint("minimum IS NULL OR maximum IS NULL OR minimum <= maximum", name="bounds"),
        CheckConstraint(
            "CASE value_type "
            "WHEN 'INTEGER' THEN CASE WHEN jsonb_typeof(value) = 'number' "
            "THEN (value::text)::numeric = trunc((value::text)::numeric) "
            "AND (minimum IS NULL OR (value::text)::numeric >= minimum) "
            "AND (maximum IS NULL OR (value::text)::numeric <= maximum) ELSE false END "
            "WHEN 'BOOLEAN' THEN jsonb_typeof(value) = 'boolean' "
            "WHEN 'STRING' THEN jsonb_typeof(value) = 'string' "
            "WHEN 'JSON' THEN jsonb_typeof(value) IN ('object','array') END",
            name="typed_value",
        ),
    )
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[object] = mapped_column(JSONB, nullable=False)
    value_type: Mapped[SettingType] = mapped_column(Enum(SettingType, name="setting_type"))
    minimum: Mapped[float | None] = mapped_column(Numeric(asdecimal=False))
    maximum: Mapped[float | None] = mapped_column(Numeric(asdecimal=False))
    description: Mapped[str] = mapped_column(Text)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )


class AuditLog(Identity, Created, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint("action ~ '^[A-Z][A-Z0-9_]+$'", name="action"),
        CheckConstraint("length(btrim(entity_type)) > 0", name="entity_type"),
        CheckConstraint(
            "details IS NULL OR jsonb_typeof(details) = 'object'", name="details_object"
        ),
        Index("ix_audit_logs_actor_time", "user_id", "created_at"),
        Index("ix_audit_logs_action_time", "action", "created_at"),
        Index("ix_audit_logs_entity_time", "entity_type", "entity_id", "created_at"),
        Index("ix_audit_logs_time", "created_at", "id"),
    )
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[UUID | None]
    details: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    request_id: Mapped[UUID | None]
