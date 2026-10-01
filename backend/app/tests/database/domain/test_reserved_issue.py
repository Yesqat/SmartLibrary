from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import UUID, uuid4

import jwt
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, undefer

from app.core.security import now
from app.db.enums import BorrowingStatus, CopyStatus, ReservationStatus, UserRole, UserStatus
from app.db.models import AuditLog, BookCopy, Borrowing, Reservation, SystemSetting, User
from app.services.borrowings.proof import AUDIENCE, proof_key
from app.tests.database.domain.support import PrivateContext
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy
from app.tests.database.domain.test_reservations import PATH, cancel, reserve

pytestmark = pytest.mark.integration
VERIFY = BASE + "/librarian/qr/verify"


@pytest.fixture
def pickup(staff, actor):
    librarian, librarian_token = actor()
    book = create_book(staff)
    copy = create_copy(staff, book)
    reader, reader_token = actor(UserRole.READER)
    reservation = reserve(staff, book)
    qr = staff.get(PATH + f"/{reservation['id']}/qr").json()["token"]
    staff.headers["Authorization"] = "Bearer " + librarian_token
    return PrivateContext(
        {
            "book": book,
            "copy": copy,
            "reader": reader,
            "reservation": reservation,
            "qr": qr,
            "librarian": librarian,
            "staff_token": librarian_token,
            "reader_token": reader_token,
        }
    )


def verify(client, pickup):
    response = client.post(VERIFY, json={"token": pickup["qr"]})
    assert response.status_code == 200, response.text
    return response.json()


def issue(client, reservation_id, proof, token=None):
    return client.post(
        BASE + f"/librarian/reservations/{reservation_id}/issue",
        json={"verification_token": proof},
        headers={"Authorization": "Bearer " + token} if token else {},
    )


def test_verify_never_issues_and_explicit_issue_is_atomic_idempotent(staff, pickup, domain_db):
    preview = verify(staff, pickup)
    assert preview["inventory_number"] == pickup["copy"]["inventory_number"]
    assert "email" not in preview and "phone" not in preview and pickup["qr"] not in str(preview)
    with Session(domain_db) as db:
        assert not db.scalar(
            select(Borrowing.id).where(Borrowing.reservation_id == pickup["reservation"]["id"])
        )
        assert (
            db.get(Reservation, UUID(pickup["reservation"]["id"])).status == ReservationStatus.READY
        )
        assert db.get(BookCopy, UUID(pickup["copy"]["id"])).status == CopyStatus.RESERVED
    response = issue(staff, pickup["reservation"]["id"], preview["verification_token"])
    assert response.status_code == 200, response.text
    borrowing = response.json()
    assert (
        borrowing["status"] == "BORROWED"
        and borrowing["reservation_id"] == pickup["reservation"]["id"]
    )
    assert (
        issue(staff, pickup["reservation"]["id"], preview["verification_token"]).json()["id"]
        == borrowing["id"]
    )
    assert staff.post(VERIFY, json={"token": pickup["qr"]}).json()["error"]["code"] == "INVALID_QR"
    with Session(domain_db) as db:
        row = db.scalar(
            select(Reservation)
            .options(undefer("*"))
            .where(Reservation.id == pickup["reservation"]["id"])
        )
        assert row.status == ReservationStatus.COMPLETED and row.completed_at
        assert row.qr_token_hash is None and row.qr_token_ciphertext is None
        assert db.get(BookCopy, UUID(pickup["copy"]["id"])).status == CopyStatus.BORROWED
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "BOOK_ISSUED", AuditLog.entity_id == borrowing["id"])
            )
            == 1
        )


def test_proof_requires_verify_and_is_bound_to_session_and_reservation(staff, pickup, actor):
    identity = pickup["reservation"]["id"]
    assert (
        staff.post(BASE + f"/librarian/reservations/{identity}/issue", json={}).status_code == 422
    )
    assert issue(staff, identity, "forged" * 10).status_code == 409
    preview = verify(staff, pickup)
    assert issue(staff, str(uuid4()), preview["verification_token"]).status_code == 409
    actor()
    assert issue(staff, identity, preview["verification_token"]).status_code == 409


