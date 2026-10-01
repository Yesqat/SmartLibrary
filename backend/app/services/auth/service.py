"""Transactional authentication. User locks serialize rotation/revocation/password changes."""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    DUMMY_HASH,
    PASSWORD_HASHER,
    new_refresh_token,
    now,
    sign_access,
    token_hash,
    verify_password,
)
from app.db.enums import UserRole, UserStatus
from app.db.models.users import RefreshSession, User
from app.repositories import auth as repository
from app.schemas.auth import AuthResponse, PasswordChangeInput, RegisterInput, UserResponse
from app.services.audit.events import AuditContext, record


def account_error(user: User) -> AppError | None:
    if user.status == UserStatus.BLOCKED:
        return AppError("USER_BLOCKED", "Тіркелгі бұғатталған. Кітапханаға хабарласыңыз.", 403)
    if user.status != UserStatus.ACTIVE:
        return AppError("ACCOUNT_INACTIVE", "Тіркелгі белсенді емес.", 403)
    return None


def invalid_refresh() -> AppError:
    return AppError("REFRESH_TOKEN_INVALID", "Сеанс аяқталды. Қайта кіріңіз.", 401)


@dataclass(frozen=True, repr=False)
class Credentials:
    response: AuthResponse
    refresh_token: str
    max_age: int


