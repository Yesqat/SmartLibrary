"""Admin mutations, live revocation and settings verified against PostgreSQL/Redis."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.enums import UserRole, UserStatus
from app.db.models import AuditLog, RefreshSession, SystemSetting, User
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy
from app.tests.database.domain.test_reservations import reserve
from app.tests.database.test_auth import login

pytestmark = pytest.mark.integration
ROOT = BASE + "/admin"


@pytest.mark.parametrize("role", [UserRole.READER, UserRole.LIBRARIAN])
def test_nonadmins_cannot_read_manage_or_elevate(client, actor, role):
    user, _ = actor(role)
    for path in [
        "/users",
        "/settings",
        "/audit-logs",
        "/dashboard",
        "/inventory",
        "/borrowings",
        "/reservations",
        "/librarians",
    ]:
        assert client.get(ROOT + path).status_code == 403
    assert (
        client.patch(ROOT + f"/users/{user['id']}/role", json={"role": "ADMIN"}).status_code == 403
    )
    assert (
        client.patch(ROOT + f"/users/{user['id']}/status", json={"status": "BLOCKED"}).status_code
        == 403
    )


def test_role_change_revokes_all_sessions_and_is_audited(client, actor, domain_db):
    user, old_token = actor(UserRole.READER)
    assert login(client, user["email"]).status_code == 200
    admin, _ = actor(UserRole.ADMIN)
    changed = client.patch(ROOT + f"/users/{user['id']}/role", json={"role": "LIBRARIAN"})
    assert changed.status_code == 200 and changed.json()["role"] == "LIBRARIAN"
    assert "password_hash" not in changed.text
    assert (
        client.get(BASE + "/auth/me", headers={"Authorization": "Bearer " + old_token}).status_code
        == 401
    )
    with Session(domain_db) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(RefreshSession)
                .where(RefreshSession.user_id == user["id"], RefreshSession.revoked_at.is_(None))
            )
            == 0
        )
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == user["id"], AuditLog.action == "ROLE_CHANGED"
            )
        )
        assert audit.user_id == UUID(admin["id"]) and audit.details == {
            "reason": "READER->LIBRARIAN"
        }
    fresh = login(client, user["email"])
    assert fresh.status_code == 200 and fresh.json()["user"]["role"] == "LIBRARIAN"


def test_block_unblock_inactive_enforced_and_repeat_does_not_audit_twice(client, actor, domain_db):
    user, _ = actor(UserRole.READER)
    _, admin_token = actor(UserRole.ADMIN)
    path = ROOT + f"/users/{user['id']}/status"
    for status in ["BLOCKED", "BLOCKED"]:
        assert client.patch(path, json={"status": status}).status_code == 200
    with Session(domain_db) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "USER_BLOCKED", AuditLog.entity_id == user["id"])
            )
            == 1
        )
    assert login(client, user["email"]).status_code == 403
    client.headers["Authorization"] = "Bearer " + admin_token
    assert client.patch(path, json={"status": "INACTIVE"}).status_code == 200
    assert login(client, user["email"]).status_code == 403
    client.headers["Authorization"] = "Bearer " + admin_token
    assert client.patch(path, json={"status": "ACTIVE"}).status_code == 200
    assert login(client, user["email"]).status_code == 200


def test_concurrent_self_demotion_cannot_remove_last_active_admin(client, actor, domain_db):
    first, first_token = actor(UserRole.ADMIN)
    second, second_token = actor(UserRole.ADMIN)
    with domain_db.begin() as db:
        prior = list(
            db.execute(
                select(User.id, User.status).where(
                    User.role == UserRole.ADMIN, User.id.not_in([first["id"], second["id"]])
                )
            )
        )
        db.execute(
            update(User)
            .where(User.id.in_([row.id for row in prior]))
            .values(status=UserStatus.INACTIVE)
        )
    try:
        barrier = Barrier(2)

        def demote(item):
            user, token = item
            barrier.wait(timeout=10)
            return client.patch(
                ROOT + f"/users/{user['id']}/role",
                json={"role": "READER"},
                headers={"Authorization": "Bearer " + token},
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(demote, [(first, first_token), (second, second_token)]))
        assert sorted(r.status_code for r in results) == [200, 409]
        with Session(domain_db) as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(User)
                    .where(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE)
                )
                == 1
            )
    finally:
        with domain_db.begin() as db:
            for row in prior:
                db.execute(update(User).where(User.id == row.id).values(status=row.status))


def test_active_circulation_prevents_reader_role_change(staff, actor):
    book = create_book(staff)
    user, reader_token = actor(UserRole.READER)
    reservation = reserve(staff, book)
    actor(UserRole.ADMIN)
    path = ROOT + f"/users/{user['id']}/role"
    assert (
        staff.patch(path, json={"role": "LIBRARIAN"}).json()["error"]["code"]
        == "USER_HAS_ACTIVE_CIRCULATION"
    )
    assert (
        staff.post(
            BASE + f"/reservations/{reservation['id']}/cancel",
            headers={"Authorization": "Bearer " + reader_token},
        ).status_code
        == 200
    )
    assert staff.patch(path, json={"role": "LIBRARIAN"}).status_code == 200


def test_settings_atomic_type_bounds_unknown_and_stale_rejected(client, actor, domain_db):
    actor(UserRole.ADMIN)
    rows = client.get(ROOT + "/settings").json()
    originals = {row["key"]: row["value"] for row in rows}
    limit = next(row for row in rows if row["key"] == "max_books_per_user")
    change = {"key": limit["key"], "value": 7, "expected_updated_at": limit["updated_at"]}
    try:
        for invalid in [-1, 101, True, "8"]:
            result = client.patch(
                ROOT + "/settings", json={"changes": [{**change, "value": invalid}]}
            )
            assert result.status_code == 422
        assert (
            client.patch(
                ROOT + "/settings", json={"changes": [{**change, "key": "jwt_secret"}]}
            ).status_code
            == 422
        )
        assert (
            client.patch(ROOT + "/settings", json={"changes": [change, change]}).status_code == 422
        )
        assert (
            client.patch(
                ROOT + "/settings", json={"changes": [change, {**change, "key": "unknown"}]}
            ).status_code
            == 422
        )
        assert (
            next(
                row for row in client.get(ROOT + "/settings").json() if row["key"] == limit["key"]
            )["value"]
            == limit["value"]
        )
        response = client.patch(ROOT + "/settings", json={"changes": [change]})
        assert response.status_code == 200, response.text
        assert (
            client.patch(ROOT + "/settings", json={"changes": [{**change, "value": 8}]}).status_code
            == 409
        )
    finally:
        with domain_db.begin() as db:
            for key, value in originals.items():
                db.execute(
                    update(SystemSetting).where(SystemSetting.key == key).values(value=value)
                )


def test_changed_settings_apply_to_next_reservation_without_restart(staff, actor, domain_db):
    book = create_book(staff)
    create_copy(staff, book)
    actor(UserRole.ADMIN)
    setting = next(
        row
        for row in staff.get(ROOT + "/settings").json()
        if row["key"] == "reservation_hold_hours"
    )
    try:
        assert (
            staff.patch(
                ROOT + "/settings",
                json={
                    "changes": [
                        {
                            "key": setting["key"],
                            "value": 3,
                            "expected_updated_at": setting["updated_at"],
                        }
                    ]
                },
            ).status_code
            == 200
        )
        actor(UserRole.READER)
        row = reserve(staff, book)
        from datetime import datetime

        assert (
            datetime.fromisoformat(row["expires_at"]) - datetime.fromisoformat(row["ready_at"])
        ).total_seconds() == 10800
    finally:
        with domain_db.begin() as db:
            db.execute(
                update(SystemSetting)
                .where(SystemSetting.key == setting["key"])
                .values(value=setting["value"])
            )


def test_admin_read_models_filters_and_audit_read_only(staff, actor):
    book = create_book(staff)
    copy = create_copy(staff, book)
    admin, _ = actor(UserRole.ADMIN)
    assert (
        staff.get(
            ROOT + "/users", params={"q": admin["id"], "role": "ADMIN", "status": "ACTIVE"}
        ).json()["total"]
        == 1
    )
    inventory = staff.get(
        ROOT + "/inventory", params={"q": copy["inventory_number"], "status": "AVAILABLE"}
    ).json()
    assert inventory["total"] == 1 and inventory["items"][0]["book_title"] == book["title"]
    summary = staff.get(ROOT + "/dashboard").json()
    assert summary["physical_copies"] >= 1 and summary["available_copies"] >= 1
    assert (
        staff.get(ROOT + "/audit-logs?date_from=2026-12-01&date_to=2026-01-01").status_code == 422
    )
    audit = staff.get(
        ROOT + "/audit-logs",
        params={"actor": admin["id"], "action": "USER_REGISTERED", "page_size": 1},
    ).json()
    assert audit["total"] == 1 and "ip_address" not in audit["items"][0]
    assert staff.delete(ROOT + "/audit-logs").status_code == 405
    assert staff.patch(ROOT + "/audit-logs", json={}).status_code == 405
    assert (
        staff.patch(ROOT + f"/users/{admin['id']}/role", json={"role": "SUPERADMIN"}).status_code
        == 422
    )
    assert (
        staff.patch(ROOT + f"/users/{uuid4()}/status", json={"status": "BLOCKED"}).status_code
        == 404
    )
