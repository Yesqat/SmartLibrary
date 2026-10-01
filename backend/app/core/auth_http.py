"""Cookie/CSRF and trusted ingress handling, kept separate from credential services."""

import ipaddress
import secrets
from uuid import UUID

from fastapi import Request, Response

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import keyed_digest, token_hash
from app.services.audit.events import AuditContext

COOKIE_PATH = "/api/v1/auth"


def cookie_names(settings: Settings) -> tuple[str, str]:
    return (
        ("__Secure-sl_refresh", "__Host-sl_csrf")
        if settings.app_env == "production"
        else ("sl_refresh", "sl_csrf")
    )


def client_ip(request: Request) -> str:
    settings: Settings = request.app.state.settings
    peer = request.client.host if request.client else "127.0.0.1"
    candidate = request.headers.get("x-real-ip", peer) if settings.trust_proxy_headers else peer
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return "127.0.0.1"


def audit_context(request: Request) -> AuditContext:
    return AuditContext(UUID(request.state.request_id), client_ip(request))


def refresh_cookie(request: Request) -> str | None:
    token = request.cookies.get(cookie_names(request.app.state.settings)[0])
    return token if token and len(token) <= 128 else None


def check_origin(request: Request, required: bool = True) -> None:
    origin = request.headers.get("origin")
    settings: Settings = request.app.state.settings
    if (required or origin is not None) and origin not in settings.cors_origins:
        raise AppError("CSRF_FAILED", "Қауіпсіздік тексеруі өтпеді. Бетті жаңартыңыз.", 403)
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise AppError("CSRF_FAILED", "Қауіпсіздік тексеруі өтпеді.", 403)


def csrf_value(settings: Settings, binding: str) -> str:
    return keyed_digest(settings, "csrf", token_hash(binding))


def issue_csrf(request: Request, response: Response) -> str:
    check_origin(request, required=False)
    settings: Settings = request.app.state.settings
    _, preauth = cookie_names(settings)
    binding = refresh_cookie(request) or request.cookies.get(preauth)
    if not binding or len(binding) > 128:
        binding = secrets.token_urlsafe(32)
        response.set_cookie(
            preauth,
            binding,
            max_age=3600,
            httponly=True,
            secure=settings.app_env == "production",
            samesite="strict",
            path="/",
        )
    return csrf_value(settings, binding)


def require_csrf(request: Request) -> None:
    check_origin(request)
    settings: Settings = request.app.state.settings
    binding = refresh_cookie(request) or request.cookies.get(cookie_names(settings)[1], "")
    supplied = request.headers.get("x-csrf-token", "")
    if (
        not binding
        or len(binding) > 128
        or len(supplied) != 64
        or not supplied.isascii()
        or not secrets.compare_digest(supplied, csrf_value(settings, binding))
    ):
        raise AppError("CSRF_FAILED", "Қауіпсіздік тексеруі өтпеді. Бетті жаңартыңыз.", 403)


def set_refresh(response: Response, settings: Settings, token: str, max_age: int) -> None:
    response.set_cookie(
        cookie_names(settings)[0],
        token,
        max_age=max_age,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
    )


def clear_refresh(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        cookie_names(settings)[0],
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
    )
