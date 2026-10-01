from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, undefer

from app.core.errors import AppError
from app.core.security import now
from app.db.enums import BorrowingStatus, CopyStatus, ReservationStatus, UserRole, UserStatus
from app.db.models import BookCopy, Borrowing, Notification, Reservation, SystemSetting, User
from app.services.notifications.scheduled import ScheduledCirculation
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy
from app.tests.database.domain.test_reservations import cancel, reserve

pytestmark = pytest.mark.integration


def jobs(client):
    return ScheduledCirculation(client.app.state.db, client.app.state.settings)


def count(db, kind, identity):
    with Session(db) as session:
        return session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.event_key == f"{kind}:{identity}")
        )


def ready_queue(client, actor, domain_db, waiters=2):
    actor()
    book = create_book(client)
    copy = create_copy(client, book)
    actor(UserRole.READER)
    first = reserve(client, book)
    waiting = []
    for _ in range(waiters):
        actor(UserRole.READER)
        waiting.append(reserve(client, book))
    with domain_db.begin() as db:
        db.execute(
            update(Reservation)
            .where(Reservation.id == first["id"])
            .values(
                reserved_at=now() - timedelta(days=4),
                ready_at=now() - timedelta(days=3),
                expires_at=now() - timedelta(minutes=1),
            )
        )
    return book, copy, first, waiting


def loan(client, actor, domain_db, due_days):
    _, token = actor()
    book = create_book(client)
    copy = create_copy(client, book)
    reader, _ = actor(UserRole.READER)
    client.headers["Authorization"] = "Bearer " + token
    response = client.post(
        BASE + "/librarian/borrowings",
        json={"book_copy_id": copy["id"], "user_id": reader["id"], "idempotency_key": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    row = response.json()
    with domain_db.begin() as db:
        db.execute(
            update(Borrowing)
            .where(Borrowing.id == row["id"])
            .values(borrowed_at=now() - timedelta(days=10), due_at=now() + timedelta(days=due_days))
        )
    return row, token


@pytest.mark.parametrize("waiters", [0, 2])
def test_expiration_reuses_copy_fifo_clears_qr_and_is_repeatable(client, actor, domain_db, waiters):
    book, copy, first, waiting = ready_queue(client, actor, domain_db, waiters)
    assert jobs(client).expiration(UUID(book["id"])) == 1
    assert jobs(client).expiration(UUID(book["id"])) == 0
    with Session(domain_db) as db:
        old = db.scalar(
            select(Reservation)
            .options(undefer(Reservation.qr_token_hash))
            .where(Reservation.id == first["id"])
        )
        assert old.status == ReservationStatus.EXPIRED and old.qr_token_hash is None
        assert db.get(BookCopy, UUID(copy["id"])).status == (
            CopyStatus.RESERVED if waiters else CopyStatus.AVAILABLE
        )
        if waiting:
            next_row = db.get(Reservation, UUID(waiting[0]["id"]))
            assert next_row.status == ReservationStatus.READY and next_row.book_copy_id == UUID(
                copy["id"]
            )
            assert db.get(Reservation, UUID(waiting[1]["id"])).status == ReservationStatus.WAITING
    assert count(domain_db, "RESERVATION_EXPIRED", first["id"]) == 1


def test_concurrent_expiration_advances_only_once(client, actor, domain_db):
    book, copy, first, waiting = ready_queue(client, actor, domain_db)
    barrier = Barrier(2)

    def run():
        barrier.wait(timeout=10)
        return jobs(client).expiration(UUID(book["id"]))

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(results) == [0, 1]
    with Session(domain_db) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Reservation)
                .where(
                    Reservation.book_id == book["id"], Reservation.status == ReservationStatus.READY
                )
            )
            == 1
        )
    assert count(domain_db, "RESERVATION_READY", waiting[0]["id"]) == 1


def test_crypto_failure_rolls_back_expiry_and_recovers(client, actor, domain_db):
    book, copy, first, waiting = ready_queue(client, actor, domain_db)
    bad = client.app.state.settings.model_copy(update={"qr_encryption_key": SecretStr("invalid")})
    with pytest.raises(AppError) as error:
        ScheduledCirculation(client.app.state.db, bad).expiration(UUID(book["id"]))
    assert error.value.code == "QR_SERVICE_UNAVAILABLE"
    with Session(domain_db) as db:
        assert db.get(Reservation, UUID(first["id"])).status == ReservationStatus.READY
        assert db.get(Reservation, UUID(waiting[0]["id"])).status == ReservationStatus.WAITING
        assert db.get(BookCopy, UUID(copy["id"])).status == CopyStatus.RESERVED
    assert count(domain_db, "RESERVATION_EXPIRED", first["id"]) == 0
    assert jobs(client).expiration(UUID(book["id"])) == 1


