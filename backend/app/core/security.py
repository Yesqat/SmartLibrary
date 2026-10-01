"""Credential primitives. Never serialize these values into logs or user schemas."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings
from app.core.errors import AppError

PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, type=Type.ID)
DUMMY_HASH = PASSWORD_HASHER.hash(secrets.token_urlsafe(32))
ISSUER = "smartlibrary"
AUDIENCE = "smartlibrary-api"


def now() -> datetime:
    return datetime.now(UTC)


def verify_password(encoded: str, password: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def sign_access(user_id: UUID, family_id: UUID, settings: Settings) -> str:
    issued = now()
    return jwt.encode(
        {
            "sub": str(user_id),
            "sid": str(family_id),
            "type": "access",
            "iat": issued,
            "nbf": issued,
            "exp": issued + timedelta(seconds=settings.access_token_ttl),
            "iss": ISSUER,
            "aud": AUDIENCE,
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def decode_access(token: str, settings: Settings) -> tuple[UUID, UUID]:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["sub", "sid", "type", "iat", "nbf", "exp", "iss", "aud"]},
        )
        if claims["type"] != "access":
            raise ValueError
        return UUID(claims["sub"]), UUID(claims["sid"])
    except jwt.ExpiredSignatureError:
        raise AppError("TOKEN_EXPIRED", "Сеанс мерзімі аяқталды.", 401) from None
    except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError):
        raise AppError("TOKEN_INVALID", "Сеанс жарамсыз. Қайта кіріңіз.", 401) from None


def keyed_digest(settings: Settings, purpose: str, value: str) -> str:
    return hmac.new(
        settings.jwt_secret.get_secret_value().encode(),
        f"{purpose}:{value}".encode(),
        hashlib.sha256,
    ).hexdigest()
