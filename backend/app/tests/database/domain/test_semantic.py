"""Real pinned multilingual inference and PostgreSQL vectors; no synthetic encoder."""

from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.embeddings.encoder import PROFILES
from app.ai.embeddings.pipeline import generate_one, persist_vector
from app.ai.embeddings.source import book_source, source_hash
from app.db.enums import InteractionSource, SearchType, UserRole
from app.db.models import BookEmbedding, EmbeddingModel, SearchEvent, UserInteraction
from app.db.seed_data import BOOKS
from app.repositories.catalog import get_book
from app.schemas.search import SearchParams
from app.services.search.service import search
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def corpus_data():
    return BOOKS


@pytest.fixture
def corpus(staff, model_settings, corpus_data):
    category = staff.post(BASE + "/categories", json={"name": "Retrieval " + uuid4().hex}).json()
    books = []
    for title, author, language, year, _, description in corpus_data:
        record = staff.post(BASE + "/authors", json={"full_name": author}).json()
        book = create_book(
            staff,
            title=title,
            language=language,
            description=description,
            publication_year=year,
            author_ids=[record["id"]],
            category_ids=[category["id"]],
        )
        physical_copy = create_copy(staff, book)
        assert generate_one(staff.app.state.db, model_settings, UUID(book["id"])) == "generated"
        books.append({**book, "physical_copy": physical_copy})
    yield {"category": category, "books": books}
    # These real seed titles must not pollute later exact/fuzzy ranking fixtures.
    response = staff.get(BASE + "/search", params={"category": category["id"], "page_size": 100})
    assert response.status_code == 200
    for row in response.json()["items"]:
        assert (
            staff.patch(BASE + f"/books/{row['id']}/archive", json={"archived": True}).status_code
            == 200
        )
    assert (
        staff.patch(
            BASE + f"/categories/{category['id']}/archive", json={"archived": True}
        ).status_code
        == 200
    )


def run_search(client, settings, corpus, **values):
    with Session(client.app.state.db) as db, db.begin():
        return search(
            db,
            SearchParams(mode="semantic", category=corpus["category"]["id"], **values),
            None,
            settings,
        )


def test_multilingual_meaning_and_current_combined_filters(staff, model_settings, corpus):
    for q, title in [
        ("Нейрондық желілерді үйретуді үйренгім келеді", "Deep Learning with Python"),
        ("Объяснение космологии и черных дыр", "A Brief History of Time"),
        ("Everyday actions that build better habits", "Atomic Habits"),
    ]:
        result = run_search(staff, model_settings, corpus, q=q)
        assert result.items[0].title == title
        assert result.total == 12 and not result.indexing_pending
        assert all(book.available_copies == 1 for book in result.items)
    target = corpus["books"][3]
    params = dict(
        q="нейронные сети",
        language=["en"],
        year_from=2017,
        year_to=2017,
        available=True,
        author=target["authors"][0]["id"],
    )
    assert run_search(staff, model_settings, corpus, **params).total == 1
    assert (
        staff.patch(
            BASE + f"/copies/{target['physical_copy']['id']}", json={"status": "MAINTENANCE"}
        ).status_code
        == 200
    )
    assert run_search(staff, model_settings, corpus, **params).total == 0
    page = run_search(
        staff, model_settings, corpus, q="кітап", page=2, page_size=3, sort="title_asc"
    )
    assert len(page.items) == 3 and page.pages == 4


def test_hybrid_exact_priority_and_missing_vector_disclosure(staff, model_settings, corpus):
    target = corpus["books"][2]
    isbn = "9780201633610"
    assert staff.patch(BASE + f"/books/{target['id']}", json={"isbn": isbn}).status_code == 200
    pending = create_book(
        staff, title="Exact Retrieval " + uuid4().hex, category_ids=[corpus["category"]["id"]]
    )
    for q, expected in [
        (isbn, target["id"]),
        (target["title"], target["id"]),
        (pending["title"], pending["id"]),
    ]:
        with Session(staff.app.state.db) as db, db.begin():
            result = search(
                db,
                SearchParams(q=q, mode="hybrid", category=corpus["category"]["id"]),
                None,
                model_settings,
            )
        assert str(result.items[0].id) == expected
        assert result.indexing_pending
    with Session(staff.app.state.db) as db, db.begin():
        result = search(
            db,
            SearchParams(
                q="черные дыры и космос", mode="hybrid", category=corpus["category"]["id"]
            ),
            None,
            model_settings,
        )
        assert result.items[0].title == "A Brief History of Time"


