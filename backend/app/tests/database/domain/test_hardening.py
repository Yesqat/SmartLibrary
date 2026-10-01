from uuid import uuid4

import pytest

from app.db.enums import UserRole
from app.tests.database.domain.test_catalog import BASE, create_book

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("role", [None, UserRole.READER, UserRole.LIBRARIAN, UserRole.ADMIN])
def test_cross_surface_read_permissions(client, actor, role):
    if role:
        actor(role)
    groups = {
        UserRole.READER: [
            "/favorites",
            "/notifications",
            "/borrowings/me/active",
            "/borrowings/me/history",
            "/reservations/me",
            "/reader/summary",
            "/ai/conversations",
        ],
        UserRole.LIBRARIAN: ["/librarian/dashboard", "/librarian/readers"],
        UserRole.ADMIN: [
            "/admin/users",
            "/admin/settings",
            "/admin/audit-logs",
            "/admin/analytics/overview",
            "/admin/analytics/ai",
        ],
    }
    for required, paths in groups.items():
        for path in paths:
            response = client.get(BASE + path)
            expected = 401 if role is None else 200 if role == required else 403
            assert response.status_code == expected, (role, path, response.text)
            assert response.headers["cache-control"] == "no-store"
            assert "password_hash" not in response.text
            assert "token_hash" not in response.text


def test_authenticated_catalog_is_not_shared_cacheable_and_upload_limit_is_real(staff):
    book = create_book(staff)
    assert staff.get(BASE + "/books?include_archived=true").headers["cache-control"] == "no-store"
    assert staff.get(BASE + f"/books/{book['id']}/copies").headers["cache-control"] == "no-store"
    path = BASE + f"/books/{book['id']}/cover"
    for _ in range(30):
        assert (
            staff.post(path, files={"file": ("x.png", b"invalid", "image/png")}).status_code == 422
        )
    response = staff.post(path, files={"file": ("x.png", b"invalid", "image/png")})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert int(response.headers["retry-after"]) > 0


def test_catalog_mutation_cannot_use_cross_site_or_missing_origin(staff):
    book = create_book(staff)
    for origin in ("https://attacker.invalid", "null", ""):
        response = staff.patch(
            BASE + f"/books/{book['id']}", json={"title": str(uuid4())}, headers={"Origin": origin}
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "CSRF_FAILED"
