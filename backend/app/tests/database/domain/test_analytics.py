"""Analytics execute real SQL against isolated PostgreSQL with known historical fixtures."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.enums import (
    BorrowingStatus,
    InteractionSource,
    InteractionType,
    MessageRole,
    PredictionReview,
    RecommendationType,
    SearchType,
    UserRole,
)
from app.db.models import (
    AIConversation,
    AIMessage,
    Borrowing,
    CategoryPrediction,
    CategoryPredictionRun,
    RecommendationImpression,
    Reservation,
    SearchEvent,
    User,
    UserInteraction,
)
from app.services.analytics.definitions import overdue_borrowing
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy
from app.tests.database.domain.test_reservations import reserve

pytestmark = pytest.mark.integration
ROOT = BASE + "/admin/analytics"
GROUPS = ["overview", "circulation", "inventory", "readers", "search", "ai"]


def report(client, group, start="2025-01-01", end="2025-01-03"):
    response = client.get(ROOT + "/" + group, params={"date_from": start, "date_to": end})
    assert response.status_code == 200, response.text
    return response.json()


def test_roles_validation_empty_ranges_and_consistent_overview(client, actor, domain_db):
    for role in (UserRole.READER, UserRole.LIBRARIAN):
        actor(role)
        for group in GROUPS:
            assert client.get(ROOT + "/" + group).status_code == 403
    actor(UserRole.ADMIN)
    for params in [
        {"date_from": "2025-02-01", "date_to": "2025-01-01"},
        {"date_to": "0001-01-01"},
        {"date_to": "9999-12-31"},
        {"date_from": "2000-01-01", "date_to": "2025-01-01"},
        {"unknown": "value"},
    ]:
        assert client.get(ROOT + "/overview", params=params).status_code == 422
    overview = report(client, "overview", "2080-01-01", "2080-01-03")
    assert overview["circulation"]["issued"] == 0
    assert overview["circulation"]["borrowing_trend"] == [
        {"date": f"2080-01-0{i}", "count": 0} for i in range(1, 4)
    ]
    assert overview["readers"]["active_readers"] == 0
    for group in ("inventory", "circulation", "readers"):
        single = report(client, group, "2080-01-01", "2080-01-03")
        assert {k: v for k, v in single.items() if k != "period"} == {
            k: v for k, v in overview[group].items() if k != "period"
        }
    search = report(client, "search", "2080-01-01", "2080-01-03")
    assert search["zero_result_rate"] is None
    ai = report(client, "ai", "2080-01-01", "2080-01-03")
    assert ai["prediction_acceptance_rate"] is None and ai["input_tokens"] is None
    assert all(item["ctr"] is None for item in ai["recommendations"])
    with Session(domain_db) as db:
        assert overview["circulation"]["active_borrowings"] == db.scalar(
            select(func.count())
            .select_from(Borrowing)
            .where(Borrowing.status.in_([BorrowingStatus.BORROWED, BorrowingStatus.OVERDUE]))
        )


def test_actual_circulation_inventory_and_overdue_without_worker(staff, actor, domain_db):
    _, librarian = actor()
    category = staff.post(BASE + "/categories", json={"name": "Analytics " + uuid4().hex}).json()
    book = create_book(staff, category_ids=[category["id"]])
    copies = [create_copy(staff, book) for _ in range(3)]
    reader, _ = actor(UserRole.READER)
    staff.headers["Authorization"] = "Bearer " + librarian
    loans = []
    for copy in copies:
        response = staff.post(
            BASE + "/librarian/borrowings",
            json={
                "user_id": reader["id"],
                "book_copy_id": copy["id"],
                "idempotency_key": str(uuid4()),
            },
        )
        assert response.status_code == 200, response.text
        loans.append(response.json())
    assert (
        staff.post(
            BASE + f"/librarian/borrowings/{loans[1]['id']}/return", json={"condition": "DAMAGED"}
        ).status_code
        == 200
    )
    assert staff.post(BASE + f"/librarian/borrowings/{loans[2]['id']}/lost").status_code == 200
    at = datetime(2025, 2, 2, 10, tzinfo=UTC)
    with Session(domain_db) as db, db.begin():
        for index, loan in enumerate(loans):
            row = db.get(Borrowing, UUID(loan["id"]))
            row.borrowed_at = at
            row.due_at = at + timedelta(days=1)
            if index == 1:
                row.returned_at = at + timedelta(days=2)
            if index == 2:
                row.lost_at = at + timedelta(days=2)
    actor(UserRole.ADMIN)
    data = report(staff, "circulation", "2025-02-01", "2025-02-05")
    assert (data["issued"], data["returned"], data["lost"]) == (3, 1, 1)
    assert data["popular_books"] == [{"id": book["id"], "label": book["title"], "count": 3}]
    assert data["popular_categories"][0]["count"] == 3
    assert [p["count"] for p in data["borrowing_trend"]] == [0, 3, 0, 0, 0]
    with Session(domain_db) as db:
        assert db.get(Borrowing, UUID(loans[0]["id"])).status == BorrowingStatus.BORROWED
        expected = db.scalar(
            select(func.count())
            .select_from(Borrowing)
            .where(overdue_borrowing(datetime.fromisoformat(data["period"]["generated_at"])))
        )
        assert data["overdue_borrowings"] == expected and expected >= 1
    inventory = report(staff, "inventory")
    states = {row["key"]: row["count"] for row in inventory["status"]}
    assert states["DAMAGED"] >= 1 and states["LOST"] >= 1 and states["BORROWED"] >= 1
    assert sum(states.values()) == inventory["physical_copies"]


def test_timezone_search_events_and_distinct_active_reader(staff, actor, domain_db):
    book = create_book(staff)
    reader, _ = actor(UserRole.READER)
    at = datetime(2025, 3, 1, 19, 30, tzinfo=UTC)  # 2 March in library timezone
    with Session(domain_db) as db, db.begin():
        db.execute(update(User).where(User.id == reader["id"]).values(created_at=at))
        for kind, results in [
            (SearchType.STANDARD, 0),
            (SearchType.SEMANTIC, 2),
            (SearchType.HYBRID, 0),
        ]:
            db.add(
                SearchEvent(
                    user_id=reader["id"],
                    query="Kazakh query",
                    search_type=kind,
                    result_count=results,
                    created_at=at,
                )
            )
        db.add(
            SearchEvent(
                query="outside",
                search_type=SearchType.STANDARD,
                result_count=0,
                created_at=at - timedelta(hours=1),
            )
        )
        db.add(
            UserInteraction(
                user_id=reader["id"],
                book_id=book["id"],
                interaction_type=InteractionType.VIEW,
                source=InteractionSource.CATALOG,
                created_at=at,
            )
        )
    staff.app.state.settings = staff.app.state.settings.model_copy(
        update={"library_timezone": "Asia/Qyzylorda"}
    )
    actor(UserRole.ADMIN)
    search = report(staff, "search", "2025-03-02", "2025-03-02")
    assert search["total_searches"] == 3 and search["zero_result_searches"] == 2
    assert search["zero_result_queries"] == [{"query": "Kazakh query", "count": 2}]
    assert search["zero_result_rate"] == 66.6667 and all(m["count"] == 1 for m in search["modes"])
    readers = report(staff, "readers", "2025-03-02", "2025-03-02")
    assert readers["new_readers"] == readers["active_readers"] == 1
    assert readers["registrations"] == [{"date": "2025-03-02", "count": 1}]


def test_ctr_pairs_impression_cohort_with_unique_clicks_and_real_ai_records(
    staff, actor, domain_db
):
    librarian, _ = actor()
    book = create_book(staff)
    category = staff.post(BASE + "/categories", json={"name": uuid4().hex}).json()
    reader, _ = actor(UserRole.READER)
    at = datetime(2025, 4, 2, 12, tzinfo=UTC)
    with Session(domain_db) as db, db.begin():
        for index in range(3):
            impression = RecommendationImpression(
                user_id=reader["id"],
                book_id=book["id"],
                recommendation_type=RecommendationType.POPULAR,
                source=InteractionSource.POPULAR_BOOKS,
                shown_at=at if index < 2 else at - timedelta(days=5),
                position=1,
                event_key=uuid4().hex,
            )
            db.add(impression)
            db.flush()
            if index != 1:
                db.add(
                    UserInteraction(
                        user_id=reader["id"],
                        book_id=book["id"],
                        interaction_type=InteractionType.RECOMMENDATION_CLICK,
                        source=InteractionSource.POPULAR_BOOKS,
                        recommendation_impression_id=impression.id,
                        created_at=at + timedelta(days=2),
                    )
                )
        run = CategoryPredictionRun(
            book_id=book["id"],
            requested_by=librarian["id"],
            model_name="test-fixture",
            model_revision="fixture",
            source_hash="a" * 64,
            created_at=at,
            review_status=PredictionReview.ACCEPTED,
            reviewed_by=librarian["id"],
            reviewed_at=at + timedelta(hours=1),
        )
        db.add(run)
        db.flush()
        db.add(
            CategoryPrediction(
                run_id=run.id,
                book_id=book["id"],
                category_id=category["id"],
                confidence=0.8,
                score_kind="PROBABILITY",
                created_at=at,
                accepted=True,
                reviewed_by=librarian["id"],
                reviewed_at=at + timedelta(hours=1),
            )
        )
        conversation = AIConversation(user_id=reader["id"])
        db.add(conversation)
        db.flush()
        db.add_all(
            [
                AIMessage(
                    conversation_id=conversation.id,
                    role=MessageRole.USER,
                    content="fixture private question",
                    created_at=at,
                ),
                AIMessage(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content="fixture response",
                    created_at=at,
                    latency_ms=100,
                    input_tokens=20,
                    output_tokens=10,
                ),
                AIMessage(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content="unavailable",
                    created_at=at,
                    latency_ms=200,
                    error_code="AI_SERVICE_UNAVAILABLE",
                ),
            ]
        )
    actor(UserRole.ADMIN)
    data = report(staff, "ai", "2025-04-01", "2025-04-03")
    popular = next(row for row in data["recommendations"] if row["kind"] == "POPULAR")
    assert popular == {"kind": "POPULAR", "impressions": 2, "clicks": 1, "ctr": 50.0}
    assert data["prediction_runs"] == data["predictions"] == data["accepted_predictions"] == 1
    assert data["prediction_acceptance_rate"] == 100
    assert (
        data["assistant_questions"]
        == data["assistant_successes"]
        == data["assistant_failures"]
        == 1
    )
    assert data["assistant_readers"] == data["assistant_conversations"] == 1
    assert data["assistant_average_latency_ms"] == 150 and data["input_tokens"] == 20
    assert data["responses_without_usage"] == 1 and "private question" not in str(data)


def test_reservation_terminal_rate_excludes_active(staff, actor, domain_db):
    book = create_book(staff)
    first, _ = actor(UserRole.READER)
    cancelled = reserve(staff, book)
    assert staff.post(BASE + f"/reservations/{cancelled['id']}/cancel").status_code == 200
    actor(UserRole.READER)
    waiting = reserve(staff, book)
    at = datetime(2025, 5, 2, 10, tzinfo=UTC)
    with Session(domain_db) as db, db.begin():
        for identity in [cancelled["id"], waiting["id"]]:
            row = db.get(Reservation, UUID(identity))
            row.reserved_at = at
            if row.cancelled_at:
                row.cancelled_at = at + timedelta(hours=1)
    actor(UserRole.ADMIN)
    data = report(staff, "circulation", "2025-05-01", "2025-05-03")
    assert data["reservations_created"] == 2 and data["reservations_cancelled"] == 1
    assert data["reservation_completion_rate"] == 0
    assert {row["key"]: row["count"] for row in data["reservation_cohort_status"]}["WAITING"] == 1