@pytest.mark.parametrize("role", [UserRole.READER, UserRole.ADMIN])
def test_only_librarian_can_verify_or_issue(staff, pickup, actor, role):
    proof = verify(staff, pickup)["verification_token"]
    actor(role)
    assert staff.post(VERIFY, json={"token": pickup["qr"]}).status_code == 403
    assert issue(staff, pickup["reservation"]["id"], proof).status_code == 403


@pytest.mark.parametrize("transition", ["cancel", "expire", "block", "inactive", "copy"])
def test_current_state_rechecked_at_verify_and_issue(staff, pickup, domain_db, transition):
    proof = verify(staff, pickup)["verification_token"]
    if transition == "cancel":
        cancel(staff, pickup["reservation"], pickup["reader_token"])
    else:
        with domain_db.begin() as db:
            if transition == "expire":
                db.execute(
                    update(Reservation)
                    .where(Reservation.id == pickup["reservation"]["id"])
                    .values(
                        reserved_at=now() - timedelta(days=4),
                        ready_at=now() - timedelta(days=3),
                        expires_at=now() - timedelta(days=1),
                    )
                )
            elif transition == "copy":
                db.execute(
                    update(BookCopy)
                    .where(BookCopy.id == pickup["copy"]["id"])
                    .values(status=CopyStatus.AVAILABLE)
                )
            else:
                db.execute(
                    update(User)
                    .where(User.id == pickup["reader"]["id"])
                    .values(
                        status=UserStatus.BLOCKED if transition == "block" else UserStatus.INACTIVE
                    )
                )
    assert staff.post(VERIFY, json={"token": pickup["qr"]}).status_code in (403, 404, 409)
    assert issue(staff, pickup["reservation"]["id"], proof).status_code in (403, 409)
    with Session(domain_db) as db:
        assert not db.scalar(
            select(Borrowing.id).where(Borrowing.reservation_id == pickup["reservation"]["id"])
        )
        logs = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "QR_VERIFICATION_FAILED",
                AuditLog.user_id == pickup["librarian"]["id"],
            )
        ).all()
        assert logs and all(pickup["qr"] not in str(log.details) for log in logs)


def test_borrow_limit_overdue_and_live_period_settings(staff, pickup, domain_db):
    preview = verify(staff, pickup)
    other = create_book(staff)
    copy = create_copy(staff, other)
    with Session(domain_db) as db, db.begin():
        existing = Borrowing(
            user_id=pickup["reader"]["id"],
            book_copy_id=copy["id"],
            issued_by=pickup["librarian"]["id"],
            borrowed_at=now() - timedelta(days=3),
            due_at=now() - timedelta(days=1),
            status=BorrowingStatus.BORROWED,
        )
        db.add(existing)
        db.execute(
            update(BookCopy).where(BookCopy.id == copy["id"]).values(status=CopyStatus.BORROWED)
        )
    assert (
        issue(staff, pickup["reservation"]["id"], preview["verification_token"]).json()["error"][
            "code"
        ]
        == "USER_HAS_OVERDUE_BOOKS"
    )
    with domain_db.begin() as db:
        keys = ["block_borrowing_if_overdue", "max_books_per_user", "borrow_period_days"]
        previous = dict(
            db.execute(
                select(SystemSetting.key, SystemSetting.value).where(SystemSetting.key.in_(keys))
            ).all()
        )
        db.execute(
            update(SystemSetting)
            .where(SystemSetting.key == "block_borrowing_if_overdue")
            .values(value=False)
        )
        db.execute(
            update(SystemSetting).where(SystemSetting.key == "max_books_per_user").values(value=1)
        )
        db.execute(
            update(SystemSetting).where(SystemSetting.key == "borrow_period_days").values(value=7)
        )
    try:
        response = issue(staff, pickup["reservation"]["id"], preview["verification_token"])
        assert (
            response.status_code == 409 and response.json()["error"]["code"] == "BOOK_LIMIT_REACHED"
        )
        with Session(domain_db) as db:
            assert (
                db.get(Reservation, UUID(pickup["reservation"]["id"])).status
                == ReservationStatus.READY
            )
            assert db.get(BookCopy, UUID(pickup["copy"]["id"])).status == CopyStatus.RESERVED
        with domain_db.begin() as db:
            db.execute(
                update(SystemSetting)
                .where(SystemSetting.key == "max_books_per_user")
                .values(value=2)
            )
        response = issue(staff, pickup["reservation"]["id"], preview["verification_token"])
        assert response.status_code == 200, response.text
        with Session(domain_db) as db:
            row = db.get(Borrowing, UUID(response.json()["id"]))
            assert row.due_at - row.borrowed_at == timedelta(days=7)
    finally:
        with domain_db.begin() as db:
            for key, value in previous.items():
                db.execute(
                    update(SystemSetting).where(SystemSetting.key == key).values(value=value)
                )


