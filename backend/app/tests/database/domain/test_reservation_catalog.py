from uuid import UUID

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.security import now
from app.db.enums import CopyStatus, ReservationStatus, UserRole
from app.db.models import Book, BookCopy, Reservation
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy
from app.tests.database.domain.test_reservations import cancel, reserve

pytestmark = pytest.mark.integration


def test_new_copy_immediately_serves_existing_fifo(staff, actor, domain_db):
    librarian_token = actor()[1]
    book = create_book(staff)
    actor(UserRole.READER)
    first = reserve(staff, book)
    actor(UserRole.READER)
    second = reserve(staff, book)
    staff.headers["Authorization"] = "Bearer " + librarian_token
    copy = create_copy(staff, book)
    assert copy["status"] == "RESERVED"
    with Session(domain_db) as db:
        assert db.get(Reservation, UUID(first["id"])).book_copy_id == UUID(copy["id"])
        assert db.get(Reservation, UUID(second["id"])).status == ReservationStatus.WAITING


def test_unavailable_inventory_and_archived_title_cannot_be_allocated(staff, actor, domain_db):
    book = create_book(staff)
    create_copy(staff, book, condition="DAMAGED")
    maintained = create_copy(staff, book)
    archived = create_copy(staff, book)
    with domain_db.begin() as db:
        db.execute(
            update(BookCopy)
            .where(BookCopy.id == maintained["id"])
            .values(status=CopyStatus.MAINTENANCE)
        )
        db.execute(update(BookCopy).where(BookCopy.id == archived["id"]).values(archived_at=now()))
    actor(UserRole.READER)
    row = reserve(staff, book)
    assert row["status"] == "WAITING"
    cancel(staff, row)
    with domain_db.begin() as db:
        db.execute(update(Book).where(Book.id == book["id"]).values(archived_at=now()))
    # Terminal cancellation stays idempotent even after later title archival.
    assert cancel(staff, row)["status"] == "CANCELLED"
    reserve(staff, book, expected=404)


def test_repair_makes_copy_ready_for_waiter(staff, actor, domain_db):
    librarian_token = actor()[1]
    book = create_book(staff)
    copy = create_copy(staff, book, condition="DAMAGED")
    staff.patch(BASE + f"/copies/{copy['id']}", json={"status": "MAINTENANCE"})
    actor(UserRole.READER)
    row = reserve(staff, book)
    staff.headers["Authorization"] = "Bearer " + librarian_token
    response = staff.patch(
        BASE + f"/copies/{copy['id']}", json={"status": "AVAILABLE", "condition": "GOOD"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "RESERVED"
    with Session(domain_db) as db:
        assert (
            db.scalar(select(Reservation.status).where(Reservation.id == row["id"]))
            == ReservationStatus.READY
        )
