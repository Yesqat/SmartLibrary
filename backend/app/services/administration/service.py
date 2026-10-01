"""Admin mutations serialize privilege changes and revoke existing session families."""

from uuid import UUID

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import Principal
from app.core.config import Settings
from app.core.errors import AppError
from app.core.permissions import Permission, authorize
from app.db.enums import SettingType, UserRole, UserStatus
from app.db.models import Borrowing, Reservation, SystemSetting, User
from app.repositories.auth import revoke
from app.schemas.admin import SettingRead, SettingsChange
from app.schemas.auth import UserResponse
from app.services.audit.events import AuditContext, record
from app.services.auth.service import AuthService
from app.services.reservations.service import ACTIVE_LOANS, ACTIVE_RESERVATIONS
from app.services.settings.policy import CirculationPolicy, circulation_policy

# One project-specific transaction lock serializes last-active-admin decisions.
ADMIN_MEMBERSHIP_LOCK = 73412901261877


class AdminService:
    def __init__(
        self, engine: Engine, settings: Settings, context: AuditContext, principal: Principal
    ):
        self.engine, self.context, self.principal = engine, context, principal
        self.auth = AuthService(engine, settings, context)

    def authorize(self, db: Session, permission: Permission) -> User:
        user = self.auth.require_live(db, self.principal.user.id, self.principal.family_id)
        authorize(user.role, permission)
        return user

    def change_user(
        self, identity: UUID, *, role: UserRole | None = None, status: UserStatus | None = None
    ) -> UserResponse:
        with Session(self.engine) as db, db.begin():
            db.execute(select(func.pg_advisory_xact_lock(ADMIN_MEMBERSHIP_LOCK)))
            users = {
                row.id: row
                for row in db.scalars(
                    select(User)
                    .where(User.id.in_([identity, self.principal.user.id]))
                    .order_by(User.id)
                    .with_for_update()
                )
            }
            actor = self.authorize(db, Permission.MANAGE_USERS)
            target = users.get(identity)
            if not target:
                raise AppError("USER_NOT_FOUND", "Пайдаланушы табылмады.", 404)
            new_role, new_status = role or target.role, status or target.status
            if target.role == new_role and target.status == new_status:
                return UserResponse.model_validate(target)
            if (
                target.role == UserRole.ADMIN
                and target.status == UserStatus.ACTIVE
                and (new_role != UserRole.ADMIN or new_status != UserStatus.ACTIVE)
            ):
                other = db.scalar(
                    select(User.id)
                    .where(
                        User.role == UserRole.ADMIN,
                        User.status == UserStatus.ACTIVE,
                        User.id != identity,
                    )
                    .limit(1)
                )
                if not other:
                    raise AppError(
                        "LAST_ACTIVE_ADMIN", "Кемінде бір белсенді әкімші қалуы керек.", 409
                    )
            if target.role == UserRole.READER and new_role != UserRole.READER:
                active_loan = db.scalar(
                    select(Borrowing.id)
                    .where(Borrowing.user_id == identity, Borrowing.status.in_(ACTIVE_LOANS))
                    .limit(1)
                )
                active_reservation = db.scalar(
                    select(Reservation.id)
                    .where(
                        Reservation.user_id == identity, Reservation.status.in_(ACTIVE_RESERVATIONS)
                    )
                    .limit(1)
                )
                if active_loan or active_reservation:
                    raise AppError(
                        "USER_HAS_ACTIVE_CIRCULATION",
                        "Рөлді өзгертпес бұрын белсенді кітаптар мен броньдарды аяқтаңыз.",
                        409,
                    )
            if new_role != target.role:
                record(
                    db,
                    "ROLE_CHANGED",
                    self.context,
                    actor.id,
                    identity,
                    f"{target.role.value}->{new_role.value}",
                    entity_type="USER",
                )
            if new_status != target.status:
                action = (
                    "USER_BLOCKED"
                    if new_status == UserStatus.BLOCKED
                    else (
                        "USER_UNBLOCKED"
                        if target.status == UserStatus.BLOCKED and new_status == UserStatus.ACTIVE
                        else "USER_STATUS_CHANGED"
                    )
                )
                record(
                    db,
                    action,
                    self.context,
                    actor.id,
                    identity,
                    f"{target.status.value}->{new_status.value}",
                    entity_type="USER",
                )
            target.role, target.status = new_role, new_status
            revoke(db, identity)
            record(
                db,
                "SESSION_REVOKED",
                self.context,
                actor.id,
                identity,
                "ADMIN_ACCOUNT_CHANGE",
                entity_type="USER",
            )
            db.flush()
            return UserResponse.model_validate(target)

    def change_settings(self, data: SettingsChange) -> list[SettingRead]:
        with Session(self.engine) as db, db.begin():
            actor = self.authorize(db, Permission.MANAGE_SETTINGS)
            allowed = CirculationPolicy.__annotations__
            changes = {item.key: item for item in data.changes}
            if not set(changes).issubset(allowed):
                raise AppError("VALIDATION_ERROR", "Белгісіз баптау.", 422)
            rows = list(
                db.scalars(
                    select(SystemSetting)
                    .where(SystemSetting.key.in_(allowed))
                    .order_by(SystemSetting.key)
                    .with_for_update()
                )
            )
            if len(rows) != len(allowed):
                raise AppError("SETTINGS_UNAVAILABLE", "Кітапхана баптаулары қолжетімсіз.", 503)
            for row in rows:
                change = changes.get(row.key)
                if not change:
                    continue
                if change.expected_updated_at != row.updated_at:
                    raise AppError(
                        "SETTINGS_CONFLICT", "Баптау өзгертілген. Қайта жүктеп, қайталаңыз.", 409
                    )
                value = change.value
                valid = (row.value_type == SettingType.BOOLEAN and type(value) is bool) or (
                    row.value_type == SettingType.INTEGER
                    and type(value) is int
                    and (row.minimum is None or value >= row.minimum)
                    and (row.maximum is None or value <= row.maximum)
                )
                if not valid:
                    raise AppError(
                        "VALIDATION_ERROR", "Баптау мәні рұқсат етілген ауқымда болуы керек.", 422
                    )
                if row.value != value:
                    record(
                        db,
                        "SYSTEM_SETTING_CHANGED",
                        self.context,
                        actor.id,
                        row.id,
                        f"{row.key}:{row.value}->{value}",
                        entity_type="SYSTEM_SETTING",
                    )
                    row.value, row.updated_by = value, actor.id
            db.flush()
            circulation_policy(db)
            # Trigger-assigned updated_at is the optimistic concurrency version.
            for row in rows:
                db.refresh(row)
            return [SettingRead.model_validate(row) for row in rows]
