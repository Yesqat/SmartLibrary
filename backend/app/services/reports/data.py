from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Book, BookCopy, Borrowing, Reservation, User
from app.schemas.reports import ReportInput
from app.services.analytics.catalog import inventory
from app.services.analytics.circulation import circulation
from app.services.analytics.definitions import Period, overdue_borrowing

type Value = str | int | float | date | datetime | None
MAX_ROWS = 5000
TITLES = {
    "inventory": "Кітапхана қоры",
    "borrowings": "Кітап беру есебі",
    "overdue": "Мерзімі өткен қарыздар",
    "reservations": "Броньдар есебі",
}
STATES = {
    "AVAILABLE": "Қолжетімді",
    "RESERVED": "Брондалған",
    "BORROWED": "Берілген",
    "OVERDUE": "Мерзімі өткен",
    "RETURNED": "Қайтарылған",
    "LOST": "Жоғалған",
    "DAMAGED": "Зақымдалған",
    "MAINTENANCE": "Жөндеуде",
    "GOOD": "Жақсы",
    "NEW": "Жаңа",
    "WORN": "Тозған",
    "WAITING": "Кезекте",
    "READY": "Алуға дайын",
    "COMPLETED": "Орындалған",
    "CANCELLED": "Жойылған",
    "EXPIRED": "Мерзімі өткен",
}


@dataclass(frozen=True)
class ReportData:
    kind: str
    window: Period
    generated_by: str
    note: str
    headers: list[str]
    widths: list[int]
    rows: list[list[Value]]
    summary: list[tuple[str, Value]]


def collect(db: Session, data: ReportInput, window: Period, generated_by: str) -> ReportData:
    query: Select[Any]
    if data.report_type == "inventory":
        query = (
            select(
                Book.title,
                BookCopy.inventory_number,
                BookCopy.shelf_location,
                BookCopy.status,
                BookCopy.condition,
                BookCopy.acquired_at,
                BookCopy.created_at,
            )
            .join(Book)
            .where(
                Book.archived_at.is_(None),
                BookCopy.archived_at.is_(None),
                window.contains(BookCopy.created_at),
            )
            .order_by(Book.title, BookCopy.inventory_number)
        )
        headers = [
            "Кітап",
            "Түгендеу №",
            "Сөре",
            "Күйі",
            "Жағдайы",
            "Алынған күні",
            "Қосылған уақыты",
        ]
        widths = [25, 15, 12, 12, 10, 12, 14]
        metrics = inventory(db, window)
        summary: list[tuple[str, Value]] = [
            ("Қазіргі кітап атаулары", metrics.book_titles),
            ("Қазіргі физикалық даналар", metrics.physical_copies),
            ("Кезеңде қосылған даналар (архивті қоса)", metrics.added_copies),
        ]
        note = (
            "Кесте: кезеңде қосылған, қазір архивте емес даналар. Күйі - есеп жасалған сәттегі күй."
        )
    elif data.report_type in {"borrowings", "overdue"}:
        query = (
            select(
                Book.title,
                BookCopy.inventory_number,
                User.first_name + " " + User.last_name,
                Borrowing.borrowed_at,
                Borrowing.due_at,
                Borrowing.returned_at,
                Borrowing.lost_at,
                Borrowing.status,
            )
            .select_from(Borrowing)
            .join(BookCopy)
            .join(Book)
            .join(User, User.id == Borrowing.user_id)
        )
        if data.report_type == "overdue":
            query = query.where(
                overdue_borrowing(window.meta.generated_at), window.contains(Borrowing.due_at)
            )
            note = (
                "Кесте: мерзімі таңдалған кезеңде аяқталған, "
                "қазір қайтарылмаған/жоғалмаған қарыздар."
            )
        else:
            query = query.where(window.contains(Borrowing.borrowed_at))
            note = "Кесте: таңдалған кезеңде берілген қарыздар; күйі есеп жасалған сәтке сәйкес."
        query = query.order_by(Borrowing.due_at, Borrowing.id)
        headers = [
            "Кітап",
            "Түгендеу №",
            "Оқырман",
            "Берілді",
            "Қайтару мерзімі",
            "Қайтарылды",
            "Жоғалды",
            "Күйі",
        ]
        widths = [21, 12, 16, 11, 11, 10, 9, 10]
        loans = circulation(db, window)
        summary = [
            ("Қазіргі белсенді қарыздар", loans.active_borrowings),
            ("Қазіргі мерзімі өткен қарыздар", loans.overdue_borrowings),
            ("Кезеңде берілді", loans.issued),
            ("Кезеңде қайтарылды", loans.returned),
            ("Кезеңде жоғалды", loans.lost),
        ]
    else:
        query = (
            select(
                Reservation.reservation_number,
                Book.title,
                User.first_name + " " + User.last_name,
                BookCopy.inventory_number,
                Reservation.reserved_at,
                Reservation.expires_at,
                Reservation.status,
            )
            .select_from(Reservation)
            .join(Book, Book.id == Reservation.book_id)
            .join(User, User.id == Reservation.user_id)
            .outerjoin(BookCopy, BookCopy.id == Reservation.book_copy_id)
            .where(window.contains(Reservation.reserved_at))
            .order_by(Reservation.reserved_at, Reservation.id)
        )
        headers = ["Бронь №", "Кітап", "Оқырман", "Дана №", "Жасалды", "Сақтау мерзімі", "Күйі"]
        widths = [10, 25, 18, 12, 12, 12, 11]
        loans = circulation(db, window)
        summary = [
            ("Кезеңде жасалды", loans.reservations_created),
            ("Кезеңде орындалды", loans.reservations_completed),
            ("Кезеңде жойылды", loans.reservations_cancelled),
            ("Кезеңде мерзімі өтті", loans.reservations_expired),
            ("Орындалу үлесі (%)", loans.reservation_completion_rate),
        ]
        note = (
            "Кесте: кезеңде жасалған броньдар. Қорытындыдағы аяқталу оқиғалары "
            "өз уақытымен саналады. QR құпиялары кірмейді."
        )
    rows = [list(row) for row in db.execute(query.limit(MAX_ROWS + 1))]
    if len(rows) > MAX_ROWS:
        raise AppError("REPORT_TOO_LARGE", "Есеп тым үлкен. Күндер аралығын қысқартыңыз.", 422)
    for row in rows:
        if (
            data.report_type in {"borrowings", "overdue"}
            and row[-1] in {"BORROWED", "OVERDUE"}
            and row[4] < window.meta.generated_at
        ):
            row[-1] = "Мерзімі өткен"
        for index, value in enumerate(row):
            if isinstance(value, Enum):
                row[index] = STATES.get(value.value, value.value)
    return ReportData(
        data.report_type,
        window,
        generated_by,
        note,
        headers,
        widths,
        rows,
        [("Кестедегі жазбалар", len(rows)), *summary],
    )
