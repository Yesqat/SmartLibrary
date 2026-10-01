"""Authentication HTTP contract; cookies never appear in response JSON."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import Authenticated
from app.core.auth_http import (
    audit_context,
    clear_refresh,
    issue_csrf,
    refresh_cookie,
    require_csrf,
    set_refresh,
)
from app.core.rate_limit import limit_auth
from app.repositories.auth import active_roots
from app.schemas.auth import (
    AuthResponse,
    CSRFResponse,
    ErrorResponse,
    LoginInput,
    PasswordChangeInput,
    RegisterInput,
    SessionResponse,
    UserResponse,
)
from app.services.auth.service import AuthService, invalid_refresh

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Auth"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 429, 503)},
)
mutations = [Depends(require_csrf)]


def service(request: Request) -> AuthService:
    return AuthService(request.app.state.db, request.app.state.settings, audit_context(request))


@router.get("/csrf", response_model=CSRFResponse, summary="Get a cookie-bound CSRF proof")
def csrf(request: Request, response: Response) -> CSRFResponse:
    limit_auth(request, "csrf")
    return CSRFResponse(csrf_token=issue_csrf(request, response))


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    dependencies=mutations,
    summary="Register an ACTIVE READER; role/status input is forbidden",
)
def register(data: RegisterInput, request: Request) -> UserResponse:
    limit_auth(request, "register")
    return service(request).register(data)


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=mutations,
    summary="Authenticate and start a revocable session",
)
def login(data: LoginInput, request: Request, response: Response) -> AuthResponse:
    limit_auth(request, "login", str(data.email))
    result = service(request).login(str(data.email), data.password.get_secret_value())
    set_refresh(response, request.app.state.settings, result.refresh_token, result.max_age)
    return result.response


@router.post(
    "/refresh",
    response_model=AuthResponse,
    dependencies=mutations,
    summary="Rotate the HttpOnly refresh credential; reuse revokes the family",
)
def refresh(request: Request, response: Response) -> AuthResponse:
    limit_auth(request, "refresh")
    raw = refresh_cookie(request)
    if not raw:
        raise invalid_refresh()
    result = service(request).refresh(raw)
    set_refresh(response, request.app.state.settings, result.refresh_token, result.max_age)
    return result.response


@router.post(
    "/logout",
    status_code=204,
    dependencies=mutations,
    summary="Revoke the current session family and clear its cookie",
)
def logout(request: Request, response: Response) -> None:
    limit_auth(request, "session")
    service(request).logout(refresh_cookie(request))
    clear_refresh(response, request.app.state.settings)


@router.get("/me", response_model=UserResponse, summary="Get the active authenticated account")
def me(principal: Authenticated) -> UserResponse:
    return UserResponse.model_validate(principal.user)


@router.post(
    "/change-password",
    status_code=204,
    dependencies=mutations,
    summary="Verify current password, change it and revoke all sessions",
)
def change_password(
    data: PasswordChangeInput,
    principal: Authenticated,
    request: Request,
    response: Response,
) -> None:
    limit_auth(request, "password")
    service(request).change_password(principal.user.id, principal.family_id, data)
    clear_refresh(response, request.app.state.settings)


@router.get("/sessions", response_model=list[SessionResponse], summary="List own active sessions")
def sessions(principal: Authenticated, request: Request) -> list[SessionResponse]:
    with Session(request.app.state.db) as db:
        return [
            SessionResponse(
                id=row.id,
                created_at=row.created_at,
                expires_at=row.expires_at,
                current=row.id == principal.family_id,
            )
            for row in active_roots(db, principal.user.id)
        ]


@router.delete(
    "/sessions/{session_id}",
    status_code=204,
    dependencies=mutations,
    summary="Revoke an owned session; other owners' IDs return 404",
)
def revoke_session(
    session_id: UUID,
    principal: Authenticated,
    request: Request,
    response: Response,
) -> None:
    limit_auth(request, "session")
    service(request).revoke_session(principal.user.id, principal.family_id, session_id)
    if session_id == principal.family_id:
        clear_refresh(response, request.app.state.settings)
