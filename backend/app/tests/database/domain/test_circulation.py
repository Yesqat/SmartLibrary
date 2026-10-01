"""Physical circulation and real PostgreSQL resource races; no business-service mocks."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.security import now
from app.db.enums import BorrowingStatus, CopyStatus, ReservationStatus, UserRole, UserStatus
from app.db.models import AuditLog, BookCopy, Borrowing, Reservation, User
from app.tests.database.domain.support import PrivateContext
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy
from app.tests.database.domain.test_reservations import PATH, cancel, reserve

pytestmark = pytest.mark.integration
LOANS = BASE + "/librarian/borrowings"


@pytest.fixture
def circulation(staff, actor):
    librarian, staff_token = actor()
    book = create_book(staff)
    copy = create_copy(staff, book)
    reader, reader_token = actor(UserRole.READER)
    staff.headers["Authorization"] = "Bearer " + staff_token
    return PrivateContext(
        {
            "book": book,
            "copy": copy,
            "reader": reader,
            "reader_token": reader_token,
            "staff_token": staff_token,
            "librarian": librarian,
        }
    )


def direct(client, fixture, key=None, token=None):
    return client.post(
        LOANS,
        json={
            "user_id": fixture["reader"]["id"],
            "book_copy_id": fixture["copy"]["id"],
            "idempotency_key": str(key or uuid4()),
        },
        headers={"Authorization": "Bearer " + token} if token else {},
    )


def returned(client, loan, condition="GOOD", token=None):
    return client.post(
        LOANS + f"/{loan['id']}/return",
        json={"condition": condition},
        headers={"Authorization": "Bearer " + token} if token else {},
    )


def test_direct_issue_lookup_return_and_repeat_cannot_change_later_loan(
    staff, circulation, domain_db
):
    key = uuid4()
    first = direct(staff, circulation, key)
    assert first.status_code == 200, first.text
    loan = first.json()
    assert loan["reservation_id"] is None and loan["status"] == "BORROWED"
    assert direct(staff, circulation, key).json()["id"] == loan["id"]
    lookup = staff.get(LOANS + f"/by-inventory/{circulation['copy']['inventory_number']}")
    assert lookup.status_code == 200
    assert lookup.json()["active_borrowing"]["id"] == loan["id"]
    assert lookup.json()["physical_copy"]["status"] == "BORROWED"
    result = returned(staff, loan)
    assert result.status_code == 200 and result.json()["status"] == "RETURNED"
    second = direct(staff, circulation).json()
    assert second["id"] != loan["id"]
    assert returned(staff, loan).json()["id"] == loan["id"]
    assert direct(staff, circulation, key).json()["status"] == "RETURNED"
    with Session(domain_db) as db:
        assert db.get(BookCopy, UUID(circulation["copy"]["id"])).status == CopyStatus.BORROWED
        assert db.get(Borrowing, UUID(second["id"])).status == BorrowingStatus.BORROWED
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "BOOK_RETURNED", AuditLog.entity_id == loan["id"])
            )
            == 1
        )


def test_idempotency_key_reuse_requires_same_payload(staff, circulation, actor):
    key = uuid4()
    assert direct(staff, circulation, key).status_code == 200
    other, _ = actor(UserRole.READER)
    changed = {**circulation, "reader": other}
    response = direct(staff, changed, key, circulation["staff_token"])
    assert (
        response.status_code == 409 and response.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    )


def test_return_assigns_same_copy_to_first_waiter(staff, circulation, actor, domain_db):
    loan = direct(staff, circulation).json()
    actor(UserRole.READER)
    first = reserve(staff, circulation["book"])
    actor(UserRole.READER)
    second = reserve(staff, circulation["book"])
    result = returned(staff, loan, token=circulation["staff_token"])
    assert result.status_code == 200, result.text
    with Session(domain_db) as db:
        assert db.get(BookCopy, UUID(circulation["copy"]["id"])).status == CopyStatus.RESERVED
        ready = db.get(Reservation, UUID(first["id"]))
        assert ready.status == ReservationStatus.READY and ready.book_copy_id == UUID(
            circulation["copy"]["id"]
        )
        assert db.get(Reservation, UUID(second["id"])).status == ReservationStatus.WAITING


def test_damaged_return_never_enters_queue_or_availability(staff, circulation, actor, domain_db):
    loan = direct(staff, circulation).json()
    actor(UserRole.READER)
    waiter = reserve(staff, circulation["book"])
    result = returned(staff, loan, "DAMAGED", circulation["staff_token"])
    assert result.status_code == 200 and result.json()["status"] == "RETURNED"
    with Session(domain_db) as db:
        copy = db.get(BookCopy, UUID(circulation["copy"]["id"]))
        assert copy.status == CopyStatus.DAMAGED and copy.condition.value == "DAMAGED"
        assert db.get(Reservation, UUID(waiter["id"])).status == ReservationStatus.WAITING
    assert (
        direct(staff, circulation, token=circulation["staff_token"]).json()["error"]["code"]
        == "COPY_DAMAGED"
    )


def test_lost_is_terminal_unavailable_and_idempotent(staff, circulation, domain_db):
    loan = direct(staff, circulation).json()
    for _ in range(2):
        response = staff.post(LOANS + f"/{loan['id']}/lost")
        assert response.status_code == 200 and response.json()["status"] == "LOST"
    assert returned(staff, loan).status_code == 409
    assert direct(staff, circulation).json()["error"]["code"] == "COPY_LOST"
    with Session(domain_db) as db:
        assert db.get(Borrowing, UUID(loan["id"])).lost_at
        assert db.get(BookCopy, UUID(circulation["copy"]["id"])).status == CopyStatus.LOST
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "BOOK_LOST", AuditLog.entity_id == loan["id"])
            )
            == 1
        )


@pytest.mark.parametrize("role", [UserRole.READER, UserRole.ADMIN])
def test_staff_only_physical_operations_and_reader_ownership(staff, circulation, actor, role):
    loan = direct(staff, circulation).json()
    actor(role)
    assert returned(staff, loan).status_code == 403
    assert direct(staff, circulation).status_code == 403
    assert staff.post(LOANS + f"/{loan['id']}/lost").status_code == 403
    assert (
        staff.get(LOANS + f"/by-inventory/{circulation['copy']['inventory_number']}").status_code
        == 403
    )
    if role == UserRole.READER:
        assert staff.get(BASE + "/borrowings/me/active").json()["total"] == 0
        assert (
            staff.get(BASE + "/borrowings/me/active?user_id=" + circulation["reader"]["id"]).json()[
                "total"
            ]
            == 0
        )
    response = staff.get(
        BASE + "/borrowings/me/active",
        headers={"Authorization": "Bearer " + circulation["reader_token"]},
    )
    assert response.json()["items"][0]["id"] == loan["id"]


def test_due_date_overdue_and_reader_history(staff, circulation, domain_db):
    loan = direct(staff, circulation).json()
    with domain_db.begin() as db:
        db.execute(
            update(Borrowing)
            .where(Borrowing.id == loan["id"])
            .values(borrowed_at=now() - timedelta(days=3), due_at=now() - timedelta(days=1))
        )
    overdue = staff.get(LOANS + "/overdue").json()
    row = next(r for r in overdue["items"] if r["id"] == loan["id"])
    assert row["status"] == "BORROWED" and row["is_overdue"]
    assert returned(staff, loan).status_code == 200
    history = staff.get(
        BASE + "/borrowings/me/history",
        headers={"Authorization": "Bearer " + circulation["reader_token"]},
    ).json()
    assert history["items"][0]["id"] == loan["id"] and not history["items"][0]["is_overdue"]
    assert staff.post(LOANS + f"/{loan['id']}/lost").status_code == 409


@pytest.mark.parametrize("status", [UserStatus.BLOCKED, UserStatus.INACTIVE])
def test_unavailable_reader_cannot_borrow_but_can_physically_return(
    staff, circulation, domain_db, status
):
    loan = direct(staff, circulation).json()
    with domain_db.begin() as db:
        db.execute(update(User).where(User.id == circulation["reader"]["id"]).values(status=status))
    assert returned(staff, loan).status_code == 200
    assert direct(staff, circulation).status_code == 403


@pytest.mark.parametrize("status", ["DAMAGED", "LOST", "MAINTENANCE"])
def test_unavailable_copy_states_cannot_issue(staff, circulation, status):
    condition = "DAMAGED" if status == "DAMAGED" else "GOOD"
    copy = create_copy(staff, circulation["book"], condition=condition)
    if status != "DAMAGED":
        response = staff.patch(BASE + f"/copies/{copy['id']}", json={"status": status})
        assert response.status_code == 200, response.text
    assert direct(staff, {**circulation, "copy": copy}).status_code == 409


def test_direct_issue_cannot_bypass_eligible_waiter(staff, circulation, actor, domain_db):
    # Models a just-restored eligibility/legacy queue awaiting scheduled reconciliation.
    reader, _ = actor(UserRole.READER)
    with Session(domain_db) as db, db.begin():
        db.add(
            Reservation(
                book_id=circulation["book"]["id"],
                user_id=reader["id"],
                status=ReservationStatus.WAITING,
            )
        )
    response = direct(staff, circulation, token=circulation["staff_token"])
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "RESERVATION_QUEUE_CONFLICT"
    )


@pytest.mark.parametrize("same_request", [False, True])
def test_concurrent_direct_issue(staff, circulation, actor, domain_db, same_request):
    token_b = circulation["staff_token"] if same_request else actor()[1]
    key_a = uuid4()
    key_b = key_a if same_request else uuid4()
    barrier = Barrier(2)

    def send(args):
        key, token = args
        barrier.wait(timeout=10)
        return direct(staff, circulation, key, token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send, [(key_a, circulation["staff_token"]), (key_b, token_b)]))
    assert sorted(r.status_code for r in results) == ([200, 200] if same_request else [200, 409])
    with Session(domain_db) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Borrowing)
                .where(Borrowing.book_copy_id == circulation["copy"]["id"])
            )
            == 1
        )


def test_concurrent_reservation_vs_direct_issue(staff, circulation, actor, domain_db):
    _, reserve_token = actor(UserRole.READER)
    barrier = Barrier(2)

    def reserving():
        barrier.wait(timeout=10)
        return staff.post(
            PATH,
            json={"book_id": circulation["book"]["id"]},
            headers={"Authorization": "Bearer " + reserve_token},
        )

    def issuing():
        barrier.wait(timeout=10)
        return direct(staff, circulation, token=circulation["staff_token"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(reserving), pool.submit(issuing)]
        reservation, issue_result = [f.result(timeout=15) for f in futures]
    assert reservation.status_code == 201
    assert issue_result.status_code in (200, 409)
    with Session(domain_db) as db:
        copy = db.get(BookCopy, UUID(circulation["copy"]["id"]))
        if issue_result.status_code == 200:
            assert copy.status == CopyStatus.BORROWED and reservation.json()["status"] == "WAITING"
        else:
            assert copy.status == CopyStatus.RESERVED and reservation.json()["status"] == "READY"


def test_concurrent_return_and_ready_cancel_preserve_fifo(staff, circulation, actor, domain_db):
    loan = direct(staff, circulation).json()
    create_copy(staff, circulation["book"])
    _, cancelling_token = actor(UserRole.READER)
    cancelling = reserve(staff, circulation["book"])
    actor(UserRole.READER)
    first = reserve(staff, circulation["book"])
    actor(UserRole.READER)
    second = reserve(staff, circulation["book"])
    barrier = Barrier(2)

    def returning():
        barrier.wait(timeout=10)
        return returned(staff, loan, token=circulation["staff_token"])

    def cancelling_ready():
        barrier.wait(timeout=10)
        return cancel(staff, cancelling, cancelling_token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(returning), pool.submit(cancelling_ready)
        assert a.result(timeout=15).status_code == 200
        assert b.result(timeout=15)["status"] == "CANCELLED"
    with Session(domain_db) as db:
        first_row, second_row = (
            db.get(Reservation, UUID(first["id"])),
            db.get(Reservation, UUID(second["id"])),
        )
        assert first_row.status == second_row.status == ReservationStatus.READY
        assert first_row.book_copy_id != second_row.book_copy_id
        assert first_row.ready_at <= second_row.ready_at


def test_readers_inventory_errors_and_input_validation(staff, circulation):
    assert staff.get(LOANS + "/by-inventory/missing").status_code == 404
    assert (
        staff.get(BASE + "/librarian/readers", params={"q": circulation["reader"]["email"]}).json()[
            "total"
        ]
        == 1
    )
    assert staff.get(BASE + "/librarian/readers?page_size=101").status_code == 422
    assert (
        staff.post(
            LOANS,
            json={
                "user_id": circulation["reader"]["id"],
                "book_copy_id": circulation["copy"]["id"],
            },
        ).status_code
        == 422
    )
    loan = direct(staff, circulation).json()
    assert returned(staff, loan, "LOST").status_code == 422
    assert (
        staff.post(
            LOANS + f"/{loan['id']}/return",
            json={"condition": "GOOD", "returned_at": now().isoformat()},
        ).status_code
        == 422
    )
