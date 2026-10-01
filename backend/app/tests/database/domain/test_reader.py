"""Reader ownership, persisted profile/images and real SQL summary behavior."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from PIL import Image
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.security import now
from app.db.enums import InteractionType, UserRole
from app.db.models import Borrowing, UserInteraction
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy
from app.tests.database.domain.test_reservations import reserve

pytestmark = pytest.mark.integration


def test_favorite_idempotence_concurrency_ownership_availability(staff, actor, domain_db):
    book = create_book(staff)
    create_copy(staff, book)
    owner, _ = actor(UserRole.READER)
    path = BASE + f"/favorites/{book['id']}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: staff.post(path), range(2)))
    assert [r.status_code for r in results] == [204, 204]
    assert staff.get(path).json() == {"is_favorite": True}
    rows = staff.get(BASE + "/favorites?page_size=1").json()
    assert rows["total"] == 1 and rows["items"][0]["available_copies"] == 1
    reserve(staff, book)
    assert staff.get(BASE + "/favorites").json()["items"][0]["available_copies"] == 0
    with Session(domain_db) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(UserInteraction)
                .where(
                    UserInteraction.user_id == owner["id"],
                    UserInteraction.interaction_type == InteractionType.FAVORITE,
                )
            )
            == 1
        )
    actor(UserRole.READER)
    assert staff.get(BASE + "/favorites?user_id=" + owner["id"]).json()["total"] == 0
    assert staff.delete(path).status_code == 204


def test_favorite_remove_and_archived_title(staff, actor):
    _, librarian = actor()
    book = create_book(staff)
    actor(UserRole.READER)
    path = BASE + f"/favorites/{book['id']}"
    assert staff.post(path).status_code == 204
    assert (
        staff.patch(
            BASE + f"/books/{book['id']}/archive",
            json={"archived": True},
            headers={"Authorization": "Bearer " + librarian},
        ).status_code
        == 200
    )
    assert staff.get(BASE + "/favorites").json()["items"][0]["archived_at"]
    assert staff.post(path).status_code == 404
    assert staff.delete(path).status_code == 204
    assert staff.delete(path).status_code == 204
    assert staff.get(BASE + "/favorites").json()["total"] == 0


def test_notification_owner_read_all_and_controlled_metadata(staff, actor):
    book = create_book(staff)
    create_copy(staff, book)
    _, owner_token = actor(UserRole.READER)
    reservation = reserve(staff, book)
    page = staff.get(BASE + "/notifications?unread=true").json()
    row = page["items"][0]
    assert page["total"] == 1 and row["related_entity_id"] == reservation["id"]
    assert row["related_entity_type"] == "RESERVATION" and "event_key" not in row
    actor(UserRole.READER)
    assert staff.get(BASE + "/notifications").json()["total"] == 0
    path = BASE + f"/notifications/{row['id']}/read"
    assert staff.patch(path).status_code == 404
    assert staff.post(BASE + "/notifications/read-all").status_code == 204
    staff.headers["Authorization"] = "Bearer " + owner_token
    assert staff.get(BASE + "/notifications?unread=true").json()["total"] == 1
    assert staff.patch(path).json()["is_read"] is True
    assert staff.patch(path).status_code == 200
    assert staff.get(BASE + "/reader/summary").json()["unread_notifications"] == 0
    assert staff.post(BASE + "/notifications/read-all").status_code == 204


@pytest.mark.parametrize(
    "field,value",
    [
        ("role", "ADMIN"),
        ("status", "ACTIVE"),
        ("email", "new@example.com"),
        ("created_at", "2020-01-01"),
        ("avatar_url", "/etc/passwd"),
        ("borrowing_history", []),
    ],
)
def test_profile_rejects_mass_assignment(client, actor, field, value):
    actor(UserRole.READER)
    data = {"first_name": "Айдана", "last_name": "Омар", field: value}
    assert client.patch(BASE + "/users/me", json=data).status_code == 422


def test_profile_validated_persisted_and_audit_safe(client, actor):
    original, _ = actor(UserRole.READER)
    data = {"first_name": " Айдана ", "last_name": "Омар", "phone": "+7 701 234 5678"}
    response = client.patch(BASE + "/users/me", json=data)
    assert response.status_code == 200, response.text
    user = client.get(BASE + "/auth/me").json()
    assert user["first_name"] == "Айдана" and user["email"] == original["email"]
    assert "password_hash" not in user and user["role"] == "READER"
    assert client.patch(BASE + "/users/me", json={**data, "phone": "--------"}).status_code == 422


def test_avatar_decoding_replacement_cleanup_and_removal(client, actor):
    actor(UserRole.READER)
    output = BytesIO()
    Image.new("RGB", (32, 32), "blue").save(output, "PNG")
    path = BASE + "/users/me/avatar"
    assert (
        client.post(path, files={"file": ("a.png", b"not an image", "image/png")}).status_code
        == 422
    )
    assert (
        client.post(path, files={"file": ("a.jpg", output.getvalue(), "image/jpeg")}).status_code
        == 422
    )
    first = client.post(path, files={"file": ("../../a.png", output.getvalue(), "image/png")})
    assert first.status_code == 200, first.text
    url = first.json()["avatar_url"]
    assert url.startswith(BASE + "/media/") and client.get(url).status_code == 200
    second = client.post(path, files={"file": ("a.png", output.getvalue(), "image/png")})
    assert second.status_code == 200 and second.json()["avatar_url"] != url
    assert client.get(url).status_code == 404
    assert client.delete(path).json()["avatar_url"] is None
    assert client.get(second.json()["avatar_url"]).status_code == 404


def test_preferences_actual_categories_atomic_validation_optional(staff, actor):
    category = staff.post(BASE + "/categories", json={"name": "Қызығушылық " + uuid4().hex}).json()
    actor(UserRole.READER)
    path = BASE + "/users/me/preferences"
    assert staff.get(path).json()["categories"] == []
    result = staff.patch(path, json={"category_ids": [category["id"]]})
    assert result.status_code == 200 and result.json()["categories"][0]["id"] == category["id"]
    assert staff.patch(path, json={"category_ids": [str(uuid4())]}).status_code == 404
    assert len(staff.get(path).json()["categories"]) == 1
    assert staff.patch(path, json={"category_ids": [category["id"]] * 2}).status_code == 422
    assert staff.patch(path, json={"category_ids": [], "user_id": str(uuid4())}).status_code == 422
    assert staff.patch(path, json={"category_ids": []}).json()["categories"] == []


def test_summary_uses_real_due_date_and_reservation_tabs(staff, actor, domain_db):
    _, librarian = actor()
    book = create_book(staff)
    copy = create_copy(staff, book)
    owner, _ = actor(UserRole.READER)
    loan = staff.post(
        BASE + "/librarian/borrowings",
        json={"user_id": owner["id"], "book_copy_id": copy["id"], "idempotency_key": str(uuid4())},
        headers={"Authorization": "Bearer " + librarian},
    ).json()
    with domain_db.begin() as db:
        db.execute(
            update(Borrowing)
            .where(Borrowing.id == UUID(loan["id"]))
            .values(due_at=now() - timedelta(seconds=1), borrowed_at=now() - timedelta(days=1))
        )
    summary = staff.get(BASE + "/reader/summary").json()
    assert summary["active_borrowings"] == summary["overdue_borrowings"] == 1
    assert summary["nearest_due_at"] and summary["active_reservations"] == 0
    actor(UserRole.READER)
    reservation = reserve(staff, book)
    assert staff.get(BASE + "/reservations/me?active=true").json()["total"] == 1
    assert staff.get(BASE + "/reservations/me?active=false").json()["total"] == 0
    assert staff.post(BASE + f"/reservations/{reservation['id']}/cancel").status_code == 200
    assert staff.get(BASE + "/reservations/me?active=false").json()["total"] == 1


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.LIBRARIAN])
def test_reader_routes_reject_staff_but_self_profile_allowed(client, actor, role):
    actor(role)
    for path in ["/favorites", "/notifications", "/reader/summary", "/users/me/preferences"]:
        assert client.get(BASE + path).status_code == 403
    assert client.get(BASE + "/users/me").status_code == 200
