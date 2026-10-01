"""Atomic Redis fixed windows, keyed with HMAC to keep account identifiers out of Redis."""

from fastapi import Request
from redis import Redis
from redis.exceptions import RedisError

from app.core.auth_http import client_ip
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import keyed_digest

WINDOW = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""


def consume(request: Request, scope: str, identity: str, limit: int, seconds: int) -> None:
    settings: Settings = request.app.state.settings
    redis: Redis = request.app.state.redis
    key = f"{settings.auth_rate_namespace}:{scope}:{keyed_digest(settings, 'rate', identity)}"
    try:
        reply: object = redis.eval(WINDOW, 1, key, str(seconds))
    except RedisError:
        raise AppError(
            "AUTH_SERVICE_UNAVAILABLE", "Кіру қызметі уақытша қолжетімсіз.", 503
        ) from None
    if not isinstance(reply, list) or len(reply) != 2:
        raise AppError("AUTH_SERVICE_UNAVAILABLE", "Кіру қызметі уақытша қолжетімсіз.", 503)
    count, ttl = reply
    if int(count) > limit:
        raise AppError(
            "RATE_LIMIT_EXCEEDED",
            "Сұраныс тым көп. Кейінірек қайталаңыз.",
            429,
            {"Retry-After": str(max(1, int(ttl)))},
        )


def limit_auth(request: Request, action: str, account: str | None = None) -> None:
    settings: Settings = request.app.state.settings
    limits = {
        "login": (settings.auth_login_ip_limit, settings.auth_login_window_seconds),
        "register": (settings.auth_register_limit, 3600),
        "refresh": (settings.auth_refresh_limit, 60),
        "csrf": (240, 60),
        "password": (10, 900),
        "session": (120, 60),
    }
    limit, seconds = limits[action]
    consume(request, action, client_ip(request), limit, seconds)
    if action == "login" and account:
        consume(request, "login-account", account, settings.auth_login_account_limit, seconds)
