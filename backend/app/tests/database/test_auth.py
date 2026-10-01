"""Actual API/service tests using isolated PostgreSQL and real Redis namespaces."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from psycopg import sql
from redis import Redis
from sqlalchemy import select, update
from sqlalchemy.orm import Session, undefer

from app.api.dependencies import require_permission
from app.core.config import Settings
from app.core.errors import AppError
from app.core.permissions import Permission
from app.core.security import AUDIENCE, ISSUER, now, token_hash, verify_password
from app.db.enums import UserRole, UserStatus
from app.db.manage import engine, upgrade, url
from app.db.models import AuditLog, RefreshSession, User
from app.main import create_app
from app.services.audit.events import AuditContext
from app.services.auth.service import AuthService

pytestmark = pytest.mark.integration
PASSWORD = "Reader secure password 2026!"
ORIGIN = "http://localhost:8080"


@pytest.fixture(scope="module")
def auth_database_name(test_database_name):
    # Auth commits are separate from the earlier suite's deliberately fixed seed fixture.
    name = "smartlibrary_test_" + uuid4().hex
    owner = engine("admin", "postgres")
    created = False
    try:
        with owner.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.connection.driver_connection.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name))
            )
            created = True
        upgrade(name)
        yield name
    finally:
        if created:
            with owner.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.connection.driver_connection.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
                )
        owner.dispose()


@pytest.fixture(scope="module")
def db_engine(auth_database_name):
    db = engine("migration", auth_database_name)
    yield db
    db.dispose()


@pytest.fixture
def auth_client(auth_database_name, db_engine, settings):
    values = settings.model_dump()
    # Redis credentials are provided to the isolated test service; no production data flush.
    configured = Settings()
    values.update(
        database_url=url("runtime", auth_database_name).render_as_string(hide_password=False),
        redis_url=configured.redis_dsn,
        auth_rate_namespace="smartlibrary:test:auth:" + uuid4().hex,
        auth_login_ip_limit=1000,
        auth_login_account_limit=1000,
        auth_register_limit=1000,
    )
    app = create_app(Settings(**values))

    # HTTP probes exercise the real reusable dependencies; no later-phase production routes.
    def permitted():
        return {"allowed": True}

    for name, permission in (
        ("admin", Permission.MANAGE_USERS),
        ("librarian", Permission.CIRCULATE),
    ):
        app.get(
            f"/test-permissions/{name}", dependencies=[Depends(require_permission(permission))]
        )(permitted)
    with TestClient(app) as client:
        client.headers["Origin"] = ORIGIN
        yield client
        keys = list(app.state.redis.scan_iter(match=app.state.settings.auth_rate_namespace + ":*"))
        if keys:
            app.state.redis.delete(*keys)


def mutate(client, path, data=None, token=None, method="POST"):
    csrf = client.get("/api/v1/auth/csrf")
    assert csrf.status_code == 200
    headers = {"X-CSRF-Token": csrf.json()["csrf_token"]}
    if token:
        headers["Authorization"] = "Bearer " + token
    return client.request(method, "/api/v1/auth" + path, json=data, headers=headers)


def register(client):
    email = uuid4().hex + "@example.com"
    response = mutate(
        client,
        "/register",
        {
            "email": email,
            "password": PASSWORD,
            "first_name": "Айдана",
            "last_name": "Оқырман",
        },
    )
    assert response.status_code == 201, response.text
    return email, response.json()


def login(client, email, password=PASSWORD):
    return mutate(client, "/login", {"email": email, "password": password})


def me(client, token):
    return client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token})


def test_registration_login_current_user_and_hash(auth_client, db_engine):
    email, user = register(auth_client)
    assert user["role"] == "READER" and user["status"] == "ACTIVE"
    assert "password_hash" not in user
    result = login(auth_client, email.upper())
    assert result.status_code == 200
    assert result.json()["token_type"] == "bearer"
    assert result.headers["cache-control"] == "no-store"
    assert "HttpOnly" in result.headers["set-cookie"]
    assert me(auth_client, result.json()["access_token"]).json() == user
    with Session(db_engine) as db:
        row = db.scalar(
            select(User).where(User.id == UUID(user["id"])).options(undefer(User.password_hash))
        )
        assert verify_password(row.password_hash, PASSWORD)
        session = db.scalar(
            select(RefreshSession)
            .where(RefreshSession.user_id == row.id)
            .options(undefer(RefreshSession.token_hash))
        )
        raw = auth_client.cookies["sl_refresh"]
        assert session.token_hash == token_hash(raw) and session.token_hash != raw


@pytest.mark.parametrize("role", ["ADMIN", "LIBRARIAN", "READER"])
def test_public_role_assignment_rejected(auth_client, db_engine, role):
    email = uuid4().hex + "@example.com"
    result = mutate(
        auth_client,
        "/register",
        {
            "email": email,
            "password": PASSWORD,
            "first_name": "A",
            "last_name": "B",
            "role": role,
        },
    )
    assert result.status_code == 422
    with Session(db_engine) as db:
        assert db.scalar(select(User.id).where(User.email == email)) is None


def test_duplicate_email_and_invalid_inputs(auth_client):
    email, _ = register(auth_client)
    body = {"email": email.upper(), "password": PASSWORD, "first_name": "A", "last_name": "B"}
    assert mutate(auth_client, "/register", body).status_code == 409
    for change in (
        {"email": "broken"},
        {"password": "password123456"},
        {"first_name": " "},
        {"status": "ACTIVE"},
    ):
        assert mutate(auth_client, "/register", body | change).status_code == 422


def test_invalid_credentials_are_generic_and_audited(auth_client, db_engine, caplog):
    email, _ = register(auth_client)
    wrong = login(auth_client, email, "incorrect-sensitive-value")
    missing = login(auth_client, uuid4().hex + "@example.com", "incorrect-sensitive-value")
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"
    with Session(db_engine) as db:
        events = list(db.scalars(select(AuditLog).where(AuditLog.action == "LOGIN_FAILED")))
        assert len(events) >= 2
        assert all(event.request_id for event in events)
        assert "incorrect-sensitive-value" not in json.dumps([event.details for event in events])
    assert PASSWORD not in caplog.text and "incorrect-sensitive-value" not in caplog.text


@pytest.mark.parametrize(
    "status,code", [(UserStatus.BLOCKED, "USER_BLOCKED"), (UserStatus.INACTIVE, "ACCOUNT_INACTIVE")]
)
def test_status_rechecked_and_sessions_revoked(auth_client, db_engine, status, code):
    email, user = register(auth_client)
    token = login(auth_client, email).json()["access_token"]
    with db_engine.begin() as connection:
        connection.execute(update(User).where(User.id == UUID(user["id"])).values(status=status))
    result = me(auth_client, token)
    assert result.status_code == 403 and result.json()["error"]["code"] == code
    assert mutate(auth_client, "/refresh").status_code == 401
    assert login(auth_client, email).json()["error"]["code"] == code
    assert login(auth_client, email, "wrong").json()["error"]["code"] == "INVALID_CREDENTIALS"
    with db_engine.begin() as connection:
        connection.execute(
            update(User).where(User.id == UUID(user["id"])).values(status=UserStatus.ACTIVE)
        )
    assert me(auth_client, token).status_code == 401


@pytest.mark.parametrize(
    "role,admin,staff",
    [(UserRole.READER, 403, 403), (UserRole.LIBRARIAN, 403, 200), (UserRole.ADMIN, 200, 403)],
)
def test_backend_roles_and_immediate_demotion(auth_client, db_engine, role, admin, staff):
    email, user = register(auth_client)
    token = login(auth_client, email).json()["access_token"]
    with db_engine.begin() as connection:
        connection.execute(update(User).where(User.id == UUID(user["id"])).values(role=role))
    headers = {"Authorization": "Bearer " + token}
    assert auth_client.get("/test-permissions/admin", headers=headers).status_code == admin
    assert auth_client.get("/test-permissions/librarian", headers=headers).status_code == staff
    assert me(auth_client, token).json()["role"] == role
    with db_engine.begin() as connection:
        connection.execute(
            update(User).where(User.id == UUID(user["id"])).values(role=UserRole.READER)
        )
    assert auth_client.get("/test-permissions/admin", headers=headers).status_code == 403


def test_unauthenticated_and_invalid_access(auth_client):
    assert auth_client.get("/api/v1/auth/me").status_code == 401
    assert auth_client.get("/test-permissions/admin").status_code == 401
    for token in ("broken", jwt.encode({"sub": str(uuid4())}, key="", algorithm="none")):
        assert me(auth_client, token).json()["error"]["code"] == "TOKEN_INVALID"


@pytest.mark.parametrize("status", [UserStatus.BLOCKED, UserStatus.INACTIVE])
def test_refresh_itself_checks_current_account_status(auth_client, db_engine, status):
    email, user = register(auth_client)
    token = login(auth_client, email).json()["access_token"]
    with db_engine.begin() as connection:
        connection.execute(update(User).where(User.id == UUID(user["id"])).values(status=status))
    assert mutate(auth_client, "/refresh").status_code == 403
    with Session(db_engine) as db:
        root = db.scalar(select(RefreshSession).where(RefreshSession.user_id == UUID(user["id"])))
        assert root.revoked_at is not None
    assert me(auth_client, token).status_code == 401


def test_access_cannot_be_transplanted_to_another_users_session(auth_client):
    first, _ = register(auth_client)
    token = login(auth_client, first).json()["access_token"]
    _, other = register(auth_client)
    settings = auth_client.app.state.settings
    claims = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    claims["sub"] = other["id"]
    signed = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    assert me(auth_client, signed).status_code == 401
    forged = jwt.encode(claims, "not-the-configured-signing-key-123456789", algorithm="HS256")
    assert me(auth_client, forged).json()["error"]["code"] == "TOKEN_INVALID"


def test_expired_access_can_refresh_and_logout_revokes_access(auth_client):
    email, _ = register(auth_client)
    token = login(auth_client, email).json()["access_token"]
    settings = auth_client.app.state.settings
    claims = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    claims["exp"] = now() - timedelta(seconds=1)
    expired = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    assert me(auth_client, expired).json()["error"]["code"] == "TOKEN_EXPIRED"
    refreshed = mutate(auth_client, "/refresh")
    assert refreshed.status_code == 200
    assert me(auth_client, refreshed.json()["access_token"]).status_code == 200
    assert mutate(auth_client, "/logout").status_code == 204
    assert "sl_refresh" not in auth_client.cookies
    assert me(auth_client, token).status_code == 401
    assert mutate(auth_client, "/logout").status_code == 204


def test_refresh_rotation_replay_revokes_family(auth_client, db_engine):
    email, user = register(auth_client)
    access = login(auth_client, email).json()["access_token"]
    original = auth_client.cookies["sl_refresh"]
    assert mutate(auth_client, "/refresh").status_code == 200
    current = auth_client.cookies["sl_refresh"]
    assert current != original
    service = AuthService(auth_client.app.state.db, auth_client.app.state.settings, AuditContext())
    with pytest.raises(AppError, match="REFRESH_TOKEN_INVALID"):
        service.refresh(original)
    assert me(auth_client, access).status_code == 401
    assert mutate(auth_client, "/refresh").status_code == 401
    with Session(db_engine) as db:
        rows = list(
            db.scalars(select(RefreshSession).where(RefreshSession.user_id == UUID(user["id"])))
        )
        assert len(rows) == 2 and all(row.revoked_at is not None for row in rows)
        assert len({row.expires_at for row in rows}) == 1


def test_expired_and_invalid_refresh(auth_client, db_engine):
    email, user = register(auth_client)
    login(auth_client, email)
    with db_engine.begin() as connection:
        connection.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == UUID(user["id"]))
            .values(created_at=now() - timedelta(days=3), expires_at=now() - timedelta(days=1))
        )
    assert mutate(auth_client, "/refresh").json()["error"]["code"] == "REFRESH_TOKEN_INVALID"
    auth_client.cookies.set("sl_refresh", "invalid", path="/api/v1/auth")
    assert mutate(auth_client, "/refresh").status_code == 401


def test_sessions_are_owned_and_can_be_revoked(auth_client):
    email_a, _ = register(auth_client)
    token_a = login(auth_client, email_a).json()["access_token"]
    sessions_a = auth_client.get(
        "/api/v1/auth/sessions", headers={"Authorization": "Bearer " + token_a}
    ).json()
    assert len(sessions_a) == 1 and sessions_a[0]["current"]
    email_b, _ = register(auth_client)
    token_b = login(auth_client, email_b).json()["access_token"]
    target = sessions_a[0]["id"]
    assert (
        mutate(auth_client, "/sessions/" + target, token=token_b, method="DELETE").status_code
        == 404
    )
    assert me(auth_client, token_a).status_code == 200
    assert (
        mutate(auth_client, "/sessions/" + target, token=token_a, method="DELETE").status_code
        == 204
    )
    assert me(auth_client, token_a).status_code == 401
    assert me(auth_client, token_b).status_code == 200


def test_password_change_revokes_every_session(auth_client, db_engine):
    email, user = register(auth_client)
    token1 = login(auth_client, email).json()["access_token"]
    token2 = login(auth_client, email).json()["access_token"]
    new = "Changed secure password 2026!"
    assert (
        mutate(
            auth_client,
            "/change-password",
            {"current_password": "wrong", "new_password": new},
            token1,
        ).status_code
        == 401
    )
    assert (
        mutate(
            auth_client,
            "/change-password",
            {"current_password": PASSWORD, "new_password": PASSWORD},
            token1,
        ).status_code
        == 422
    )
    assert (
        mutate(
            auth_client,
            "/change-password",
            {"current_password": PASSWORD, "new_password": new},
            token1,
        ).status_code
        == 204
    )
    assert me(auth_client, token1).status_code == me(auth_client, token2).status_code == 401
    assert login(auth_client, email).status_code == 401
    assert login(auth_client, email, new).status_code == 200
    with Session(db_engine) as db:
        event = db.scalar(
            select(AuditLog).where(
                AuditLog.user_id == UUID(user["id"]), AuditLog.action == "PASSWORD_CHANGED"
            )
        )
        assert event is not None and event.details == {}


def test_csrf_protects_login_refresh_logout_password_and_revocation(auth_client):
    email, _ = register(auth_client)
    access = login(auth_client, email).json()["access_token"]
    raw = auth_client.cookies["sl_refresh"]
    csrf = auth_client.get("/api/v1/auth/csrf").json()["csrf_token"]
    for path in ("login", "register", "refresh", "logout", "change-password"):
        response = auth_client.post(
            "/api/v1/auth/" + path, json={}, headers={"Authorization": "Bearer " + access}
        )
        assert response.status_code == 403
    assert (
        auth_client.post(
            "/api/v1/auth/refresh", headers={"Origin": "https://evil.invalid", "X-CSRF-Token": csrf}
        ).status_code
        == 403
    )
    assert (
        auth_client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "wrong"}).status_code
        == 403
    )
    assert (
        auth_client.get("/api/v1/auth/csrf", headers={"Origin": "https://evil.invalid"}).status_code
        == 403
    )
    assert auth_client.cookies["sl_refresh"] == raw
    assert mutate(auth_client, "/refresh").status_code == 200
    assert (
        auth_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 403
    )


def test_rate_limit_is_real_redis_and_ignores_spoofed_headers(auth_client):
    settings = auth_client.app.state.settings
    settings.auth_login_ip_limit = 2
    for i in range(2):
        auth_client.headers["X-Real-IP"] = f"192.0.2.{i}"
        assert login(auth_client, f"absent{i}@example.com").status_code == 401
    auth_client.headers["X-Real-IP"] = "192.0.2.254"
    response = login(auth_client, "another@example.com")
    assert response.status_code == 429 and int(response.headers["retry-after"]) > 0
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_account_register_and_refresh_limits(auth_client):
    settings = auth_client.app.state.settings
    settings.auth_login_account_limit = 1
    email, _ = register(auth_client)
    assert login(auth_client, email, "wrong").status_code == 401
    assert login(auth_client, email).status_code == 429
    settings.auth_register_limit = 1
    assert (
        mutate(
            auth_client,
            "/register",
            {
                "email": "limited@example.com",
                "password": PASSWORD,
                "first_name": "A",
                "last_name": "B",
            },
        ).status_code
        == 429
    )
    settings.auth_refresh_limit = 1
    assert mutate(auth_client, "/refresh").status_code == 401
    assert mutate(auth_client, "/refresh").status_code == 429


def test_redis_failure_closes_auth_safely_but_liveness_works(auth_client):
    csrf = auth_client.get("/api/v1/auth/csrf").json()["csrf_token"]
    original = auth_client.app.state.redis
    unavailable = Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.2, socket_timeout=0.2)
    auth_client.app.state.redis = unavailable
    try:
        response = auth_client.post(
            "/api/v1/auth/login",
            json={"email": "reader@example.com", "password": PASSWORD},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "AUTH_SERVICE_UNAVAILABLE"
        assert auth_client.get("/health").status_code == 200
    finally:
        unavailable.close()
        auth_client.app.state.redis = original


def test_concurrent_refresh_has_one_success_and_replay_revokes(auth_client):
    email, _ = register(auth_client)
    token = login(auth_client, email).json()["access_token"]
    raw = auth_client.cookies["sl_refresh"]
    barrier = Barrier(2)

    def rotate():
        barrier.wait(timeout=5)
        try:
            AuthService(
                auth_client.app.state.db, auth_client.app.state.settings, AuditContext()
            ).refresh(raw)
            return 200
        except AppError as exc:
            return exc.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: rotate(), range(2))) == [200, 401]
    assert me(auth_client, token).status_code == 401


def test_registration_rolls_back_if_audit_write_fails(auth_client, db_engine, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("injected audit persistence failure")

    monkeypatch.setattr("app.services.auth.service.record", fail)
    email = uuid4().hex + "@example.com"
    response = mutate(
        auth_client,
        "/register",
        {"email": email, "password": PASSWORD, "first_name": "A", "last_name": "B"},
    )
    assert response.status_code == 500
    assert "injected" not in response.text
    with Session(db_engine) as db:
        assert db.scalar(select(User.id).where(User.email == email)) is None
