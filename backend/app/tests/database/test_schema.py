from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    UniqueConstraint,
    Uuid,
    insert,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from app.db.models import (
    Book,
    BookAuthor,
    BookCategory,
    BookCopy,
    Borrowing,
    Favorite,
    Notification,
    Reservation,
    User,
    UserCategoryPreference,
)
from app.db.seed import seed_id

pytestmark = pytest.mark.integration


def reject(connection, statement, constraint):
    with pytest.raises(IntegrityError) as error, connection.begin_nested():
        connection.execute(statement)
    assert error.value.orig.diag.constraint_name == constraint


def ready_values(reader="reader3", book="book-4", copy="copy-4-0"):
    now = datetime.now(UTC)
    return dict(
        user_id=seed_id(reader),
        book_id=seed_id(book),
        book_copy_id=seed_id(copy),
        status="READY",
        reserved_at=now,
        ready_at=now,
        expires_at=now + timedelta(hours=48),
        qr_token_hash=uuid4().hex + uuid4().hex,
        qr_token_ciphertext="test-ciphertext",
        qr_key_id="isolated-test",
    )


def loan_values(reader="reader3", copy="copy-4-0"):
    now = datetime.now(UTC)
    return dict(
        user_id=seed_id(reader),
        book_copy_id=seed_id(copy),
        issued_by=seed_id("librarian"),
        borrowed_at=now,
        due_at=now + timedelta(days=14),
        status="BORROWED",
    )


def test_catalog_matches_metadata(connection):
    inspector = inspect(connection)
    assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
    extensions = set(connection.scalars(text("SELECT extname FROM pg_extension")))
    assert {"vector", "pg_trgm"} <= extensions
    enum_values = {enum["name"]: enum["labels"] for enum in inspector.get_enums()}
    preparer = connection.dialect.identifier_preparer
    for table in Base.metadata.sorted_tables:
        actual = {column["name"]: column for column in inspector.get_columns(table.name)}
        assert set(actual) == set(table.columns.keys())
        assert inspector.get_pk_constraint(table.name)["constrained_columns"] == ["id"]
        assert isinstance(actual["id"]["type"], Uuid)
        for column in table.columns:
            if isinstance(column.type, DateTime):
                assert actual[column.name]["type"].timezone
            if isinstance(column.type, Enum):
                assert enum_values[column.type.name] == column.type.enums
        assert {
            preparer.truncate_and_render_constraint_name(c.name, _alembic_quote=False)
            for c in table.foreign_key_constraints
        } == {c["name"] for c in inspector.get_foreign_keys(table.name)}
        for kind, actual in (
            (CheckConstraint, inspector.get_check_constraints(table.name)),
            (UniqueConstraint, inspector.get_unique_constraints(table.name)),
        ):
            assert {
                preparer.truncate_and_render_constraint_name(c.name, _alembic_quote=False)
                for c in table.constraints
                if isinstance(c, kind)
            } == {c["name"] for c in actual}
        assert {i.name for i in table.indexes} <= {
            i["name"] for i in inspector.get_indexes(table.name)
        }


@pytest.mark.parametrize(
    "values,constraint",
    [
        ({"page_count": -1}, "ck_books_page_count"),
        ({"publication_year": 0}, "ck_books_publication_year"),
        ({"title": " "}, "ck_books_title"),
        ({"isbn": "not-an-isbn"}, "ck_books_isbn"),
        ({"language": ""}, "ck_books_language"),
    ],
)
def test_invalid_book_values(connection, values, constraint):
    reject(
        connection, update(Book).where(Book.id == seed_id("book-0")).values(**values), constraint
    )


def test_optional_isbn_and_historical_year(connection):
    connection.execute(
        insert(Book),
        [
            {"title": "Older work", "language": "en", "publication_year": 100},
            {"title": "Unknown edition", "language": "kk", "publication_year": None},
        ],
    )
    connection.execute(
        update(Book).where(Book.id == seed_id("book-0")).values(isbn="9780132350884")
    )
    reject(
        connection,
        update(Book).where(Book.id == seed_id("book-1")).values(isbn="9780132350884"),
        "uq_books_isbn",
    )


def test_unique_email_inventory_and_associations(connection):
    reject(
        connection,
        update(User)
        .where(User.id == seed_id("reader2"))
        .values(email="reader1@smartlibrary.example"),
        "uq_users_email",
    )
    reject(
        connection,
        update(BookCopy)
        .where(BookCopy.id == seed_id("copy-0-1"))
        .values(inventory_number="DEV-001-01"),
        "uq_book_copies_inventory_number",
    )
    cases = [
        (
            Favorite,
            dict(user_id=seed_id("reader1"), book_id=seed_id("book-1")),
            "uq_favorites_user_id",
        ),
        (
            BookAuthor,
            dict(book_id=seed_id("book-0"), author_id=seed_id("author-0")),
            "uq_book_authors_book_id",
        ),
        (
            BookCategory,
            dict(book_id=seed_id("book-0"), category_id=seed_id("Fiction")),
            "uq_book_categories_book_id",
        ),
        (
            UserCategoryPreference,
            dict(user_id=seed_id("reader1"), category_id=seed_id("Programming")),
            "uq_user_category_preferences_user_id",
        ),
    ]
    for model, values, constraint in cases:
        reject(connection, insert(model).values(**values), constraint)


