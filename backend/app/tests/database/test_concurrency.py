from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.db.models import BookCopy, Borrowing, Reservation
from app.db.seed import seed_id
from app.tests.database.test_schema import loan_values, ready_values

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("kind", ["reservation", "borrowing"])
def test_two_connections_cannot_create_duplicate_copy_claims(db_engine, kind):
    copy = uuid4()
    barrier = Barrier(2)
    model = Reservation if kind == "reservation" else Borrowing
    with db_engine.begin() as connection:
        connection.execute(
            insert(BookCopy).values(
                id=copy, book_id=seed_id("book-4"), inventory_number="RACE-" + str(copy)
            )
        )

    def attempt(reader):
        values = (
            ready_values(reader=reader) if kind == "reservation" else loan_values(reader=reader)
        )
        values["book_copy_id"] = copy
        try:
            with db_engine.begin() as connection:
                connection.execute(text("SET LOCAL lock_timeout = '10s'"))
                barrier.wait(timeout=10)
                connection.execute(insert(model).values(**values))
            return "committed"
        except IntegrityError as error:
            return error.orig.diag.constraint_name

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, ("reader3", "reader4")))
    expected = (
        "uq_reservations_ready_copy" if kind == "reservation" else "uq_borrowings_active_copy"
    )
    assert sorted(outcomes) == sorted(["committed", expected])
    with db_engine.begin() as connection:
        assert (
            len(connection.scalars(select(model.id).where(model.book_copy_id == copy)).all()) == 1
        )
        connection.execute(model.__table__.delete().where(model.book_copy_id == copy))
        connection.execute(BookCopy.__table__.delete().where(BookCopy.id == copy))


def test_physical_copy_row_lock_blocks_competing_connection(db_engine):
    copy = seed_id("copy-4-0")
    with db_engine.connect() as first, db_engine.connect() as second:
        with first.begin():
            first.execute(select(BookCopy.id).where(BookCopy.id == copy).with_for_update())
            with pytest.raises(OperationalError) as error, second.begin():
                second.execute(
                    select(BookCopy.id).where(BookCopy.id == copy).with_for_update(nowait=True)
                )
            assert error.value.orig.sqlstate == "55P03"
        with second.begin():
            assert (
                second.scalar(
                    select(BookCopy.id).where(BookCopy.id == copy).with_for_update(nowait=True)
                )
                == copy
            )
