"""Real operational queries and manual verification share circulation invariants."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.security import now
from app.db.enums import UserRole, UserStatus
from app.db.models import AuditLog, BookCopy, Borrowing, Reservation, User
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy
from app.tests.database.domain.test_reservations import reserve

pytestmark = pytest.mark.integration
ROOT = BASE + "/librarian"


def test_manual_verification_does_not_issue_and_cannot_reuse(staff, actor, domain_db):
    _, token = actor()
    book = create_book(staff)
    copy = create_copy(staff, book)
    actor(UserRole.READER)
    reservation = reserve(staff, book)
    staff.headers["Authorization"] = "Bearer " + token
    response = staff.post(
        ROOT + "/reservations/verify-number",
        json={"reservation_number": reservation["reservation_number"]},
    )
    assert response.status_code == 200, response.text
    preview = response.json()
    assert "qr_token" not in preview and preview["book_copy_id"] == copy["id"]
    with Session(domain_db) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Borrowing)
                .where(Borrowing.book_copy_id == copy["id"])
            )
            == 0
        )
        assert db.get(BookCopy, UUID(copy["id"])).status.value == "RESERVED"
        assert db.scalar(
            select(AuditLog.id).where(
                AuditLog.action == "RESERVATION_MANUALLY_VERIFIED",
                AuditLog.entity_id == reservation["id"],
            )
        )
    issued = staff.post(
        ROOT + f"/reservations/{reservation['id']}/issue",
        json={"verification_token": preview["verification_token"]},
    )
    assert issued.status_code == 200
    assert (
        staff.post(
            ROOT + "/reservations/verify-number",
            json={"reservation_number": reservation["reservation_number"]},
        ).status_code
        == 409
    )


@pytest.mark.parametrize("change", ["expired", "blocked", "cancelled"])
def test_manual_rejects_expired_blocked_cancelled(staff, actor, domain_db, change):
    _, token = actor()
    book = create_book(staff)
    create_copy(staff, book)
    reader, _ = actor(UserRole.READER)
    row = reserve(staff, book)
    if change == "cancelled":
        assert staff.post(BASE + f"/reservations/{row['id']}/cancel").status_code == 200
    else:
        with domain_db.begin() as db:
            if change == "blocked":
                db.execute(
                    update(User).where(User.id == reader["id"]).values(status=UserStatus.BLOCKED)
                )
            else:
                db.execute(
                    update(Reservation)
                    .where(Reservation.id == row["id"])
                    .values(
                        reserved_at=now() - timedelta(days=3),
                        ready_at=now() - timedelta(days=2),
                        expires_at=now() - timedelta(days=1),
                    )
                )
    response = staff.post(
        ROOT + "/reservations/verify-number",
        json={"reservation_number": row["reservation_number"]},
        headers={"Authorization": "Bearer " + token},
    )
    assert response.status_code in (403, 409)


def test_reader_details_limits_search_and_secret_minimization(staff, actor, domain_db):
    _, librarian = actor()
    reader, _ = actor(UserRole.READER)
    staff.headers["Authorization"] = "Bearer " + librarian
    result = staff.get(ROOT + f"/readers/{reader['id']}")
    assert result.status_code == 200
    data = result.json()
    assert data["borrowing_limit"] > 0 and data["can_borrow"] is True
    assert "password_hash" not in result.text and "conversation" not in result.text
    assert staff.get(ROOT + "/readers", params={"q": reader["id"]}).json()["total"] == 1
    with domain_db.begin() as db:
        db.execute(update(User).where(User.id == reader["id"]).values(status=UserStatus.BLOCKED))
    assert staff.get(ROOT + f"/readers/{reader['id']}").json()["restriction_code"] == "USER_BLOCKED"
    assert (
        staff.get(ROOT + "/readers", params={"q": reader["email"], "status": "ACTIVE"}).json()[
            "total"
        ]
        == 0
    )
    assert staff.get(ROOT + f"/readers/{uuid4()}/borrowings").status_code == 404


def test_dashboard_actual_counts_overdue_filters_and_history(staff, actor, domain_db):
    _, librarian = actor()
    before = staff.get(ROOT + "/dashboard").json()
    book = create_book(staff)
    copy = create_copy(staff, book)
    reader, _ = actor(UserRole.READER)
    staff.headers["Authorization"] = "Bearer " + librarian
    loan = staff.post(
        ROOT + "/borrowings",
        json={"user_id": reader["id"], "book_copy_id": copy["id"], "idempotency_key": str(uuid4())},
    ).json()
    after = staff.get(ROOT + "/dashboard").json()
    assert after["issued_today"] == before["issued_today"] + 1
    assert any(item["entity_id"] == loan["id"] for item in after["recent_operations"])
    assert all(
        "details" not in item and "ip_address" not in item for item in after["recent_operations"]
    )
    with domain_db.begin() as db:
        db.execute(
            update(Borrowing)
            .where(Borrowing.id == loan["id"])
            .values(borrowed_at=now() - timedelta(days=20), due_at=now() - timedelta(days=3))
        )
    query = {"q": copy["inventory_number"], "minimum_days": 2, "order": "oldest"}
    overdue = staff.get(ROOT + "/borrowings/overdue", params=query).json()
    assert overdue["total"] == 1 and overdue["items"][0]["is_overdue"]
    assert (
        staff.get(ROOT + "/borrowings/overdue", params={**query, "minimum_days": 4}).json()["total"]
        == 0
    )
    assert staff.get(ROOT + f"/readers/{reader['id']}").json()["overdue_borrowings"] == 1
    assert staff.get(ROOT + f"/readers/{reader['id']}/borrowings").json()["total"] == 1
    assert (
        staff.post(
            ROOT + f"/borrowings/{loan['id']}/return", json={"condition": "GOOD"}
        ).status_code
        == 200
    )
    assert staff.get(ROOT + f"/readers/{reader['id']}/borrowings?active=false").json()["total"] == 1
    assert staff.get(ROOT + "/dashboard").json()["returned_today"] == before["returned_today"] + 1


def test_reservation_filtering_no_qr_secrets(staff, actor):
    _, librarian = actor()
    book = create_book(staff)
    reader, _ = actor(UserRole.READER)
    reservation = reserve(staff, book)
    staff.headers["Authorization"] = "Bearer " + librarian
    response = staff.get(
        ROOT + "/reservations", params={"reader_id": reader["id"], "status": "WAITING"}
    )
    assert response.status_code == 200 and response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == reservation["id"]
    assert "qr_token" not in response.text and "password" not in response.text
    assert (
        staff.get(ROOT + "/reservations", params={"q": reservation["reservation_number"]}).json()[
            "total"
        ]
        == 1
    )


@pytest.mark.parametrize("role", [UserRole.READER, UserRole.ADMIN])
def test_staff_operations_and_manual_are_librarian_only(client, actor, role):
    reader, _ = actor(role)
    for path in ["/dashboard", "/reservations", f"/readers/{reader['id']}", "/borrowings/overdue"]:
        assert client.get(ROOT + path).status_code == 403
    assert (
        client.post(
            ROOT + "/reservations/verify-number", json={"reservation_number": "SL-123"}
        ).status_code
        == 403
    )
