"""Real restricted-role PostgreSQL transactions, Redis limits and concurrent HTTP requests."""

import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import BytesIO
from threading import Barrier
from uuid import UUID

import pytest
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, undefer

from app.core.security import now
from app.db.enums import BorrowingStatus, CopyStatus, ReservationStatus, UserRole, UserStatus
from app.db.models import (
    AuditLog,
    BookCopy,
    Borrowing,
    Notification,
    Reservation,
    SystemSetting,
    User,
)
from app.services.reservations.qr import ReservationQR
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy

pytestmark = pytest.mark.integration
PATH = BASE + "/reservations"


def reserve(client, book, token=None, expected=201):
    response = client.post(
        PATH,
        json={"book_id": book["id"]},
        headers={"Authorization": "Bearer " + token} if token else {},
    )
    assert response.status_code == expected, response.text
    return response.json()


def cancel(client, reservation, token=None):
    response = client.post(
        PATH + f"/{reservation['id']}/cancel",
        headers={"Authorization": "Bearer " + token} if token else {},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_ready_qr_recovery_copy_state_and_no_loan(staff, actor, domain_db):
    book = create_book(staff)
    newer = create_copy(staff, book, acquired_at="2024-01-01")
    older = create_copy(staff, book, acquired_at="2020-01-01")
    user, _ = actor(UserRole.READER)
    result = reserve(staff, book)
    assert result["status"] == "READY" and result["book_copy_id"] == older["id"]
    assert result["qr_available"] and result["queue_position"] is None
    assert not any("token" in key or "cipher" in key for key in result)
    response = staff.get(PATH + f"/{result['id']}/qr")
    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "no-store"
    qr = response.json()
    assert qr == staff.get(PATH + f"/{result['id']}/qr").json()
    assert qr["token"].startswith("slr1.") and len(qr["token"]) >= 48
    Image.open(BytesIO(base64.b64decode(qr["image_data_url"].split(",")[1]))).verify()
    with Session(domain_db) as db:
        row = db.scalar(
            select(Reservation).options(undefer("*")).where(Reservation.id == result["id"])
        )
        assert row.qr_token_hash == hashlib.sha256(qr["token"].encode()).hexdigest()
        assert qr["token"] not in row.qr_token_ciphertext
        assert db.get(BookCopy, UUID(older["id"])).status == CopyStatus.RESERVED
        assert db.get(BookCopy, UUID(newer["id"])).status == CopyStatus.AVAILABLE
        assert not db.scalar(select(Borrowing.id).where(Borrowing.user_id == user["id"]))
        assert (
            db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.reservation_id == result["id"])
            )
            == 1
        )
    assert staff.get(BASE + f"/books/{book['id']}").json()["available_copies"] == 1


def test_waiting_has_no_copy_hold_or_qr(staff, actor):
    book = create_book(staff)
    actor(UserRole.READER)
    row = reserve(staff, book)
    assert row["status"] == "WAITING" and row["queue_position"] == 1
    assert all(row[key] is None for key in ("book_copy_id", "ready_at", "expires_at"))
    assert not row["qr_available"]
    response = staff.get(PATH + f"/{row['id']}/qr")
    assert (
        response.status_code == 409 and response.json()["error"]["code"] == "RESERVATION_NOT_READY"
    )


def test_cancel_advances_fifo_and_is_idempotent(staff, actor, domain_db):
    book = create_book(staff)
    copy = create_copy(staff, book)
    _, first_token = actor(UserRole.READER)
    first = reserve(staff, book)
    _, second_token = actor(UserRole.READER)
    second = reserve(staff, book)
    _, third_token = actor(UserRole.READER)
    third = reserve(staff, book)
    assert third["queue_position"] == 2
    assert cancel(staff, first, first_token)["status"] == "CANCELLED"
    assert cancel(staff, first, first_token)["status"] == "CANCELLED"
    second_now = staff.get(
        PATH + f"/{second['id']}", headers={"Authorization": "Bearer " + second_token}
    ).json()
    assert second_now["status"] == "READY" and second_now["book_copy_id"] == copy["id"]
    assert staff.get(PATH + f"/{third['id']}").json()["queue_position"] == 1
    cancel(staff, third, third_token)
    cancel(staff, second, second_token)
    with Session(domain_db) as db:
        assert db.get(BookCopy, UUID(copy["id"])).status == CopyStatus.AVAILABLE
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(
                    AuditLog.action == "RESERVATION_CANCELLED", AuditLog.entity_id == first["id"]
                )
            )
            == 1
        )
        row = db.scalar(
            select(Reservation).options(undefer("*")).where(Reservation.id == first["id"])
        )
        assert (
            row.qr_token_hash is None and row.qr_token_ciphertext is None and row.qr_key_id is None
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.reservation_id == second["id"])
            )
            == 1
        )


