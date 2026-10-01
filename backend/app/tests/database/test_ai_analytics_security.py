import hashlib
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.db.models import (
    AIConversation,
    AIMessage,
    AIMessageBook,
    BookEmbedding,
    CategoryPrediction,
    CategoryPredictionRun,
    CategoryPredictionSelection,
    EmbeddingModel,
    RecommendationImpression,
    RefreshSession,
    SystemSetting,
    User,
    UserInteraction,
)
from app.db.seed import seed_development, seed_id
from app.tests.database.test_schema import reject

pytestmark = pytest.mark.integration


def test_vector_spaces_enforce_dimension_and_actual_distance(connection):
    model = uuid4()
    other = uuid4()
    connection.execute(
        insert(EmbeddingModel),
        [
            dict(
                id=model,
                model_name="isolated-vector-test",
                revision="v1",
                dimension=3,
                source_recipe="test",
            ),
            dict(
                id=other,
                model_name="isolated-vector-test",
                revision="v2",
                dimension=4,
                source_recipe="test",
            ),
        ],
    )
    for index, vector in enumerate(([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])):
        connection.execute(
            insert(BookEmbedding).values(
                book_id=seed_id(f"book-{index}"),
                model_id=model,
                dimension=3,
                embedding=vector,
                source_hash="a" * 64,
            )
        )
    nearest = connection.scalar(
        select(BookEmbedding.book_id)
        .where(BookEmbedding.model_id == model)
        .order_by(BookEmbedding.embedding.cosine_distance([1.0, 0.0, 0.0]))
        .limit(1)
    )
    assert nearest == seed_id("book-0")
    reject(
        connection,
        insert(BookEmbedding).values(
            book_id=seed_id("book-3"),
            model_id=model,
            dimension=3,
            embedding=[1, 2, 3, 4],
            source_hash="a" * 64,
        ),
        "ck_book_embeddings_dimension",
    )
    reject(
        connection,
        insert(BookEmbedding).values(
            book_id=seed_id("book-3"),
            model_id=model,
            dimension=4,
            embedding=[1, 2, 3, 4],
            source_hash="a" * 64,
        ),
        "fk_book_embeddings_model_dimension",
    )
    reject(
        connection,
        insert(BookEmbedding).values(
            book_id=seed_id("book-3"),
            model_id=model,
            dimension=3,
            embedding=[0, 0, 0],
            source_hash="a" * 64,
        ),
        "ck_book_embeddings_nonzero_vector",
    )
    connection.execute(
        insert(BookEmbedding).values(
            book_id=seed_id("book-0"),
            model_id=other,
            dimension=4,
            embedding=[1, 0, 0, 0],
            source_hash="a" * 64,
        )
    )
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(
            update(EmbeddingModel).where(EmbeddingModel.id == model).values(revision="v3")
        )


def test_trigram_search_is_real_postgresql(connection):
    assert connection.scalar(text("SELECT similarity('Clean Code', 'Clen Code')")) > 0.4
    indexes = connection.scalars(
        text(
            "SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE '%trgm'"
        )
    ).all()
    assert len(indexes) == 5
    assert all("gin_trgm_ops" in definition for definition in indexes)


