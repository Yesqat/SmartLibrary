"""Transactional, repeat-safe development fixture; refuses production and preserves edits."""

import hashlib
import os
import secrets
from contextlib import ExitStack
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid5

from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from sqlalchemy import insert, select, text

from app.db.manage import engine, env
from app.db.models import (
    AuditLog,
    Author,
    Book,
    BookAuthor,
    BookCategory,
    BookCopy,
    Borrowing,
    Category,
    Favorite,
    Notification,
    Publisher,
    Reservation,
    SearchEvent,
    User,
    UserCategoryPreference,
    UserInteraction,
)
from app.db.seed_data import BOOKS, CATEGORIES

NAMESPACE = UUID("0484934a-0aee-43b7-9a6e-6b408bf7d365")


def seed_id(name: str) -> UUID:
    return uuid5(NAMESPACE, name)


def seed_development(database: str | None = None) -> None:
    if os.environ.get("APP_ENV") not in {"development", "test"}:
        raise ValueError("Development seed is disabled outside development/test")
    password = env("DEV_SEED_PASSWORD")
    if len(password) < 16:
        raise ValueError("DEV_SEED_PASSWORD must have at least 16 characters")
    key = env("QR_ENCRYPTION_KEY")
    cipher = Fernet((key + "=" * (-len(key) % 4)).encode())
    db = engine("migration", database)
    now = datetime.now(UTC)
    marker = seed_id("seed-v1-complete")
    with ExitStack() as stack:
        stack.callback(db.dispose)
        connection = stack.enter_context(db.begin())
        connection.execute(text("SELECT pg_advisory_xact_lock(8729102461)"))
        if connection.scalar(select(AuditLog.id).where(AuditLog.id == marker)):
            print("Development seed v1 already applied; existing data and passwords preserved.")
            return
        accounts = [
            ("admin", "Әкімші", "Кітапхана", "ADMIN"),
            ("librarian", "Айдана", "Серік", "LIBRARIAN"),
            ("reader1", "Аян", "Омар", "READER"),
            ("reader2", "Мария", "Иванова", "READER"),
            ("reader3", "Дана", "Әлі", "READER"),
            ("reader4", "Alex", "Morgan", "READER"),
        ]
        hasher = PasswordHasher()
        for name, first, last, role in accounts:
            connection.execute(
                insert(User).values(
                    id=seed_id(name),
                    first_name=first,
                    last_name=last,
                    email=f"{name}@smartlibrary.example",
                    password_hash=hasher.hash(password),
                    role=role,
                    status="ACTIVE",
                    created_at=now - timedelta(days=45),
                )
            )
        for name, description in CATEGORIES.items():
            connection.execute(
                insert(Category).values(id=seed_id(name), name=name, description=description)
            )
        for language, publisher in (
            ("kk", "Атамұра"),
            ("ru", "АСТ"),
        ):
            connection.execute(
                insert(Publisher).values(id=seed_id("publisher-" + language), name=publisher)
            )
        for i, (title, author, language, year, categories, description) in enumerate(BOOKS):
            connection.execute(
                insert(Author).values(id=seed_id("author-" + str(i)), full_name=author)
            )
            connection.execute(
                insert(Book).values(
                    id=seed_id("book-" + str(i)),
                    title=title,
                    description=description,
                    language=language,
                    publication_year=year,
                    publisher_id=seed_id("publisher-" + language) if language != "en" else None,
                    created_at=now - timedelta(days=40 - i),
                )
            )
            connection.execute(
                insert(BookAuthor).values(
                    book_id=seed_id("book-" + str(i)), author_id=seed_id("author-" + str(i))
                )
            )
            for category in categories:
                connection.execute(
                    insert(BookCategory).values(
                        book_id=seed_id("book-" + str(i)), category_id=seed_id(category)
                    )
                )
            for copy in range(2):
                state = {
                    (0, 0): "RESERVED",
                    (1, 0): "BORROWED",
                    (1, 1): "BORROWED",
                    (3, 0): "LOST",
                    (6, 0): "DAMAGED",
                    (7, 0): "MAINTENANCE",
                }.get((i, copy), "AVAILABLE")
                connection.execute(
                    insert(BookCopy).values(
                        id=seed_id(f"copy-{i}-{copy}"),
                        book_id=seed_id("book-" + str(i)),
                        inventory_number=f"DEV-{i + 1:03}-{copy + 1:02}",
                        shelf_location=f"{language.upper()}-{i // 3 + 1}",
                        acquired_at=date(2025, 9, 1),
                        status=state,
                        condition="DAMAGED" if state == "DAMAGED" else "GOOD",
                    )
                )
        token = secrets.token_urlsafe(32)
        connection.execute(
            insert(Reservation).values(
                id=seed_id("ready"),
                reservation_number="DEV-R-READY",
                user_id=seed_id("reader1"),
                book_id=seed_id("book-0"),
                book_copy_id=seed_id("copy-0-0"),
                status="READY",
                reserved_at=now - timedelta(hours=1),
                ready_at=now - timedelta(hours=1),
                expires_at=now + timedelta(hours=47),
                qr_token_hash=hashlib.sha256(token.encode()).hexdigest(),
                qr_token_ciphertext=cipher.encrypt(token.encode()).decode(),
                qr_key_id="development-v1",
            )
        )
        for index, reader in enumerate(("reader3", "reader4")):
            connection.execute(
                insert(Reservation).values(
                    id=seed_id("waiting-" + reader),
                    reservation_number="DEV-R-WAIT-" + str(index + 1),
                    user_id=seed_id(reader),
                    book_id=seed_id("book-1"),
                    status="WAITING",
                    reserved_at=now - timedelta(hours=4 - index),
                )
            )
        for name, status in (
            ("cancelled", "CANCELLED"),
            ("expired", "EXPIRED"),
            ("completed", "COMPLETED"),
        ):
            connection.execute(
                insert(Reservation).values(
                    id=seed_id(name),
                    reservation_number="DEV-R-" + status,
                    user_id=seed_id("reader2"),
                    book_id=seed_id("book-2"),
                    book_copy_id=None if status == "CANCELLED" else seed_id("copy-2-0"),
                    status=status,
                    reserved_at=now - timedelta(days=30),
                    ready_at=None if status == "CANCELLED" else now - timedelta(days=29),
                    expires_at=None if status == "CANCELLED" else now - timedelta(days=27),
                    completed_at=now - timedelta(days=28) if status == "COMPLETED" else None,
                    cancelled_at=now - timedelta(days=29) if status == "CANCELLED" else None,
                )
            )
        loans = [
            ("active", "reader1", "copy-1-0", "BORROWED", 3, 11, None),
            ("overdue", "reader2", "copy-1-1", "OVERDUE", 20, -6, None),
            ("returned", "reader2", "copy-2-0", "RETURNED", 28, -14, "completed"),
            ("lost", "reader3", "copy-3-0", "LOST", 25, -11, None),
            ("damaged-return", "reader4", "copy-6-0", "RETURNED", 15, -1, None),
        ]
        for name, reader, loan_copy, status, ago, due, reservation in loans:
            connection.execute(
                insert(Borrowing).values(
                    id=seed_id(name + "-loan"),
                    user_id=seed_id(reader),
                    book_copy_id=seed_id(loan_copy),
                    reservation_id=seed_id(reservation) if reservation else None,
                    issued_by=seed_id("librarian"),
                    borrowed_at=now - timedelta(days=ago),
                    due_at=now + timedelta(days=due),
                    status=status,
                    returned_at=now - timedelta(days=1) if status == "RETURNED" else None,
                    returned_by=seed_id("librarian") if status == "RETURNED" else None,
                    lost_at=now - timedelta(days=2) if status == "LOST" else None,
                )
            )
            connection.execute(
                insert(AuditLog).values(
                    user_id=seed_id("librarian"),
                    action="ISSUE_BOOK",
                    entity_type="borrowing",
                    entity_id=seed_id(name + "-loan"),
                    details={"development_fixture": True},
                    created_at=now - timedelta(days=ago),
                )
            )
        for reader_index in range(1, 5):
            for book_index in (reader_index, reader_index + 4):
                book_id = seed_id("book-" + str(book_index))
                user_id = seed_id("reader" + str(reader_index))
                connection.execute(insert(Favorite).values(user_id=user_id, book_id=book_id))
                for event in ("VIEW", "FAVORITE"):
                    connection.execute(
                        insert(UserInteraction).values(
                            user_id=user_id,
                            book_id=book_id,
                            interaction_type=event,
                            source="CATALOG",
                            created_at=now - timedelta(days=reader_index),
                            event_key=f"dev-{reader_index}-{book_index}-{event}",
                        )
                    )
            connection.execute(
                insert(UserCategoryPreference).values(
                    user_id=seed_id("reader" + str(reader_index)),
                    category_id=seed_id("Programming"),
                    weight=1,
                )
            )
        for query, result_count in (("Python", 2), ("Абай", 2), ("marine robotics", 0)):
            connection.execute(
                insert(SearchEvent).values(
                    query=query, result_count=result_count, search_type="STANDARD", filters={}
                )
            )
        connection.execute(
            insert(Notification).values(
                user_id=seed_id("reader1"),
                type="RESERVATION_READY",
                title="Бронь дайын",
                message="Даму ортасындағы Абай жолы данасы алуға дайын.",
                related_entity_type="RESERVATION",
                reservation_id=seed_id("ready"),
                event_key="dev-reservation-ready",
            )
        )
        connection.execute(
            insert(Notification).values(
                user_id=seed_id("reader2"),
                type="OVERDUE",
                title="Қайтару мерзімі өтті",
                message="Даму ортасындағы Clean Code данасын қайтару мерзімі өтті.",
                related_entity_type="BORROWING",
                borrowing_id=seed_id("overdue-loan"),
                event_key="dev-overdue",
            )
        )
        connection.execute(
            insert(AuditLog).values(
                id=marker, action="DEVELOPMENT_SEED", entity_type="dataset", details={"version": 1}
            )
        )
    print(
        "Seeded 6 accounts, 12 titles, 24 copies and circulation/engagement fixtures. "
        "Passwords come from DEV_SEED_PASSWORD; no credentials printed. "
        "No synthetic AI output seeded."
    )