def test_duplicate_and_request_allowlist(staff, actor):
    book = create_book(staff)
    actor(UserRole.READER)
    reserve(staff, book)
    assert reserve(staff, book, expected=409)["error"]["code"] == "RESERVATION_ALREADY_EXISTS"
    for extra in (
        {"user_id": str(UUID(int=1))},
        {"book_copy_id": str(UUID(int=2))},
        {"status": "READY"},
    ):
        assert staff.post(PATH, json={"book_id": book["id"], **extra}).status_code == 422


def test_ownership_role_origin_and_pagination(staff, actor):
    book = create_book(staff)
    create_copy(staff, book)
    _, owner_token = actor(UserRole.READER)
    row = reserve(staff, book)
    other, _ = actor(UserRole.READER)
    for suffix in ("", "/qr"):
        assert staff.get(PATH + f"/{row['id']}" + suffix).status_code == 404
    assert staff.post(PATH + f"/{row['id']}/cancel").status_code == 404
    assert staff.get(PATH + "/me").json()["total"] == 0
    staff.headers["Authorization"] = "Bearer " + owner_token
    assert staff.get(PATH + "/me?page_size=1&status=READY").json()["items"][0]["id"] == row["id"]
    assert (
        staff.post(
            PATH + f"/{row['id']}/cancel", headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    for role in (UserRole.ADMIN, UserRole.LIBRARIAN):
        actor(role)
        assert staff.post(PATH, json={"book_id": book["id"]}).status_code == 403
        assert staff.get(PATH + "/me").status_code == 403
    staff.headers.pop("Authorization")
    assert staff.get(PATH + "/me").status_code == 401


@pytest.mark.parametrize("status", [UserStatus.BLOCKED, UserStatus.INACTIVE])
def test_account_denied(staff, actor, domain_db, status):
    book = create_book(staff)
    user, _ = actor(UserRole.READER)
    with domain_db.begin() as db:
        db.execute(update(User).where(User.id == user["id"]).values(status=status))
    assert staff.post(PATH, json={"book_id": book["id"]}).status_code == 403


def test_skip_ineligible_waiter_without_cancelling(staff, actor, domain_db):
    book = create_book(staff)
    create_copy(staff, book)
    _, first_token = actor(UserRole.READER)
    first = reserve(staff, book)
    blocked, _ = actor(UserRole.READER)
    skipped = reserve(staff, book)
    actor(UserRole.READER)
    next_row = reserve(staff, book)
    with domain_db.begin() as db:
        db.execute(update(User).where(User.id == blocked["id"]).values(status=UserStatus.BLOCKED))
    cancel(staff, first, first_token)
    with Session(domain_db) as db:
        assert db.get(Reservation, UUID(skipped["id"])).status == ReservationStatus.WAITING
        assert db.get(Reservation, UUID(next_row["id"])).status == ReservationStatus.READY


def test_live_settings_and_due_at_overdue(staff, actor, domain_db):
    librarian_id = actor()[0]["id"]
    book = create_book(staff)
    copy = create_copy(staff, book)
    target = create_book(staff)
    create_copy(staff, target)
    user, _ = actor(UserRole.READER)
    with Session(domain_db) as db, db.begin():
        db.add(
            Borrowing(
                user_id=user["id"],
                book_copy_id=copy["id"],
                issued_by=librarian_id,
                borrowed_at=now() - timedelta(days=3),
                due_at=now() - timedelta(days=1),
                status=BorrowingStatus.BORROWED,
            )
        )
        db.execute(
            update(BookCopy).where(BookCopy.id == copy["id"]).values(status=CopyStatus.BORROWED)
        )
    assert reserve(staff, target, expected=409)["error"]["code"] == "USER_HAS_OVERDUE_BOOKS"
    with domain_db.begin() as db:
        previous = dict(
            db.execute(
                select(SystemSetting.key, SystemSetting.value).where(
                    SystemSetting.key.in_(
                        ["block_reservation_if_overdue", "reservation_hold_hours"]
                    )
                )
            ).all()
        )
        db.execute(
            update(SystemSetting)
            .where(SystemSetting.key == "block_reservation_if_overdue")
            .values(value=False)
        )
        db.execute(
            update(SystemSetting)
            .where(SystemSetting.key == "reservation_hold_hours")
            .values(value=3)
        )
    try:
        result = reserve(staff, target)
        with Session(domain_db) as db:
            row = db.get(Reservation, UUID(result["id"]))
            assert row.expires_at - row.ready_at == timedelta(hours=3)
    finally:
        with domain_db.begin() as db:
            for key, value in previous.items():
                db.execute(
                    update(SystemSetting).where(SystemSetting.key == key).values(value=value)
                )


def test_expired_qr_and_transactional_reassignment(staff, actor, domain_db):
    book = create_book(staff)
    copy = create_copy(staff, book)
    _, old_token = actor(UserRole.READER)
    expired = reserve(staff, book)
    actor(UserRole.READER)
    waiting = reserve(staff, book)
    with domain_db.begin() as db:
        db.execute(
            update(Reservation)
            .where(Reservation.id == expired["id"])
            .values(
                reserved_at=now() - timedelta(days=4),
                ready_at=now() - timedelta(days=3),
                expires_at=now() - timedelta(days=1),
            )
        )
    denied = staff.get(
        PATH + f"/{expired['id']}/qr", headers={"Authorization": "Bearer " + old_token}
    )
    assert denied.status_code == 409 and denied.json()["error"]["code"] == "RESERVATION_EXPIRED"
    actor(UserRole.READER)
    newer = reserve(staff, book)
    assert newer["status"] == "WAITING"
    with Session(domain_db) as db:
        assert db.get(Reservation, UUID(waiting["id"])).book_copy_id == UUID(copy["id"])
        assert db.get(Reservation, UUID(expired["id"])).status == ReservationStatus.EXPIRED
    assert cancel(staff, expired, old_token)["status"] == "EXPIRED"


def test_crypto_failure_rolls_back_allocation(staff, actor, domain_db):
    book = create_book(staff)
    copy = create_copy(staff, book)
    actor(UserRole.READER)
    configured = staff.app.state.settings
    previous = configured.qr_encryption_key
    configured.qr_encryption_key = SecretStr("invalid-key")
    try:
        assert reserve(staff, book, expected=503)["error"]["code"] == "QR_SERVICE_UNAVAILABLE"
        with Session(domain_db) as db:
            assert db.get(BookCopy, UUID(copy["id"])).status == CopyStatus.AVAILABLE
            assert not db.scalar(select(Reservation.id).where(Reservation.book_id == book["id"]))
    finally:
        configured.qr_encryption_key = previous


@pytest.mark.parametrize("same_reader", [False, True])
def test_simultaneous_reservation_serialization(staff, actor, domain_db, same_reader):
    book = create_book(staff)
    copy = create_copy(staff, book)
    _, token_a = actor(UserRole.READER)
    token_b = token_a if same_reader else actor(UserRole.READER)[1]
    barrier = Barrier(2)

    def send(token):
        barrier.wait(timeout=10)
        return staff.post(
            PATH, json={"book_id": book["id"]}, headers={"Authorization": "Bearer " + token}
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send, (token_a, token_b)))
    assert sorted(r.status_code for r in responses) == ([201, 409] if same_reader else [201, 201])
    if not same_reader:
        assert sorted(r.json()["status"] for r in responses) == ["READY", "WAITING"]
    with Session(domain_db) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Reservation)
                .where(
                    Reservation.book_copy_id == copy["id"],
                    Reservation.status == ReservationStatus.READY,
                )
            )
            == 1
        )


def test_concurrent_cancel_advances_once(staff, actor, domain_db):
    book = create_book(staff)
    create_copy(staff, book)
    _, token = actor(UserRole.READER)
    ready = reserve(staff, book)
    actor(UserRole.READER)
    waiting = reserve(staff, book)
    barrier = Barrier(2)

    def send(_):
        barrier.wait(timeout=10)
        return cancel(staff, ready, token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(r["status"] == "CANCELLED" for r in pool.map(send, range(2)))
    with Session(domain_db) as db:
        assert db.get(Reservation, UUID(waiting["id"])).status == ReservationStatus.READY
        assert (
            db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.reservation_id == waiting["id"])
            )
            == 1
        )


def test_qr_ciphertext_and_key_tampering_fail_closed(staff):
    qr = ReservationQR(staff.app.state.settings)
    digest, cipher, key = qr.generate()
    assert qr.recover(cipher, digest, key).startswith("slr1.")
    from app.core.errors import AppError

    for values in (
        (cipher, "0" * 64, key),
        (cipher, digest, "unknown"),
        (cipher[:-4] + "xxxx", digest, key),
    ):
        with pytest.raises(AppError, match="QR_SERVICE_UNAVAILABLE"):
            qr.recover(*values)