class AuthService:
    def __init__(self, engine: Engine, settings: Settings, context: AuditContext) -> None:
        self.engine, self.settings, self.context = engine, settings, context

    def register(self, data: RegisterInput) -> UserResponse:
        password_hash = PASSWORD_HASHER.hash(data.password.get_secret_value())
        try:
            with Session(self.engine, expire_on_commit=False) as db, db.begin():
                user = User(
                    first_name=data.first_name,
                    last_name=data.last_name,
                    email=str(data.email),
                    phone=data.phone,
                    password_hash=password_hash,
                    role=UserRole.READER,
                    status=UserStatus.ACTIVE,
                )
                db.add(user)
                db.flush()
                record(db, "USER_REGISTERED", self.context, user.id, user.id)
                response = UserResponse.model_validate(user)
            return response
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise AppError("EMAIL_ALREADY_EXISTS", "Бұл email тіркелген.", 409) from None
            raise

    def credentials(self, user: User, row: RefreshSession, raw: str) -> Credentials:
        return Credentials(
            AuthResponse(
                access_token=sign_access(user.id, row.family_id, self.settings),
                expires_in=self.settings.access_token_ttl,
                user=UserResponse.model_validate(user),
            ),
            raw,
            max(1, int((row.expires_at - now()).total_seconds())),
        )

    def login(self, email: str, password: str) -> Credentials:
        failure: AppError | None = None
        result: Credentials | None = None
        with Session(self.engine, expire_on_commit=False) as db, db.begin():
            user = repository.user_by_email(db, email)
            valid = verify_password(user.password_hash if user else DUMMY_HASH, password)
            if not user or not valid:
                record(db, "LOGIN_FAILED", self.context, reason="INVALID_CREDENTIALS")
                failure = AppError("INVALID_CREDENTIALS", "Email немесе құпиясөз қате.", 401)
            elif (failure := account_error(user)) is not None:
                repository.revoke(db, user.id)
                record(db, "LOGIN_FAILED", self.context, user.id, reason=failure.code)
            else:
                if PASSWORD_HASHER.check_needs_rehash(user.password_hash):
                    user.password_hash = PASSWORD_HASHER.hash(password)
                identity, raw = uuid4(), new_refresh_token()
                row = RefreshSession(
                    id=identity,
                    user_id=user.id,
                    family_id=identity,
                    token_hash=token_hash(raw),
                    expires_at=now() + timedelta(seconds=self.settings.refresh_token_ttl),
                )
                db.add(row)
                db.flush()
                record(db, "LOGIN_SUCCEEDED", self.context, user.id, row.family_id)
                result = self.credentials(user, row, raw)
        if failure:
            raise failure
        assert result is not None
        return result

    def refresh(self, raw: str) -> Credentials:
        failure: AppError | None = None
        result: Credentials | None = None
        with Session(self.engine, expire_on_commit=False) as db, db.begin():
            row = repository.refresh_by_hash(db, token_hash(raw))
            if row is None:
                failure = invalid_refresh()
            else:
                user = repository.lock_user(db, row.user_id)
                assert user is not None
                # Another request may have consumed this row while we waited for the user lock.
                db.refresh(row)
                root = db.get(RefreshSession, row.family_id)
                assert root is not None
                if row.consumed_at is not None:
                    repository.revoke(db, user.id, row.family_id)
                    record(db, "REFRESH_REUSE_DETECTED", self.context, user.id, row.family_id)
                    failure = invalid_refresh()
                elif row.revoked_at or root.revoked_at or row.expires_at <= now():
                    failure = invalid_refresh()
                elif (failure := account_error(user)) is not None:
                    repository.revoke(db, user.id)
                    record(db, "SESSION_REVOKED", self.context, user.id, reason=failure.code)
                else:
                    replacement = new_refresh_token()
                    row.consumed_at = now()
                    child = RefreshSession(
                        user_id=user.id,
                        family_id=row.family_id,
                        parent_id=row.id,
                        token_hash=token_hash(replacement),
                        expires_at=root.expires_at,
                    )
                    db.add(child)
                    db.flush()
                    result = self.credentials(user, child, replacement)
        if failure:
            raise failure
        assert result is not None
        return result

    def logout(self, raw: str | None) -> None:
        if not raw:
            return
        with Session(self.engine) as db, db.begin():
            row = repository.refresh_by_hash(db, token_hash(raw))
            if row:
                repository.lock_user(db, row.user_id)
                repository.revoke(db, row.user_id, row.family_id)
                record(db, "LOGOUT", self.context, row.user_id, row.family_id)

    def require_live(self, db: Session, user_id: UUID, family_id: UUID) -> User:
        user = repository.lock_user(db, user_id)
        row = db.get(RefreshSession, family_id)
        if (
            not user
            or not row
            or row.user_id != user_id
            or row.revoked_at
            or row.expires_at <= now()
        ):
            raise AppError("UNAUTHORIZED", "Қайта кіріңіз.", 401)
        if failure := account_error(user):
            raise failure
        return user

    def change_password(self, user_id: UUID, family_id: UUID, data: PasswordChangeInput) -> None:
        failure: AppError | None = None
        with Session(self.engine) as db, db.begin():
            user = self.require_live(db, user_id, family_id)
            if not verify_password(user.password_hash, data.current_password.get_secret_value()):
                record(
                    db,
                    "PASSWORD_CHANGE_FAILED",
                    self.context,
                    user.id,
                    reason="INVALID_CREDENTIALS",
                )
                failure = AppError("INVALID_CREDENTIALS", "Қазіргі құпиясөз қате.", 401)
            elif verify_password(user.password_hash, data.new_password.get_secret_value()):
                failure = AppError("PASSWORD_UNCHANGED", "Жаңа құпиясөз басқаша болуы керек.", 422)
            else:
                user.password_hash = PASSWORD_HASHER.hash(data.new_password.get_secret_value())
                repository.revoke(db, user.id)
                record(db, "PASSWORD_CHANGED", self.context, user.id, user.id)
        if failure:
            raise failure

    def revoke_session(self, user_id: UUID, current_family: UUID, target: UUID) -> None:
        with Session(self.engine) as db, db.begin():
            self.require_live(db, user_id, current_family)
            row = db.get(RefreshSession, target)
            if row is None or row.user_id != user_id or row.parent_id is not None:
                raise AppError("SESSION_NOT_FOUND", "Сеанс табылмады.", 404)
            repository.revoke(db, user_id, target)
            record(db, "SESSION_REVOKED", self.context, user_id, target)
