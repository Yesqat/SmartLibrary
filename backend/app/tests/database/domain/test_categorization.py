"""Actual trained classifiers/encoder and PostgreSQL human-review transactions."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.enums import UserRole
from app.db.models import AuditLog, Category, CategoryPrediction, CategoryPredictionSelection
from app.db.seed_data import CATEGORIES
from app.tests.database.domain.test_catalog import BASE, create_book

pytestmark = pytest.mark.integration


@pytest.fixture
def categorizer(staff):
    staff.app.state.settings = staff.app.state.settings.model_copy(
        update={"model_cache_directory": Settings().model_cache_directory}
    )
    categories = {}
    for name, description in CATEGORIES.items():
        page = staff.get(BASE + "/categories", params={"q": name, "page_size": 100}).json()
        row = next((row for row in page["items"] if row["name"] == name), None)
        if row is None:
            result = staff.post(
                BASE + "/categories", json={"name": name, "description": description}
            )
            assert result.status_code == 201
            row = result.json()
        categories[name] = row
    return categories


def predict(client, book, method="embedding"):
    result = client.post(BASE + "/ai/categorize", json={"book_id": book["id"], "method": method})
    assert result.status_code == 201, result.text
    return result.json()


def learning_book(client):
    return create_book(
        client,
        title="Deep Learning with Python " + uuid4().hex[:5],
        language="en",
        description=(
            "Neural networks, machine learning and artificial intelligence. "
            "Practical Python programming for deep learning and model training."
        ),
    )


def test_actual_methods_multilabel_provenance_and_no_automatic_assignment(
    staff, categorizer, domain_db
):
    book = learning_book(staff)
    for method in ["embedding", "classical"]:
        run = predict(staff, book, method)
        assert run["review_status"] == "PENDING"
        if method == "embedding":
            assert len(run["predictions"]) >= 2
        with Session(domain_db) as db:
            existing = {
                str(identity)
                for identity in db.scalars(
                    select(Category.id).where(Category.archived_at.is_(None))
                )
            }
        assert all(row["category_id"] in existing for row in run["predictions"])
        assert all(
            -1 <= row["confidence"] <= 1 and row["accepted"] is None for row in run["predictions"]
        )
        assert all(
            row["score_kind"] == ("PROBABILITY" if method == "classical" else "COSINE_SIMILARITY")
            for row in run["predictions"]
        )
        assert staff.get(BASE + f"/books/{book['id']}").json()["categories"] == []
        with Session(domain_db) as db:
            assert db.scalar(
                select(func.count())
                .select_from(CategoryPrediction)
                .where(CategoryPrediction.run_id == run["id"])
            ) == len(run["predictions"])
        assert (
            staff.get(BASE + f"/ai/category-predictions/{run['id']}").json()["model_revision"]
            == run["model_revision"]
        )


@pytest.mark.parametrize("decision", ["ACCEPTED", "MODIFIED", "REJECTED"])
def test_review_persists_final_labels_and_audit(staff, categorizer, domain_db, decision):
    book = learning_book(staff)
    run = predict(staff, book)
    selected = [row["category_id"] for row in run["predictions"]]
    assert selected
    if decision == "REJECTED":
        selected = []
    if decision == "MODIFIED":
        selected = [categorizer["Biography"]["id"]]
        assert set(selected) != {row["category_id"] for row in run["predictions"]}
    endpoint = BASE + f"/ai/category-predictions/{run['id']}/review"
    response = staff.post(endpoint, json={"category_ids": selected})
    assert response.status_code == 200, response.text
    assert response.json()["review_status"] == decision
    assert {
        row["id"] for row in staff.get(BASE + f"/books/{book['id']}").json()["categories"]
    } == set(selected)
    assert staff.post(endpoint, json={"category_ids": selected}).status_code == 200
    with Session(domain_db) as db:
        assert set(
            str(row)
            for row in db.scalars(
                select(CategoryPredictionSelection.category_id).where(
                    CategoryPredictionSelection.run_id == run["id"]
                )
            )
        ) == set(selected)
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "CATEGORY_REVIEWED", AuditLog.entity_id == run["id"])
            )
            == 1
        )
        for row in db.scalars(
            select(CategoryPrediction).where(CategoryPrediction.run_id == run["id"])
        ):
            assert row.accepted == (str(row.category_id) in selected)
            assert row.reviewed_by and row.reviewed_at


def test_concurrent_review_once_and_stale_metadata_rejected(staff, categorizer, domain_db):
    book = learning_book(staff)
    run = predict(staff, book)
    endpoint = BASE + f"/ai/category-predictions/{run['id']}/review"
    payload = {"category_ids": [row["category_id"] for row in run["predictions"]]}
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: staff.post(endpoint, json=payload), range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    assert staff.post(endpoint, json={"category_ids": []}).status_code == 409
    run = predict(staff, book)
    assert (
        staff.patch(
            BASE + f"/books/{book['id']}", json={"description": "Changed content"}
        ).status_code
        == 200
    )
    response = staff.post(BASE + f"/ai/category-predictions/{run['id']}/review", json=payload)
    assert response.status_code == 409 and response.json()["error"]["code"] == "STALE_PREDICTION"
    assert (
        staff.get(BASE + f"/ai/category-predictions/{run['id']}").json()["review_status"]
        == "PENDING"
    )


def test_roles_invalid_categories_and_model_failure(staff, categorizer, actor, tmp_path):
    book = learning_book(staff)
    run = predict(staff, book)
    endpoint = BASE + f"/ai/category-predictions/{run['id']}/review"
    assert staff.post(endpoint, json={"category_ids": [str(uuid4())]}).status_code == 404
    assert (
        staff.post(
            endpoint, json={"category_ids": [categorizer["Programming"]["id"]] * 2}
        ).status_code
        == 422
    )
    actor(UserRole.READER)
    assert staff.post(BASE + "/ai/categorize", json={"book_id": book["id"]}).status_code == 403
    assert staff.get(BASE + "/ai/category-predictions").status_code == 403
    assert staff.post(endpoint, json={"category_ids": []}).status_code == 403
    actor(UserRole.ADMIN)
    assert staff.post(endpoint, json={"category_ids": []}).status_code == 200
    staff.app.state.settings = staff.app.state.settings.model_copy(
        update={"model_cache_directory": tmp_path}
    )
    unavailable = staff.post(BASE + "/ai/categorize", json={"book_id": book["id"]})
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "CATEGORIZATION_UNAVAILABLE"
    assert staff.get(BASE + f"/books/{book['id']}").status_code == 200


def test_taxonomy_change_invalidates_review_without_changing_book(staff, categorizer):
    book = learning_book(staff)
    run = predict(staff, book)
    custom = staff.post(BASE + "/categories", json={"name": "New taxonomy " + uuid4().hex}).json()
    assert custom["id"]
    response = staff.post(
        BASE + f"/ai/category-predictions/{run['id']}/review",
        json={"category_ids": [row["category_id"] for row in run["predictions"]]},
    )
    assert response.status_code == 409
    assert staff.get(BASE + f"/books/{book['id']}").json()["categories"] == []