def test_prediction_review_and_existing_categories(connection):
    run = uuid4()
    prediction = uuid4()
    connection.execute(
        insert(CategoryPredictionRun).values(
            id=run,
            book_id=seed_id("book-0"),
            requested_by=seed_id("librarian"),
            model_name="isolated-constraint-test",
            model_revision="v1",
            source_hash="a" * 64,
            configuration={"threshold": 0.5},
        )
    )
    values = dict(
        id=prediction,
        run_id=run,
        book_id=seed_id("book-0"),
        category_id=seed_id("History"),
        confidence=0.8,
        score_kind="PROBABILITY",
    )
    connection.execute(insert(CategoryPrediction).values(**values))
    reject(
        connection,
        update(CategoryPrediction)
        .where(CategoryPrediction.id == prediction)
        .values(confidence=1.2),
        "ck_category_predictions_score",
    )
    reject(
        connection,
        update(CategoryPrediction)
        .where(CategoryPrediction.id == prediction)
        .values(category_id=uuid4()),
        "fk_category_predictions_category_id_categories",
    )
    reject(
        connection,
        update(CategoryPrediction)
        .where(CategoryPrediction.id == prediction)
        .values(accepted=False),
        "ck_category_predictions_review",
    )
    assert (
        connection.scalar(
            select(CategoryPrediction.accepted).where(CategoryPrediction.id == prediction)
        )
        is None
    )
    connection.execute(
        update(CategoryPrediction)
        .where(CategoryPrediction.id == prediction)
        .values(accepted=False, reviewed_by=seed_id("librarian"), reviewed_at=datetime.now(UTC))
    )
    connection.execute(
        update(CategoryPredictionRun)
        .where(CategoryPredictionRun.id == run)
        .values(
            review_status="MODIFIED",
            reviewed_by=seed_id("librarian"),
            reviewed_at=datetime.now(UTC),
        )
    )
    connection.execute(
        insert(CategoryPredictionSelection).values(run_id=run, category_id=seed_id("Fiction"))
    )


def test_impression_click_attribution_and_deduplication(connection):
    impression = uuid4()
    connection.execute(
        insert(RecommendationImpression).values(
            id=impression,
            user_id=seed_id("reader1"),
            book_id=seed_id("book-0"),
            recommendation_type="PERSONALIZED",
            source="RECOMMENDATION",
            shown_at=datetime.now(UTC),
            position=1,
            event_key=str(uuid4()),
        )
    )
    values = dict(
        user_id=seed_id("reader1"),
        book_id=seed_id("book-0"),
        interaction_type="RECOMMENDATION_CLICK",
        source="RECOMMENDATION",
        recommendation_impression_id=impression,
    )
    wrong = dict(values, user_id=seed_id("reader2"))
    reject(
        connection,
        insert(UserInteraction).values(**wrong),
        "fk_user_interactions_impression_owner_book",
    )
    connection.execute(insert(UserInteraction).values(**values))
    reject(
        connection,
        insert(UserInteraction).values(**values),
        "uq_user_interactions_impression_click",
    )


def test_ai_messages_require_owned_conversation_and_real_book_reference(connection):
    conversation = uuid4()
    message = uuid4()
    connection.execute(insert(AIConversation).values(id=conversation, user_id=seed_id("reader1")))
    connection.execute(
        insert(AIMessage).values(
            id=message,
            conversation_id=conversation,
            role="ASSISTANT",
            content="Isolated schema test",
        )
    )
    reject(
        connection,
        insert(AIMessageBook).values(message_id=message, book_id=uuid4(), position=1),
        "fk_ai_message_books_book_id_books",
    )
    connection.execute(
        insert(AIMessageBook).values(message_id=message, book_id=seed_id("book-0"), position=1)
    )
    assert connection.scalar(
        select(AIConversation.user_id).where(AIConversation.id == conversation)
    ) == seed_id("reader1")