@pytest.mark.parametrize("same_librarian", [True, False])
def test_concurrent_reserved_issue(staff, pickup, actor, domain_db, same_librarian):
    proof_a = verify(staff, pickup)["verification_token"]
    token_b = pickup["staff_token"] if same_librarian else actor()[1]
    proof_b = proof_a if same_librarian else verify(staff, pickup)["verification_token"]
    barrier = Barrier(2)

    def send(args):
        token, proof = args
        barrier.wait(timeout=10)
        return issue(staff, pickup["reservation"]["id"], proof, token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send, [(pickup["staff_token"], proof_a), (token_b, proof_b)]))
    assert sorted(r.status_code for r in responses) == (
        [200, 200] if same_librarian else [200, 409]
    )
    with Session(domain_db) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Borrowing)
                .where(Borrowing.book_copy_id == pickup["copy"]["id"])
            )
            == 1
        )


def test_qr_origin_safe_errors_and_redis_rate_limit(staff, pickup):
    assert (
        staff.post(
            VERIFY, json={"token": pickup["qr"]}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    for _ in range(60):
        response = staff.post(VERIFY, json={"token": "invalid-token-with-sufficient-length"})
        assert response.status_code == 404
        assert response.headers["Cache-Control"] == "no-store"
    response = staff.post(VERIFY, json={"token": pickup["qr"]})
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0


def test_expired_or_modified_receipt_and_access_token_separation(staff, pickup):
    proof = verify(staff, pickup)["verification_token"]
    settings = staff.app.state.settings
    claims = jwt.decode(proof, proof_key(settings), algorithms=["HS256"], audience=AUDIENCE)
    claims["exp"] = now() - timedelta(seconds=1)
    expired = jwt.encode(claims, proof_key(settings), algorithm="HS256")
    assert issue(staff, pickup["reservation"]["id"], expired).status_code == 409
    assert issue(staff, pickup["reservation"]["id"], proof[:-8] + "tampered").status_code == 409
    assert (
        staff.get(BASE + "/auth/me", headers={"Authorization": "Bearer " + proof}).status_code
        == 401
    )


def test_cross_book_issues_share_reader_limit_lock(staff, pickup, actor, domain_db):
    proof_a = verify(staff, pickup)["verification_token"]
    second_book = create_book(staff)
    create_copy(staff, second_book)
    second_reservation = reserve(staff, second_book, pickup["reader_token"])
    qr = staff.get(
        PATH + f"/{second_reservation['id']}/qr",
        headers={"Authorization": "Bearer " + pickup["reader_token"]},
    ).json()["token"]
    token_b = actor()[1]
    proof_b = verify(staff, {"qr": qr})["verification_token"]
    with domain_db.begin() as db:
        previous = db.scalar(
            select(SystemSetting.value).where(SystemSetting.key == "max_books_per_user")
        )
        db.execute(
            update(SystemSetting).where(SystemSetting.key == "max_books_per_user").values(value=1)
        )
    try:
        barrier = Barrier(2)

        def send(args):
            reservation_id, proof, token = args
            barrier.wait(timeout=10)
            return issue(staff, reservation_id, proof, token)

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(
                pool.map(
                    send,
                    [
                        (pickup["reservation"]["id"], proof_a, pickup["staff_token"]),
                        (second_reservation["id"], proof_b, token_b),
                    ],
                )
            )
        assert sorted(r.status_code for r in responses) == [200, 409]
        failed = next(r for r in responses if r.status_code == 409)
        assert failed.json()["error"]["code"] == "BOOK_LIMIT_REACHED"
        with Session(domain_db) as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(Borrowing)
                    .where(Borrowing.user_id == pickup["reader"]["id"])
                )
                == 1
            )
    finally:
        with domain_db.begin() as db:
            db.execute(
                update(SystemSetting)
                .where(SystemSetting.key == "max_books_per_user")
                .values(value=previous)
            )
