"""Real PostgreSQL signals, real model vectors and authenticated render attribution."""

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import numpy as np
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.ai.embeddings.pipeline import generate_one
from app.ai.recommendations.policy import POLICY
from app.ai.recommendations.service import interest_vector, model_space, popular
from app.ai.recommendations.tracking import signature
from app.core.security import now
from app.db.enums import InteractionSource, InteractionType, UserRole
from app.db.models import Book, BookEmbedding, RecommendationImpression, UserInteraction
from app.repositories.recommendations import signals
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy

pytestmark = pytest.mark.integration


@pytest.fixture
def empty_active_catalog(domain_db):
    # This scenario requires no earlier popularity; other tests share a disposable DB.
    # Hide only their active titles, then restore exactly those records after this test.
    with Session(domain_db) as db, db.begin():
        previous = list(db.scalars(select(Book.id).where(Book.archived_at.is_(None))))
        db.execute(update(Book).where(Book.id.in_(previous)).values(archived_at=now()))
    try:
        yield
    finally:
        with Session(domain_db) as db, db.begin():
            db.execute(update(Book).where(Book.id.in_(previous)).values(archived_at=None))


def test_empty_cold_start_preferences_and_unconfigured_model(staff, actor, empty_active_catalog):
    first = create_book(staff)
    category = staff.post(BASE + "/categories", json={"name": uuid4().hex}).json()
    preferred = create_book(staff, category_ids=[category["id"]])
    create_copy(staff, preferred)
    actor(UserRole.READER)
    result = staff.get(BASE + "/recommendations/me?limit=2")
    assert result.status_code == 200, result.text
    assert len(result.json()["items"]) == 2 and not result.json()["content_available"]
    assert result.json()["items"][0]["reason"] == "recent"
    assert (
        staff.patch(
            BASE + "/users/me/preferences", json={"category_ids": [category["id"]]}
        ).status_code
        == 200
    )
    result = staff.get(BASE + "/recommendations/me").json()
    assert result["items"][0]["book"]["id"] == preferred["id"]
    assert result["items"][0]["book"]["available_copies"] == 1
    assert result["items"][0]["reason"] == "preferences"
    assert staff.get(BASE + f"/books/{first['id']}/similar").json()["items"] == []
    assert staff.get(BASE + "/recommendations/me?limit=21").status_code == 422


def test_popularity_uses_canonical_favorites_and_daily_dedup(
    staff, actor, domain_db, empty_active_catalog
):
    one, two = create_book(staff), create_book(staff)
    reader, _ = actor(UserRole.READER)
    assert staff.post(BASE + f"/favorites/{one['id']}").status_code == 204
    for _ in range(4):
        assert (
            staff.post(
                BASE + f"/books/{two['id']}/views", json={"event_id": str(uuid4())}
            ).status_code
            == 204
        )
    with Session(domain_db) as db:
        aggregate = signals()
        weights = dict(db.execute(select(aggregate.c.book_id, aggregate.c.weight)).all())
        assert weights[UUID(one["id"])] == 3  # FAVORITE interaction is not double-counted.
        assert weights[UUID(two["id"])] == 1
        result = popular(db, 20)
        assert [item.book.id for item in result.items].index(UUID(one["id"])) < [
            item.book.id for item in result.items
        ].index(UUID(two["id"]))
    with Session(domain_db) as db, db.begin():
        db.add(
            UserInteraction(
                user_id=reader["id"],
                book_id=two["id"],
                interaction_type=InteractionType.SEARCH_CLICK,
                source=InteractionSource.CATALOG,
                created_at=now() - timedelta(days=100),
            )
        )
    with Session(domain_db) as db:
        aggregate = signals(UUID(reader["id"]))
        assert db.scalar(select(aggregate.c.weight).where(aggregate.c.book_id == two["id"])) == 1
    assert staff.get(BASE + "/books/popular").status_code == 200