def test_rotated_refresh_credentials_are_hashed_and_same_family(connection):
    parent, family = uuid4(), uuid4()
    common = dict(
        user_id=seed_id("reader1"),
        family_id=family,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    connection.execute(insert(RefreshSession).values(id=parent, token_hash="a" * 64, **common))
    reject(
        connection,
        insert(RefreshSession).values(
            parent_id=parent, token_hash="b" * 64, **dict(common, user_id=seed_id("reader2"))
        ),
        "fk_refresh_sessions_parent_family",
    )
    connection.execute(
        insert(RefreshSession).values(parent_id=parent, token_hash="b" * 64, **common)
    )
    reject(
        connection,
        insert(RefreshSession).values(parent_id=parent, token_hash="c" * 64, **common),
        "uq_refresh_sessions_parent_id",
    )
    reject(
        connection,
        insert(RefreshSession).values(token_hash="raw-refresh-token", **common),
        "ck_refresh_sessions_token_hash",
    )
    connection.execute(
        update(RefreshSession)
        .where(RefreshSession.family_id == family)
        .values(revoked_at=datetime.now(UTC))
    )


@pytest.mark.parametrize("value", [-1, 0, 1.5, "14", None, True, 366])
def test_invalid_typed_setting_values(connection, value):
    reject(
        connection,
        update(SystemSetting).where(SystemSetting.key == "borrow_period_days").values(value=value),
        "ck_system_settings_typed_value",
    )


def test_setting_updates_and_automatic_timestamp(connection):
    before = connection.scalar(
        select(SystemSetting.updated_at).where(SystemSetting.key == "borrow_period_days")
    )
    connection.execute(
        text("UPDATE system_settings SET value = '21'::jsonb WHERE key = 'borrow_period_days'")
    )
    row = connection.execute(
        select(SystemSetting.value, SystemSetting.updated_at).where(
            SystemSetting.key == "borrow_period_days"
        )
    ).one()
    assert row.value == 21 and row.updated_at >= before


def test_audit_records_are_immutable_even_for_migrator(connection):
    for statement in (
        text("UPDATE audit_logs SET action = 'CHANGED'"),
        text("DELETE FROM audit_logs"),
        text("TRUNCATE audit_logs"),
    ):
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(statement)


def test_runtime_database_privileges(runtime_engine, db_engine):
    with runtime_engine.connect() as connection:
        with connection.begin():
            role = connection.execute(
                text(
                    "SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls "
                    "FROM pg_roles WHERE rolname = current_user"
                )
            ).one()
            assert not any(role)
            assert (
                connection.scalar(
                    text("SELECT value FROM system_settings WHERE key='max_books_per_user'")
                )
                == 5
            )
            for statement in (
                "CREATE TABLE forbidden (id int)",
                "DELETE FROM borrowings",
                "UPDATE audit_logs SET action = 'CHANGED'",
                "DELETE FROM audit_logs",
                "TRUNCATE audit_logs",
                "UPDATE system_settings SET minimum = -1",
                "SELECT * FROM alembic_version",
            ):
                with pytest.raises(DBAPIError), connection.begin_nested():
                    connection.execute(text(statement))
            connection.execute(
                text("UPDATE system_settings SET value='21'::jsonb WHERE key='borrow_period_days'")
            )
        with connection.begin():
            connection.execute(
                text("UPDATE system_settings SET value='14'::jsonb WHERE key='borrow_period_days'")
            )
    with db_engine.connect() as connection:
        role = connection.execute(
            text(
                "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles "
                "WHERE rolname=current_user"
            )
        ).one()
        assert not any(role)


def test_seed_passwords_qr_and_repeat_preserve_data(db_engine, test_database_name):
    with db_engine.connect() as connection:
        password_hash = connection.scalar(
            select(User.password_hash).where(User.id == seed_id("reader1"))
        )
        assert PasswordHasher().verify(password_hash, os.environ["DEV_SEED_PASSWORD"])
        before = connection.scalar(text("SELECT count(*) FROM users"))
        assert before == 6
        row = connection.execute(
            text("SELECT qr_token_hash, qr_token_ciphertext FROM reservations WHERE status='READY'")
        ).one()
        key = os.environ["QR_ENCRYPTION_KEY"]
        plain = Fernet((key + "=" * (-len(key) % 4)).encode()).decrypt(
            row.qr_token_ciphertext.encode()
        )
        assert hashlib.sha256(plain).hexdigest() == row.qr_token_hash
        assert connection.scalar(text("SELECT count(*) FROM book_embeddings")) == 0
        assert connection.scalar(text("SELECT count(*) FROM category_predictions")) == 0
    seed_development(test_database_name)
    with db_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM users")) == before
        assert (
            connection.scalar(select(User.password_hash).where(User.id == seed_id("reader1")))
            == password_hash
        )


def test_seed_refuses_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ValueError, match="disabled"):
        seed_development()