def test_reminders_use_current_settings_and_persist_deduplication(client, actor, domain_db):
    row, _ = loan(client, actor, domain_db, 3)
    assert jobs(client).borrowing(UUID(row["id"])) is False
    with domain_db.begin() as db:
        previous = db.scalar(
            select(SystemSetting.value).where(SystemSetting.key == "return_reminder_days")
        )
        db.execute(
            update(SystemSetting).where(SystemSetting.key == "return_reminder_days").values(value=4)
        )
    try:
        assert jobs(client).borrowing(UUID(row["id"])) is True
        assert jobs(client).borrowing(UUID(row["id"])) is False
        assert count(domain_db, "DUE_SOON", row["id"]) == 1
        with domain_db.begin() as db:
            db.execute(
                update(Borrowing)
                .where(Borrowing.id == row["id"])
                .values(due_at=now() - timedelta(days=1))
            )
        assert jobs(client).borrowing(UUID(row["id"])) is True
        assert jobs(client).borrowing(UUID(row["id"])) is False
        with Session(domain_db) as db:
            assert db.get(Borrowing, UUID(row["id"])).status == BorrowingStatus.OVERDUE
        assert count(domain_db, "OVERDUE", row["id"]) == 1
    finally:
        with domain_db.begin() as db:
            db.execute(
                update(SystemSetting)
                .where(SystemSetting.key == "return_reminder_days")
                .values(value=previous)
            )


def test_pickup_reminder_config_and_cancelled_not_notified(client, actor, domain_db):
    actor()
    book = create_book(client)
    create_copy(client, book)
    actor(UserRole.READER)
    row = reserve(client, book)
    with domain_db.begin() as db:
        db.execute(
            update(Reservation)
            .where(Reservation.id == row["id"])
            .values(expires_at=now() + timedelta(hours=2))
        )
        previous = db.scalar(
            select(SystemSetting.value).where(SystemSetting.key == "reservation_reminder_hours")
        )
        db.execute(
            update(SystemSetting)
            .where(SystemSetting.key == "reservation_reminder_hours")
            .values(value=0)
        )
    try:
        assert not jobs(client).upcoming_reservation(UUID(row["id"]))
        with domain_db.begin() as db:
            db.execute(
                update(SystemSetting)
                .where(SystemSetting.key == "reservation_reminder_hours")
                .values(value=3)
            )
        assert jobs(client).upcoming_reservation(UUID(row["id"]))
        assert not jobs(client).upcoming_reservation(UUID(row["id"]))
        cancel(client, row)
        assert not jobs(client).upcoming_reservation(UUID(row["id"]))
        assert count(domain_db, "RESERVATION_EXPIRING", row["id"]) == 1
    finally:
        with domain_db.begin() as db:
            db.execute(
                update(SystemSetting)
                .where(SystemSetting.key == "reservation_reminder_hours")
                .values(value=previous)
            )


def test_concurrent_return_and_overdue_do_not_resurrect_loan(client, actor, domain_db):
    row, token = loan(client, actor, domain_db, -1)
    barrier = Barrier(2)

    def run_job():
        barrier.wait(timeout=10)
        return jobs(client).borrowing(UUID(row["id"]))

    def run_return():
        barrier.wait(timeout=10)
        return client.post(
            BASE + f"/librarian/borrowings/{row['id']}/return",
            json={"condition": "GOOD"},
            headers={"Authorization": "Bearer " + token},
        )

    with ThreadPoolExecutor(2) as pool:
        job = pool.submit(run_job)
        returned = pool.submit(run_return)
        job.result(timeout=20)
        assert returned.result(timeout=20).status_code == 200
    assert not jobs(client).borrowing(UUID(row["id"]))
    with Session(domain_db) as db:
        assert db.get(Borrowing, UUID(row["id"])).status == BorrowingStatus.RETURNED


def test_sweep_skips_delivered_items_and_drains_bounded_batches(client, actor, domain_db):
    rows = [loan(client, actor, domain_db, -1)[0] for _ in range(3)]
    for _ in range(30):
        result = jobs(client).sweep(limit=1)
        assert result["failed"] == 0
        if all(count(domain_db, "OVERDUE", row["id"]) == 1 for row in rows):
            break
    assert all(count(domain_db, "OVERDUE", row["id"]) == 1 for row in rows)
    assert jobs(client).sweep()["failed"] == 0
    assert jobs(client).sweep() == {
        "expired": 0,
        "assigned": 0,
        "pickup_reminders": 0,
        "loan_notifications": 0,
        "failed": 0,
    }


def test_restored_reader_eligibility_reconciles_without_duplicate_assignment(
    client, actor, domain_db
):
    book, copy, first, waiting = ready_queue(client, actor, domain_db, waiters=1)
    with Session(domain_db) as db, db.begin():
        reader = db.get(Reservation, UUID(waiting[0]["id"])).user_id
        db.get(User, reader).status = UserStatus.BLOCKED
    assert jobs(client).expiration(UUID(book["id"])) == 1
    assert jobs(client).reconcile(UUID(book["id"])) == 0
    with Session(domain_db) as db, db.begin():
        assert db.get(BookCopy, UUID(copy["id"])).status == CopyStatus.AVAILABLE
        db.get(User, reader).status = UserStatus.ACTIVE
    barrier = Barrier(2)

    def run():
        barrier.wait(timeout=10)
        return jobs(client).sweep()

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert all(result["failed"] == 0 for result in results)
    with Session(domain_db) as db:
        row = db.get(Reservation, UUID(waiting[0]["id"]))
        assert row.status == ReservationStatus.READY
        assert row.book_copy_id == UUID(copy["id"])
        assert db.get(BookCopy, UUID(copy["id"])).status == CopyStatus.RESERVED
    assert count(domain_db, "RESERVATION_READY", waiting[0]["id"]) == 1
