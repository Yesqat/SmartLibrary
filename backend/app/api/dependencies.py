"""Reusable authentication/authorization for routes and future controlled backend tools."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth_http import audit_context
from app.core.errors import AppError
from app.core.permissions import Permission, authorize
from app.core.security import decode_access, now
from app.db.models.users import RefreshSession, User
from app.repositories.auth import revoke
from app.services.audit.events import record
from app.services.auth.service import account_error

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user: User
    family_id: UUID


def current_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    if not credentials:
        raise AppError("UNAUTHORIZED", "Жүйеге кіріңіз.", 401, {"WWW-Authenticate": "Bearer"})
    user_id, family_id = decode_access(credentials.credentials, request.app.state.settings)
    with Session(request.app.state.db, expire_on_commit=False) as db:
        user = db.get(User, user_id)
        root = db.get(RefreshSession, family_id)
        if (
            not user
            or not root
            or root.user_id != user_id
            or root.parent_id is not None
            or root.revoked_at is not None
            or root.expires_at <= now()
        ):
            raise AppError("UNAUTHORIZED", "Сеанс аяқталды. Қайта кіріңіз.", 401)
        if failure := account_error(user):
            revoke(db, user_id)
            record(db, "SESSION_REVOKED", audit_context(request), user_id, reason=failure.code)
            db.commit()
            raise failure
        return Principal(user, family_id)


Authenticated = Annotated[Principal, Depends(current_principal)]


def optional_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal | None:
    return current_principal(request, credentials) if credentials else None


OptionalPrincipal = Annotated[Principal | None, Depends(optional_principal)]


def require_permission(permission: Permission) -> Callable[..., Principal]:
    def dependency(principal: Authenticated) -> Principal:
        authorize(principal.user.role, permission)
        return principal

    return dependency
