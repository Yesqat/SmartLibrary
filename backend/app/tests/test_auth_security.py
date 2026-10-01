from datetime import timedelta
from uuid import uuid4

import jwt
import pytest
from pydantic import SecretStr, ValidationError
from starlette.responses import Response

from app.core.auth_http import cookie_names, set_refresh
from app.core.errors import AppError
from app.core.permissions import ROLE_PERMISSIONS, Permission, authorize, authorize_owner
from app.core.security import (
    AUDIENCE,
    ISSUER,
    PASSWORD_HASHER,
    decode_access,
    now,
    sign_access,
    verify_password,
)
from app.db.enums import UserRole
from app.schemas.auth import RegisterInput, validate_new_password


def test_argon2id_and_unicode_passwords():
    password = "Кітапхана! Құпия 2026"
    encoded = PASSWORD_HASHER.hash(password)
    assert encoded.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert verify_password(encoded, password)
    assert not verify_password(encoded, "wrong")
    assert not verify_password("broken", password)


@pytest.mark.parametrize("value", ["short", "password123456", "a" * 20, " password-is-long "])
def test_weak_passwords_are_rejected(value):
    with pytest.raises(ValueError):
        validate_new_password(SecretStr(value))


@pytest.mark.parametrize("field", ["role", "status", "password_hash", "id", "created_at"])
def test_registration_is_an_allowlist(field):
    with pytest.raises(ValidationError):
        RegisterInput.model_validate(
            {
                "email": "reader@example.com",
                "password": "A strong password 2026!",
                "first_name": "Айдана",
                "last_name": "Оқырман",
                field: "ADMIN",
            }
        )


def test_access_token_has_minimal_claims(settings):
    user, family = uuid4(), uuid4()
    token = sign_access(user, family, settings)
    assert decode_access(token, settings) == (user, family)
    claims = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    assert set(claims) == {"sub", "sid", "type", "iat", "nbf", "exp", "iss", "aud"}


@pytest.mark.parametrize(
    "change,code",
    [
        ({"exp": now() - timedelta(seconds=1)}, "TOKEN_EXPIRED"),
        ({"aud": "elsewhere"}, "TOKEN_INVALID"),
        ({"iss": "elsewhere"}, "TOKEN_INVALID"),
        ({"type": "refresh"}, "TOKEN_INVALID"),
        ({"sub": "not-uuid"}, "TOKEN_INVALID"),
        ({"nbf": now() + timedelta(days=1)}, "TOKEN_INVALID"),
    ],
)
def test_access_claim_validation(settings, change, code):
    claims = {
        "sub": str(uuid4()),
        "sid": str(uuid4()),
        "type": "access",
        "iat": now(),
        "nbf": now(),
        "exp": now() + timedelta(minutes=10),
        "iss": ISSUER,
        "aud": AUDIENCE,
    }
    claims.update(change)
    token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(AppError) as exc:
        decode_access(token, settings)
    assert exc.value.code == code


@pytest.mark.parametrize("role", list(UserRole))
@pytest.mark.parametrize("permission", list(Permission))
def test_exact_permission_map(role, permission):
    expected = {
        UserRole.READER: {"read_personal", "reserve"},
        UserRole.LIBRARIAN: {"manage_catalog", "circulate", "view_readers"},
        UserRole.ADMIN: {
            "manage_catalog",
            "manage_users",
            "manage_settings",
            "view_analytics",
            "view_audit",
        },
    }
    assert set(ROLE_PERMISSIONS[role]) == expected[role]
    if permission.value in expected[role]:
        authorize(role, permission)
    else:
        with pytest.raises(AppError, match="FORBIDDEN"):
            authorize(role, permission)


def test_owner_check_has_no_implicit_staff_bypass():
    user = uuid4()
    authorize_owner(user, user)
    with pytest.raises(AppError, match="NOT_FOUND"):
        authorize_owner(user, uuid4())


def test_production_cookie_flags(settings):
    production = settings.model_copy(update={"app_env": "production"})
    response = Response()
    set_refresh(response, production, "test-token", 120)
    cookie = response.headers["set-cookie"]
    assert cookie_names(production)[0] == "__Secure-sl_refresh"
    for flag in ("HttpOnly", "Secure", "SameSite=strict", "Path=/api/v1/auth", "Max-Age=120"):
        assert flag in cookie