def test_real_similarity_profile_weights_exclusion_and_live_availability(
    staff, actor, model_settings, domain_db
):
    _, librarian = actor()
    books = [
        create_book(staff, title=title, description=description)
        for title, description in [
            ("Python programming", "Learn Python functions, modules and practical programming."),
            ("Writing Python", "Readable Python programs, code and software engineering."),
            ("Astronomy", "Stars, galaxies, black holes and the universe."),
        ]
    ]
    physical = create_copy(staff, books[0])
    for book in books:
        generate_one(staff.app.state.db, model_settings, UUID(book["id"]))
    reader, token = actor(UserRole.READER)
    staff.app.state.settings = model_settings
    assert staff.post(BASE + f"/favorites/{books[0]['id']}").status_code == 204
    assert (
        staff.post(
            BASE + f"/books/{books[2]['id']}/views", json={"event_id": str(uuid4())}
        ).status_code
        == 204
    )
    with Session(domain_db) as db:
        space = model_space(db, model_settings)
        a = interest_vector(db, UUID(reader["id"]), space.id)
        b = interest_vector(db, UUID(reader["id"]), space.id, replace(POLICY, view=20))
        target = db.scalar(
            select(BookEmbedding.embedding).where(BookEmbedding.book_id == books[2]["id"])
        )
        assert float(np.dot(b, target)) > float(np.dot(a, target))
    similar = staff.get(BASE + f"/books/{books[0]['id']}/similar").json()
    assert similar["items"][0]["book"]["id"] == books[1]["id"]
    assert books[0]["id"] not in [row["book"]["id"] for row in similar["items"]]
    response = staff.post(
        BASE + "/librarian/borrowings",
        headers={"Authorization": "Bearer " + librarian},
        json={
            "user_id": reader["id"],
            "book_copy_id": physical["id"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert response.status_code == 200, response.text
    result = staff.get(BASE + "/recommendations/me").json()
    assert result["content_available"]
    assert books[0]["id"] not in [row["book"]["id"] for row in result["items"]]
    # Recommendation exclusion never changes catalog/physical lending permission.
    assert staff.get(BASE + f"/books/{books[0]['id']}").json()["available_copies"] == 0
    assert (
        staff.post(
            BASE + f"/librarian/borrowings/{response.json()['id']}/return",
            headers={"Authorization": "Bearer " + librarian},
            json={"condition": "GOOD"},
        ).status_code
        == 200
    )
    repeat = staff.post(
        BASE + "/librarian/borrowings",
        headers={"Authorization": "Bearer " + librarian},
        json={
            "user_id": reader["id"],
            "book_copy_id": physical["id"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert repeat.status_code == 200
    with Session(domain_db) as db:
        aggregate = signals(UUID(reader["id"]))
        assert (
            db.scalar(select(aggregate.c.weight).where(aggregate.c.book_id == books[0]["id"])) == 13
        )


def test_render_attribution_idempotence_owner_tamper_and_role(
    staff, actor, domain_db, empty_active_catalog
):
    book = create_book(staff)
    owner, token = actor(UserRole.READER)
    assert staff.post(BASE + f"/favorites/{book['id']}").status_code == 204
    result = staff.get(BASE + "/books/popular").json()
    assert book["id"] in [item["book"]["id"] for item in result["items"]]
    with Session(domain_db) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(RecommendationImpression)
                .where(RecommendationImpression.user_id == owner["id"])
            )
            == 0
        )
    payload = {"receipt": result["receipt"], "book_id": book["id"]}
    endpoint = BASE + "/recommendations/impressions"
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(lambda _: staff.post(endpoint, json=payload), range(2)))
    assert [row.status_code for row in rows] == [200, 200]
    identity = rows[0].json()["id"]
    assert identity == rows[1].json()["id"]
    for _ in range(2):
        assert staff.post(endpoint + f"/{identity}/click").status_code == 204
    with Session(domain_db) as db:
        row = db.get(RecommendationImpression, UUID(identity))
        assert row.source == InteractionSource.POPULAR_BOOKS
        assert (
            db.scalar(
                select(func.count())
                .select_from(UserInteraction)
                .where(UserInteraction.recommendation_impression_id == identity)
            )
            == 1
        )
    assert staff.post(endpoint, json={**payload, "book_id": str(uuid4())}).status_code == 422
    assert (
        staff.post(endpoint, json={**payload, "receipt": payload["receipt"][:-1] + "x"}).status_code
        == 422
    )
    actor(UserRole.READER)
    assert staff.post(endpoint, json=payload).status_code == 422
    assert staff.post(endpoint + f"/{identity}/click").status_code == 404
    actor(UserRole.LIBRARIAN)
    assert staff.get(BASE + "/recommendations/me").status_code == 403
    assert staff.post(endpoint, json=payload).status_code == 403
    staff.headers.pop("Authorization")
    assert staff.get(BASE + "/recommendations/me").status_code == 401
    assert staff.get(BASE + "/books/popular").json()["receipt"] is None


def test_expired_and_foreign_session_receipts_are_rejected(staff, actor):
    book = create_book(staff)
    actor(UserRole.READER)
    assert staff.post(BASE + f"/favorites/{book['id']}").status_code == 204
    receipt = staff.get(BASE + "/recommendations/me?limit=20").json()["receipt"]
    claims = json.loads(base64.urlsafe_b64decode(receipt.split(".")[0]))
    endpoint = BASE + "/recommendations/impressions"
    for changed in [
        {**claims, "issued": 1, "expires": 2},
        {**claims, "family": str(uuid4())},
    ]:
        body = base64.urlsafe_b64encode(json.dumps(changed).encode()).decode()
        rejected = staff.post(
            endpoint,
            json={
                "receipt": body + "." + signature(staff.app.state.settings, body),
                "book_id": book["id"],
            },
        )
        assert rejected.status_code == 422
        assert "receipt" not in rejected.text


def test_personalized_render_source_and_archived_exclusion(staff, actor, domain_db):
    _, librarian = actor()
    book = create_book(staff)
    category = staff.post(BASE + "/categories", json={"name": uuid4().hex}).json()
    assert (
        staff.patch(
            BASE + f"/books/{book['id']}", json={"category_ids": [category["id"]]}
        ).status_code
        == 200
    )
    actor(UserRole.READER)
    assert (
        staff.patch(
            BASE + "/users/me/preferences", json={"category_ids": [category["id"]]}
        ).status_code
        == 200
    )
    result = staff.get(BASE + "/recommendations/me").json()
    assert result["items"][0]["book"]["id"] == book["id"]
    response = staff.post(
        BASE + "/recommendations/impressions",
        json={"receipt": result["receipt"], "book_id": book["id"]},
    )
    assert response.status_code == 200
    with Session(domain_db) as db:
        assert (
            db.get(RecommendationImpression, UUID(response.json()["id"])).source
            == InteractionSource.RECOMMENDATION
        )
    assert (
        staff.patch(
            BASE + f"/books/{book['id']}/archive",
            headers={"Authorization": "Bearer " + librarian},
            json={"archived": True},
        ).status_code
        == 200
    )
    assert book["id"] not in [
        row["book"]["id"]
        for row in staff.get(BASE + "/recommendations/me?limit=20").json()["items"]
    ]