def test_real_vector_provenance_unchanged_and_safe_regeneration(staff, model_settings):
    book = create_book(staff, title="Embedding integrity", description="Introduction to chemistry")
    identity = UUID(book["id"])
    assert generate_one(staff.app.state.db, model_settings, identity) == "generated"
    with Session(staff.app.state.db) as db:
        vector = db.scalar(select(BookEmbedding).where(BookEmbedding.book_id == identity))
        original = (
            vector.id,
            vector.generated_at,
            vector.source_hash,
            list(vector.embedding),
            vector.model_id,
        )
        model = db.get(EmbeddingModel, vector.model_id)
        assert model.dimension == 768 and model.revision == PROFILES[1].revision
        assert (
            db.scalar(
                select(func.vector_dims(BookEmbedding.embedding)).where(
                    BookEmbedding.id == vector.id
                )
            )
            == 768
        )
        assert vector.source_hash == source_hash(book_source(get_book(db, identity)))
    assert generate_one(staff.app.state.db, model_settings, identity) == "unchanged"
    assert staff.patch(BASE + f"/books/{identity}", json={"page_count": 123}).status_code == 200
    assert generate_one(staff.app.state.db, model_settings, identity) == "unchanged"
    with Session(staff.app.state.db) as db:
        assert db.get(BookEmbedding, original[0]).generated_at == original[1]
    assert (
        staff.patch(
            BASE + f"/books/{identity}", json={"description": "An astronomy textbook"}
        ).status_code
        == 200
    )
    with Session(staff.app.state.db) as db:
        assert db.scalar(select(BookEmbedding.id).where(BookEmbedding.book_id == identity)) is None
    assert (
        persist_vector(
            staff.app.state.db, identity, PROFILES[1], original[4], original[2], original[3]
        )
        == "stale"
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: generate_one(staff.app.state.db, model_settings, identity), range(2))
        )
    assert all(result in {"generated", "unchanged"} for result in results)
    with Session(staff.app.state.db) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(BookEmbedding)
                .where(BookEmbedding.book_id == identity)
            )
            == 1
        )


def test_reference_changes_invalidate_only_affected_vectors(staff, model_settings):
    author = staff.post(BASE + "/authors", json={"full_name": "Embedding author"}).json()
    one = create_book(staff, author_ids=[author["id"]])
    two = create_book(staff)
    for book in [one, two]:
        generate_one(staff.app.state.db, model_settings, UUID(book["id"]))
    assert (
        staff.patch(
            BASE + f"/authors/{author['id']}", json={"full_name": "Updated author"}
        ).status_code
        == 200
    )
    with Session(staff.app.state.db) as db:
        assert db.scalar(select(BookEmbedding.id).where(BookEmbedding.book_id == one["id"])) is None
        assert (
            db.scalar(select(BookEmbedding.id).where(BookEmbedding.book_id == two["id"]))
            is not None
        )
    assert generate_one(staff.app.state.db, model_settings, UUID(one["id"])) == "generated"


def test_vector_http_modes_owned_event_click_and_safe_unavailable(staff, actor, model_settings):
    book = create_book(
        staff, title="Quantum physics", description="An introduction to atoms and matter."
    )
    generate_one(staff.app.state.db, model_settings, UUID(book["id"]))
    actor(UserRole.READER)
    staff.app.state.settings = model_settings
    for mode in ["semantic", "hybrid"]:
        result = staff.get(BASE + f"/search/{mode}", params={"q": "Quantum physics"})
        assert result.status_code == 200, result.text
        data = result.json()
        assert (
            staff.post(
                BASE + f"/search/{data['search_event_id']}/click",
                json={"book_id": book["id"], "event_id": str(uuid4())},
            ).status_code
            == 204
        )
        with Session(staff.app.state.db) as db:
            event = db.get(SearchEvent, UUID(data["search_event_id"]))
            assert event.search_type == SearchType(mode.upper())
            click = db.scalar(
                select(UserInteraction).where(UserInteraction.search_event_id == event.id)
            )
            assert click.source == InteractionSource(mode.upper() + "_SEARCH")
    staff.app.state.settings = model_settings.model_copy(
        update={"embedding_model_revision": "invalid"}
    )
    unavailable = staff.get(BASE + "/search/semantic", params={"q": "physics"})
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "SEMANTIC_SEARCH_UNAVAILABLE"
    assert staff.get(BASE + "/search", params={"q": "Quantum physics"}).status_code == 200
    assert staff.get(BASE + "/search", params={"mode": "invented"}).status_code == 422