def test_reservation_duplicate_and_fifo(connection):
    reject(
        connection,
        insert(Reservation).values(user_id=seed_id("reader3"), book_id=seed_id("book-1")),
        "uq_reservations_active_user_book",
    )
    rows = connection.scalars(
        select(Reservation.user_id)
        .where(Reservation.book_id == seed_id("book-1"), Reservation.status == "WAITING")
        .order_by(Reservation.reserved_at, Reservation.id)
    ).all()
    assert rows == [seed_id("reader3"), seed_id("reader4")]
    reject(
        connection,
        insert(Reservation).values(**ready_values(book="book-5", copy="copy-0-1")),
        "fk_reservations_copy_book",
    )


def test_copy_cannot_have_two_ready_reservations(connection):
    values = ready_values()
    connection.execute(insert(Reservation).values(**values))
    reject(
        connection,
        insert(Reservation).values(**ready_values(reader="reader4")),
        "uq_reservations_ready_copy",
    )


def test_active_loan_uniqueness_and_history(connection):
    connection.execute(insert(Borrowing).values(**loan_values()))
    reject(
        connection,
        insert(Borrowing).values(**loan_values(reader="reader4")),
        "uq_borrowings_active_copy",
    )
    historical = loan_values()
    historical.update(
        status="RETURNED", returned_at=historical["borrowed_at"], returned_by=seed_id("librarian")
    )
    connection.execute(insert(Borrowing).values(**historical))


def test_loan_reservation_owner_and_copy_must_match(connection):
    reservation_id = uuid4()
    reservation = ready_values(reader="reader2")
    reservation.update(id=reservation_id)
    connection.execute(insert(Reservation).values(**reservation))
    values = loan_values(reader="reader1")
    values["reservation_id"] = reservation_id
    reject(connection, insert(Borrowing).values(**values), "fk_borrowings_reservation_assignment")
    values["user_id"] = seed_id("reader2")
    values.update(
        status="RETURNED", returned_at=values["borrowed_at"], returned_by=seed_id("librarian")
    )
    connection.execute(insert(Borrowing).values(**values))
    reject(connection, insert(Borrowing).values(**values), "uq_borrowings_reservation_id")


def test_qr_and_timestamp_states(connection):
    values = ready_values()
    values["qr_token_hash"] = None
    reject(connection, insert(Reservation).values(**values), "ck_reservations_qr_lifecycle")
    values = loan_values()
    values["due_at"] = values["borrowed_at"]
    reject(connection, insert(Borrowing).values(**values), "ck_borrowings_due_date")
    reject(
        connection,
        update(Borrowing).where(Borrowing.id == seed_id("active-loan")).values(status="RETURNED"),
        "ck_borrowings_state_fields",
    )


def test_notification_deduplication_and_owner_reference(connection):
    values = dict(
        user_id=seed_id("reader1"),
        type="RESERVATION_READY",
        title="Ready",
        message="Pickup",
        related_entity_type="RESERVATION",
        reservation_id=seed_id("ready"),
        event_key="dev-reservation-ready",
    )
    reject(connection, insert(Notification).values(**values), "uq_notifications_user_id")
    values.update(user_id=seed_id("reader2"), event_key="different")
    reject(connection, insert(Notification).values(**values), "fk_notifications_reservation_owner")
    row = connection.execute(
        select(Notification.related_entity_id, Notification.reservation_id).where(
            Notification.event_key == "dev-reservation-ready"
        )
    ).one()
    assert row.related_entity_id == row.reservation_id


def test_history_restricts_delete_and_archive_preserves_data(connection):
    reject(
        connection,
        BookCopy.__table__.delete().where(BookCopy.id == seed_id("copy-1-0")),
        "fk_borrowings_book_copy_id_book_copies",
    )
    reject(
        connection,
        Book.__table__.delete().where(Book.id == seed_id("book-0")),
        "fk_book_copies_book_id_books",
    )
    connection.execute(
        update(Book).where(Book.id == seed_id("book-0")).values(archived_at=datetime.now(UTC))
    )
    assert connection.scalar(select(Reservation.id).where(Reservation.id == seed_id("ready")))


def test_transaction_failure_rolls_back_all_changes(db_engine):
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            update(BookCopy).where(BookCopy.id == seed_id("copy-4-0")).values(status="BORROWED")
        )
        values = loan_values()
        values["due_at"] = values["borrowed_at"]
        connection.execute(insert(Borrowing).values(**values))
    with db_engine.connect() as connection:
        assert (
            connection.scalar(select(BookCopy.status).where(BookCopy.id == seed_id("copy-4-0")))
            == "AVAILABLE"
        )
