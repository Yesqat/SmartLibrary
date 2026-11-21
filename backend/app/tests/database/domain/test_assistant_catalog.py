"""The assistant exposes the same copy counts and book facts as the public catalog."""

import json
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.ai.assistant.tools import ToolContext
from app.api.dependencies import Principal
from app.core.security import decode_access
from app.db.enums import UserRole
from app.db.models import User
from app.services.audit.events import AuditContext
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy

pytestmark = pytest.mark.integration


def test_assistant_catalog_fields_filters_and_last_copy(staff, actor):
    author_name = "Абай " + uuid4().hex
    category_name = "Тарих " + uuid4().hex
    author = staff.post(BASE + "/authors", json={"full_name": author_name}).json()
    category = staff.post(BASE + "/categories", json={"name": category_name}).json()
    book = create_book(
        staff,
        title="Дала тарихы",
        language="kk",
        isbn="9780134494166",
        publication_year=2017,
        description="Қазақ даласының тарихы.",
        author_ids=[author["id"]],
        category_ids=[category["id"]],
    )
    create_book(staff, title="Another edition", language="en", category_ids=[category["id"]])
    only_copy = create_copy(staff, book, shelf_location="A2")
    archived = create_copy(staff, book, shelf_location="Archive")
    assert (
        staff.patch(BASE + f"/copies/{archived['id']}/archive", json={"archived": True}).status_code
        == 200
    )

    librarian = staff.headers["Authorization"]
    reader, token = actor(UserRole.READER)
    engine, settings = staff.app.state.db, staff.app.state.settings
    user_id, family_id = decode_access(token, settings)
    with Session(engine) as db:
        principal = Principal(db.get(User, user_id), family_id)
    context = ToolContext(engine, settings, principal, AuditContext())
    for query in (author_name, category_name):
        result = context.execute(
            "search_books", json.dumps({"q": query, "language": "kk", "available": None})
        )
        assert result["total"] == 1
        assert result["books"][0]["id"] == book["id"]

    args = json.dumps({"book_id": book["id"]})
    facts = context.execute("get_book_details", args)["books"][0]
    public = staff.get(BASE + f"/books/{book['id']}").json()
    for key in (
        "title",
        "language",
        "isbn",
        "publication_year",
        "description",
        "available_copies",
        "total_copies",
        "shelf_locations",
    ):
        assert facts[key] == public[key]
    assert facts["authors"] == [author_name] and facts["categories"] == [category_name]
    assert facts["shelf_locations"] == ["A2"]
    assert facts["available_copies"] == facts["total_copies"] == 1

    staff.headers["Authorization"] = librarian
    issued = staff.post(
        BASE + "/librarian/borrowings",
        json={
            "user_id": reader["id"],
            "book_copy_id": only_copy["id"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert issued.status_code == 200, issued.text
    checked = context.execute("check_book_availability", args)["books"][0]
    assert checked["total_copies"] == 1
    assert checked["available_copies"] == 0 and checked["shelf_locations"] == []
    filtered = context.execute(
        "search_books", json.dumps({"q": author_name, "language": "kk", "available": True})
    )
    assert filtered["total"] == 0 and filtered["books"] == []
