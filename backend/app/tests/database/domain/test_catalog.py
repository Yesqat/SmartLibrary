"""Catalog rules verified through the real HTTP service, PostgreSQL and restricted DB role."""

from io import BytesIO
from uuid import UUID, uuid4

import pytest
from PIL import Image
from sqlalchemy import event, select, update
from sqlalchemy.orm import Session

from app.db.enums import CopyStatus, ReservationStatus, UserRole
from app.db.models import AuditLog, Book, BookCopy, Reservation, UserInteraction
from app.repositories.catalog import list_books

pytestmark = pytest.mark.integration
BASE = "/api/v1"


def create_book(client, **extra):
    response = client.post(
        BASE + "/books", json={"title": "Абай " + uuid4().hex, "language": "kk", **extra}
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_copy(client, book, **extra):
    response = client.post(
        BASE + f"/books/{book['id']}/copies", json={"inventory_number": uuid4().hex, **extra}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_public_catalog_and_live_availability(staff):
    book = create_book(staff)
    create_copy(staff, book, shelf_location="A-2")
    create_copy(staff, book, condition="DAMAGED", shelf_location="Workshop")
    staff.headers.pop("Authorization")
    result = staff.get(BASE + f"/books/{book['id']}")
    assert result.status_code == 200, result.text
    assert result.json()["total_copies"] == 2
    assert result.json()["available_copies"] == 1
    assert result.json()["shelf_locations"] == ["A-2"]
    page = staff.get(BASE + "/books", params={"q": book["title"], "page_size": 1}).json()
    assert page["total"] == 1 and len(page["items"]) == 1
    assert staff.get(BASE + f"/books/{book['id']}/copies").status_code == 401
    assert staff.get(BASE + "/books?include_archived=true").status_code == 401


@pytest.mark.parametrize("role,expected", [("READER", 403), ("LIBRARIAN", 201), ("ADMIN", 201)])
def test_write_roles(client, actor, role, expected):
    actor(UserRole(role))
    assert (
        client.post(BASE + "/books", json={"title": "Role test", "language": "kk"}).status_code
        == expected
    )


def test_origin_and_no_cookie_only_auth(staff):
    staff.headers["Origin"] = "https://untrusted.example"
    assert staff.post(BASE + "/books", json={"title": "Test", "language": "kk"}).status_code == 403
    staff.headers["Origin"] = "http://localhost:8080"
    staff.headers.pop("Authorization")
    assert staff.post(BASE + "/books", json={"title": "Test", "language": "kk"}).status_code == 401


@pytest.mark.parametrize(
    "values",
    [
        {"title": None},
        {"title": " "},
        {"isbn": "9780000000000"},
        {"available_copies": 10},
        {"ebook_url": "https://example.com"},
        {"publication_year": 0},
        {"category_ids": [str(UUID(int=1)), str(UUID(int=1))]},
        {"language": "english"},
    ],
)
def test_input_rejection(staff, values):
    response = staff.post(BASE + "/books", json={"title": "Book", "language": "kk", **values})
    assert response.status_code == 422, response.text


def test_taxonomy_relations_and_safe_archive(staff):
    links = {}
    for kind, body in [
        ("authors", {"full_name": "Author"}),
        ("categories", {"name": uuid4().hex}),
        ("publishers", {"name": "Publisher", "country": "Қазақстан"}),
    ]:
        response = staff.post(BASE + "/" + kind, json=body)
        assert response.status_code == 201, response.text
        links[kind] = response.json()["id"]
    book = create_book(
        staff,
        author_ids=[links["authors"]],
        category_ids=[links["categories"]],
        publisher_id=links["publishers"],
    )
    assert book["authors"][0]["id"] == links["authors"]
    for kind, identity in links.items():
        assert (
            staff.patch(BASE + f"/{kind}/{identity}/archive", json={"archived": True}).status_code
            == 409
        )
    assert (
        staff.patch(BASE + f"/books/{book['id']}/archive", json={"archived": True}).status_code
        == 200
    )
    assert staff.get(BASE + f"/books/{book['id']}").status_code == 404
    assert staff.get(BASE + f"/books/{book['id']}?include_archived=true").status_code == 200
    category = links["categories"]
    assert (
        staff.patch(BASE + f"/categories/{category}/archive", json={"archived": True}).status_code
        == 200
    )
    assert (
        staff.patch(BASE + f"/books/{book['id']}/archive", json={"archived": False}).status_code
        == 404
    )
    assert (
        staff.patch(BASE + f"/categories/{category}/archive", json={"archived": False}).status_code
        == 200
    )
    assert (
        staff.patch(BASE + f"/books/{book['id']}/archive", json={"archived": False}).status_code
        == 200
    )
    assert (
        staff.patch(
            BASE + f"/books/{book['id']}",
            json={"author_ids": [], "category_ids": [], "publisher_id": None},
        ).json()["authors"]
        == []
    )


def test_copy_states_and_archive(staff):
    book = create_book(staff)
    copy = create_copy(staff, book)
    path = BASE + f"/copies/{copy['id']}"
    assert staff.patch(path, json={"status": "BORROWED"}).status_code == 409
    assert staff.patch(path, json={"status": "RESERVED"}).status_code == 409
    assert staff.patch(path, json={"condition": "DAMAGED"}).status_code == 409
    assert staff.patch(path, json={"status": "DAMAGED", "condition": "DAMAGED"}).status_code == 200
    assert staff.patch(path, json={"status": "AVAILABLE", "condition": "GOOD"}).status_code == 409
    assert staff.patch(path, json={"status": "MAINTENANCE"}).status_code == 200
    assert staff.patch(path, json={"status": "AVAILABLE", "condition": "GOOD"}).status_code == 200
    assert staff.patch(path + "/archive", json={"archived": True}).status_code == 200
    assert staff.get(BASE + f"/books/{book['id']}").json()["available_copies"] == 0
    assert staff.patch(path, json={"shelf_location": "X"}).status_code == 404
    assert staff.patch(path + "/archive", json={"archived": False}).status_code == 200


def test_in_use_history_protection(staff, actor, domain_db):
    user, _ = actor(UserRole.READER)
    actor()
    book = create_book(staff)
    copy = create_copy(staff, book)
    with Session(domain_db) as db, db.begin():
        db.add(
            Reservation(
                user_id=UUID(user["id"]),
                book_id=UUID(book["id"]),
                status=ReservationStatus.WAITING,
                reservation_number="TEST-" + uuid4().hex,
            )
        )
    assert (
        staff.patch(BASE + f"/books/{book['id']}/archive", json={"archived": True}).status_code
        == 409
    )
    with domain_db.begin() as db:
        db.execute(
            update(BookCopy).where(BookCopy.id == copy["id"]).values(status=CopyStatus.BORROWED)
        )
    assert (
        staff.patch(BASE + f"/copies/{copy['id']}", json={"status": "AVAILABLE"}).status_code == 409
    )
    assert (
        staff.patch(BASE + f"/copies/{copy['id']}/archive", json={"archived": True}).status_code
        == 409
    )


def test_constraints_safe_errors_and_audit(staff, domain_db):
    book = create_book(staff, isbn="978-0-306-40615-7")
    assert book["isbn"] == "9780306406157"
    response = staff.post(
        BASE + "/books", json={"title": "Duplicate", "language": "en", "isbn": book["isbn"]}
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "CATALOG_CONFLICT"
    assert "SQL" not in response.text
    assert (
        staff.patch(BASE + f"/books/{book['id']}", json={"publisher_id": str(uuid4())}).status_code
        == 404
    )
    copy = create_copy(staff, book)
    assert (
        staff.post(
            BASE + f"/books/{book['id']}/copies",
            json={"inventory_number": copy["inventory_number"]},
        ).status_code
        == 409
    )
    with Session(domain_db) as db:
        assert db.scalar(
            select(AuditLog.id).where(
                AuditLog.entity_id == book["id"], AuditLog.action == "BOOK_CREATED"
            )
        )
        assert db.get(Book, UUID(book["id"])).publisher_id is None


def png():
    out = BytesIO()
    Image.new("RGB", (80, 100), "blue").save(out, "PNG")
    return out.getvalue()


def test_cover_lifecycle(staff):
    book = create_book(staff)
    path = BASE + f"/books/{book['id']}/cover"
    first = staff.post(path, files={"file": ("../../payload.png", png(), "image/png")})
    assert first.status_code == 200, first.text
    image_url = first.json()["cover_url"]
    response = staff.get(image_url)
    assert response.status_code == 200 and response.headers["content-type"] == "image/webp"
    with Image.open(BytesIO(response.content)) as image:
        assert image.size == (80, 100)
    second = staff.post(path, files={"file": ("new.png", png(), "image/png")})
    assert second.status_code == 200
    assert staff.get(image_url).status_code == 404
    assert staff.delete(path).status_code == 200
    assert staff.get(second.json()["cover_url"]).status_code == 404
    assert staff.get(BASE + "/media/other.txt").status_code == 404


@pytest.mark.parametrize(
    "content,mime,status",
    [
        (b"<script>alert(1)</script>", "image/png", 422),
        (png(), "image/jpeg", 422),
        (png(), "text/plain", 422),
        (b"x" * (5 * 1024 * 1024 + 1), "image/png", 413),
    ],
)
def test_invalid_upload(staff, content, mime, status):
    book = create_book(staff)
    result = staff.post(
        BASE + f"/books/{book['id']}/cover", files={"file": ("cover.png", content, mime)}
    )
    assert result.status_code == status, result.text
    assert not list(staff.app.state.settings.upload_directory.iterdir())


def test_availability_has_bounded_query_count(staff):
    for _ in range(4):
        book = create_book(staff)
        create_copy(staff, book)
    statements = []
    engine = staff.app.state.db

    def count(*args):
        statements.append(args[2])

    event.listen(engine, "before_cursor_execute", count)
    try:
        with Session(engine) as db:
            result = list_books(db, 1, 100, "", False)
            assert len(result.items) >= 4
        assert len(statements) == 4  # count, books+aggregate+publisher, authors, categories
    finally:
        event.remove(engine, "before_cursor_execute", count)


def test_reader_view_is_owned_and_idempotent(staff, actor, domain_db):
    book = create_book(staff)
    user, _ = actor(UserRole.READER)
    path = BASE + f"/books/{book['id']}/views"
    event_id = str(uuid4())
    for _ in range(2):
        assert staff.post(path, json={"event_id": event_id}).status_code == 204
    assert (
        staff.post(path, json={"event_id": str(uuid4()), "user_id": str(uuid4())}).status_code
        == 422
    )
    with Session(domain_db) as db:
        events = list(
            db.scalars(select(UserInteraction).where(UserInteraction.book_id == book["id"]))
        )
        assert len(events) == 1 and str(events[0].user_id) == user["id"]


def test_failed_cover_upload_preserves_current_cover(staff):
    book = create_book(staff)
    path = BASE + f"/books/{book['id']}/cover"
    saved = staff.post(path, files={"file": ("cover.png", png(), "image/png")}).json()["cover_url"]
    assert staff.post(path, files={"file": ("bad.png", b"invalid", "image/png")}).status_code == 422
    assert staff.get(BASE + f"/books/{book['id']}").json()["cover_url"] == saved
    assert staff.get(saved).status_code == 200
