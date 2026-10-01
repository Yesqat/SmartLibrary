"""Real pg_trgm relevance, SQL filters, bounded results and event ownership."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, select, update
from sqlalchemy.orm import Session

from app.core.security import now
from app.db.enums import CopyStatus, UserRole
from app.db.models import BookCopy, Borrowing, SearchEvent, UserInteraction
from app.repositories.search import standard_search
from app.schemas.search import SearchParams
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy

pytestmark = pytest.mark.integration


def search(client, **params):
    result = client.get(BASE + "/search", params=params)
    assert result.status_code == 200, result.text
    return result.json()


def test_exact_title_and_isbn_outrank_weak_matches(staff):
    exact = create_book(staff, title="Clean Code", isbn="9780132350884")
    prefix = create_book(staff, title="Clean Code Handbook")
    weak = create_book(
        staff,
        title="A programming text",
        description="Clean Code and 9780132350884 are discussed here",
    )
    result = search(staff, q="clean code")
    ids = [item["id"] for item in result["items"]]
    assert ids.index(exact["id"]) < ids.index(prefix["id"]) < ids.index(weak["id"])
    assert search(staff, q="978-0-13-235088-4")["items"][0]["id"] == exact["id"]
    assert search(staff, q="Clen Code")["items"][0]["id"] == exact["id"]
    assert search(staff, q="clean code", sort="title_desc")["items"][0]["id"] == exact["id"]


def test_kazakh_fuzzy_and_related_metadata_search(staff):
    author = staff.post(BASE + "/authors", json={"full_name": "Мұхтар Әуезов"}).json()
    category = staff.post(BASE + "/categories", json={"name": "Роман " + uuid4().hex}).json()
    publisher = staff.post(BASE + "/publishers", json={"name": "Қазына баспасы"}).json()
    book = create_book(
        staff,
        title="Абай жолы",
        author_ids=[author["id"]],
        category_ids=[category["id"]],
        publisher_id=publisher["id"],
        description="Қазақ даласының тарихи өмірі",
    )
    for q in ["Абай жоли", "Мұхтар", "Роман", "Қазына", "даласының"]:
        assert book["id"] in [item["id"] for item in search(staff, q=q)["items"]]


def test_combined_filters_and_live_availability(staff):
    author = staff.post(BASE + "/authors", json={"full_name": "Filter author"}).json()
    category = staff.post(BASE + "/categories", json={"name": "Filter " + uuid4().hex}).json()
    publisher = staff.post(BASE + "/publishers", json={"name": "Filter publisher"}).json()
    match = create_book(
        staff,
        language="kk",
        publication_year=2020,
        author_ids=[author["id"]],
        category_ids=[category["id"]],
        publisher_id=publisher["id"],
    )
    copy = create_copy(staff, match)
    create_book(staff, language="en", publication_year=1990, category_ids=[category["id"]])
    params = {
        "author": author["id"],
        "category": category["id"],
        "publisher": publisher["id"],
        "language": ["kk", "ru"],
        "year_from": 2019,
        "year_to": 2021,
        "available": True,
    }
    result = search(staff, **params)
    assert result["total"] == 1 and result["items"][0]["id"] == match["id"]
    assert (
        staff.patch(BASE + f"/copies/{copy['id']}", json={"status": "MAINTENANCE"}).status_code
        == 200
    )
    assert search(staff, **params)["total"] == 0
    assert search(staff, **{**params, "available": False})["total"] == 1


@pytest.mark.parametrize(
    "params",
    [
        {"year_from": 2024, "year_to": 1990},
        {"page_size": 101},
        {"sort": "drop table books"},
        {"language": "bad_language"},
        {"category": "invalid"},
        {"page": 0},
    ],
)
def test_invalid_filters(client, params):
    assert client.get(BASE + "/search", params=params).status_code == 422


def test_pagination_and_year_title_sort(staff):
    category = staff.post(BASE + "/categories", json={"name": "Paging " + uuid4().hex}).json()["id"]
    books = [
        create_book(staff, title=title, publication_year=year, category_ids=[category])
        for title, year in [("Zulu", 1980), ("Alpha", 2022), ("Middle", None)]
    ]
    newest = search(staff, category=category, sort="year_desc", page_size=1)
    assert (
        newest["total"] == 3 and newest["pages"] == 3 and newest["items"][0]["id"] == books[1]["id"]
    )
    assert search(staff, category=category, sort="year_asc")["items"][0]["id"] == books[0]["id"]
    assert search(staff, category=category, sort="title_desc")["items"][0]["id"] == books[0]["id"]
    assert search(staff, category=category, sort="title_asc")["items"][0]["id"] == books[1]["id"]
    assert search(staff, category=category, page=4, page_size=1)["items"] == []


def test_popularity_uses_real_borrowing_rows(staff, actor, domain_db):
    reader, _ = actor(UserRole.READER)
    librarian, _ = actor()
    category = staff.post(BASE + "/categories", json={"name": "Popularity " + uuid4().hex}).json()[
        "id"
    ]
    create_book(staff, title="Alpha without loans", category_ids=[category])
    book = create_book(staff, title="Zulu with loan", category_ids=[category])
    copy = create_copy(staff, book)
    with Session(domain_db) as db, db.begin():
        db.execute(
            update(BookCopy).where(BookCopy.id == copy["id"]).values(status=CopyStatus.BORROWED)
        )
        db.add(
            Borrowing(
                user_id=UUID(reader["id"]),
                book_copy_id=UUID(copy["id"]),
                issued_by=UUID(librarian["id"]),
                due_at=now() + timedelta(days=14),
            )
        )
    assert search(staff, category=category, sort="popularity")["items"][0]["id"] == book["id"]


def test_autocomplete_is_bounded_prefix_first_and_hides_archives(staff):
    prefix = "Autocomplete" + uuid4().hex[:6]
    exact = create_book(staff, title=prefix)
    for i in range(4):
        create_book(staff, title=prefix + str(i))
    hidden = create_book(staff, title=prefix + " archived")
    staff.patch(BASE + f"/books/{hidden['id']}/archive", json={"archived": True})
    result = staff.get(BASE + "/search/autocomplete", params={"q": prefix, "limit": 3})
    assert result.status_code == 200, result.text
    assert len(result.json()["items"]) == 3
    assert result.json()["items"][0]["id"] == exact["id"]
    assert hidden["id"] not in [item["id"] for item in result.json()["items"]]
    assert staff.get(BASE + "/search/autocomplete?q=x").json()["items"] == []
    assert staff.get(BASE + "/search/autocomplete?q=ab&limit=100").status_code == 422


def test_search_events_zero_results_click_ownership(staff, actor, domain_db):
    book = create_book(staff, title="Event search " + uuid4().hex)
    reader, _ = actor(UserRole.READER)
    result = search(staff, q=book["title"])
    identity = result["search_event_id"]
    data = {"book_id": book["id"], "event_id": str(uuid4())}
    for _ in range(2):
        assert staff.post(BASE + f"/search/{identity}/click", json=data).status_code == 204
    assert (
        staff.post(
            BASE + f"/search/{identity}/click", json={**data, "book_id": str(uuid4())}
        ).status_code
        == 404
    )
    actor(UserRole.READER)
    assert staff.post(BASE + f"/search/{identity}/click", json=data).status_code == 404
    staff.headers.pop("Authorization")
    zero = search(staff, q=uuid4().hex)
    with Session(domain_db) as db:
        event = db.get(SearchEvent, UUID(identity))
        assert event.user_id == UUID(reader["id"]) and event.result_count == 1
        assert event.filters["result_ids"] == [book["id"]]
        clicks = list(
            db.scalars(select(UserInteraction).where(UserInteraction.search_event_id == identity))
        )
        assert len(clicks) == 1 and str(clicks[0].user_id) == reader["id"]
        no_results = db.get(SearchEvent, UUID(zero["search_event_id"]))
        assert no_results.result_count == 0 and no_results.user_id is None


def test_sql_wildcards_are_literal_and_archive_visibility(staff):
    book = create_book(staff, title="Literal_%_" + uuid4().hex)
    assert book["id"] in [item["id"] for item in search(staff, q="_%_")["items"]]
    assert search(staff, q="'; DROP TABLE books; --")["total"] == 0
    staff.patch(BASE + f"/books/{book['id']}/archive", json={"archived": True})
    assert search(staff, q=book["title"])["total"] == 0
    assert search(staff, q=book["title"], include_archived=True)["total"] == 1
    staff.headers.pop("Authorization")
    assert staff.get(BASE + "/search?include_archived=true").status_code == 401


def test_filter_reference_lookup_and_no_n_plus_one(staff):
    category = staff.post(BASE + "/categories", json={"name": "Lookup " + uuid4().hex}).json()
    for _ in range(4):
        create_book(staff, category_ids=[category["id"]])
    assert staff.get(BASE + f"/categories/{category['id']}").json()["name"] == category["name"]
    statements = []
    engine = staff.app.state.db

    def count(*args):
        statements.append(args[2])

    event.listen(engine, "before_cursor_execute", count)
    try:
        with Session(engine) as db:
            result = standard_search(db, SearchParams(category=UUID(category["id"])))
            assert result.total == 4
        assert len(statements) == 5  # pg_trgm configuration + bounded four-query catalog read
    finally:
        event.remove(engine, "before_cursor_execute", count)
