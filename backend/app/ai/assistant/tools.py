"""A closed dispatch table; each call revalidates the authenticated Reader."""

from dataclasses import asdict
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.ai.assistant.contracts import unavailable
from app.ai.recommendations.service import personalized, similar
from app.api.dependencies import Principal
from app.core.config import Settings
from app.core.errors import AppError
from app.core.permissions import Permission, authorize
from app.repositories.borrowings import borrowing_page
from app.repositories.catalog import get_book
from app.repositories.reservations import owned_page
from app.schemas.catalog import BookRead
from app.schemas.search import SearchParams
from app.services.audit.events import AuditContext
from app.services.auth.service import AuthService
from app.services.search.service import search
from app.services.settings.policy import circulation_policy


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchInput(Empty):
    q: str = Field(min_length=1, max_length=500)
    available: bool | None
    language: str | None = Field(pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", max_length=35)


class BookInput(Empty):
    book_id: str = Field(pattern=r"^[0-9a-fA-F-]{36}$")


class PersonalInput(Empty):
    page: int = Field(ge=1, le=100)


TOOLS: dict[str, tuple[type[BaseModel], str]] = {
    "search_books": (
        SearchInput,
        "Search real catalog title/ISBN/author/category/description. Up to 8 books.",
    ),
    "semantic_search_books": (
        SearchInput,
        "Multilingual semantic catalog discovery. Up to 8 books.",
    ),
    "get_book_details": (
        BookInput,
        "Read an actual book and its current physical-copy availability.",
    ),
    "check_book_availability": (
        BookInput,
        "Current physical-copy availability, never historical context.",
    ),
    "get_similar_books": (BookInput, "Find up to 8 books using actual catalog vectors."),
    "get_recommendations": (
        Empty,
        "Recommendations for authenticated Reader, including cold start.",
    ),
    "get_my_borrowings": (
        PersonalInput,
        "Only authenticated Reader's active loans and due dates, 10/page.",
    ),
    "get_my_reservations": (
        PersonalInput,
        "Only authenticated Reader's active reservations, 10/page. No QR secrets.",
    ),
    "get_library_rules": (Empty, "Read current configured borrowing/reservation rules."),
}


def definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": name,
            "description": description,
            "parameters": schema.model_json_schema(),
            "strict": True,
        }
        for name, (schema, description) in TOOLS.items()
    ]


class ToolContext:
    def __init__(
        self, engine: Engine, settings: Settings, principal: Principal, context: AuditContext
    ):
        self.engine, self.settings, self.principal = engine, settings, principal
        self.auth = AuthService(engine, settings, context)
        self.books: dict[str, BookRead] = {}
        self.evidence: dict[str, str] = {}
        self.trace: list[dict[str, str]] = []

    def execute(self, name: str, arguments: str) -> dict[str, Any]:
        # Unknown capabilities and extra identity/SQL/action arguments fail before dispatch.
        if name not in TOOLS or len(arguments) > 4096 or len(self.trace) >= 6:
            raise unavailable()
        try:
            data = TOOLS[name][0].model_validate_json(arguments)
        except ValidationError:
            raise unavailable() from None
        ref = f"result{len(self.trace) + 1}"
        self.trace.append({"name": name, "status": "ok"})
        try:
            with Session(self.engine) as db, db.begin():
                user = self.auth.require_live(db, self.principal.user.id, self.principal.family_id)
                authorize(user.role, Permission.READ_PERSONAL)
                return self.run(db, name, data, ref)
        except AppError as error:
            if error.status in (401, 403):
                raise
            self.trace[-1]["status"] = "unavailable"
            self.evidence[ref] = "Сұралған деректер қазір қолжетімсіз. Кейінірек қайталаңыз."
            return {"evidence_ref": ref, "error": "DATA_UNAVAILABLE"}

    def book_result(self, books: list[BookRead], ref: str, summary: str) -> dict[str, Any]:
        items = []
        for index, book in enumerate(books):
            key = f"{ref}_book{index + 1}"
            self.books[key] = book
            items.append(
                {
                    "ref": key,
                    "id": str(book.id),
                    "title": book.title,
                    "description": (book.description or "")[:1200],
                    "authors": [author.full_name for author in book.authors],
                    "language": book.language,
                    "available_copies": book.available_copies,
                }
            )
        self.evidence[ref] = summary
        return {"evidence_ref": ref, "summary": summary, "books": items}

    def run(self, db: Session, name: str, data: BaseModel, ref: str) -> dict[str, Any]:
        if isinstance(data, SearchInput):
            result = search(
                db,
                SearchParams(
                    q=data.q,
                    available=data.available,
                    language=[data.language] if data.language else [],
                    page_size=8,
                    mode="semantic" if name == "semantic_search_books" else "standard",
                ),
                self.principal,
                self.settings,
            )
            summary = (
                f"Қордан {result.total} кітап табылды. "
                f"Алғашқы {len(result.items)} нәтиже көрсетілді."
                if result.total
                else "Сұрауыңызға сәйкес кітап кітапхана қорынан табылмады."
            )
            if result.indexing_pending:
                summary += " Кейбір кітаптардың мағыналық индексі әлі дайын емес."
            return self.book_result(result.items, ref, summary)
        if isinstance(data, BookInput):
            try:
                identity = UUID(data.book_id)
            except ValueError:
                raise unavailable() from None
            if name == "get_similar_books":
                result_rec = similar(db, self.settings, identity, 8)
                return self.book_result(
                    [item.book for item in result_rec.items],
                    ref,
                    "Мазмұны ұқсас кітаптар."
                    if result_rec.items
                    else "Ұқсас кітаптар үшін дерек жеткіліксіз.",
                )
            book = get_book(db, identity)
            return self.book_result(
                [book], ref, f"«{book.title}»: қазір {book.available_copies} дана қолжетімді."
            )
        if name == "get_recommendations":
            recommendations = personalized(db, self.settings, self.principal.user.id, 8)
            return self.book_result(
                [item.book for item in recommendations.items],
                ref,
                "Қызығушылықтарыңыз бен кітапхана қорына негізделген ұсыныстар.",
            )
        if isinstance(data, PersonalInput):
            lines = []
            if name == "get_my_borrowings":
                loans = borrowing_page(
                    db, data.page, 10, user_id=self.principal.user.id, active=True
                )
                for loan in loans.items:
                    date = loan.due_at.astimezone(
                        ZoneInfo(self.settings.library_timezone)
                    ).strftime("%d.%m.%Y %H:%M %Z")
                    lines.append(
                        f"«{loan.book_title}»: қайтару мерзімі {date}."
                        + (" Мерзімі өткен." if loan.is_overdue else "")
                    )
                summary = f"Қолыңыздағы кітаптар: {loans.total}. Бет: {data.page}."
            else:
                reservations = owned_page(db, self.principal.user.id, data.page, 10, None, True)
                for reservation in reservations.items:
                    state = (
                        "алуға дайын"
                        if reservation.qr_available
                        else "кезекте"
                        if reservation.status.value == "WAITING"
                        else "алу мерзімі аяқталған"
                    )
                    lines.append(
                        f"«{reservation.book_title}»: {state}."
                        + (
                            f" Кезектегі орын: {reservation.queue_position}."
                            if reservation.queue_position
                            else ""
                        )
                    )
                summary = f"Белсенді броньдарыңыз: {reservations.total}. Бет: {data.page}."
            self.evidence[ref] = summary + "\n" + "\n".join(lines)
            return {"evidence_ref": ref, "summary": self.evidence[ref]}
        policy = circulation_policy(db)
        summary = (
            f"Кітап алу мерзімі: {policy.borrow_period_days} күн. "
            f"Бір мезетте: {policy.max_books_per_user} кітап. "
            f"Дайын бронь: {policy.reservation_hold_hours} сағат сақталады. "
            f"Ескерту: қайтаруға {policy.return_reminder_days} күн қалғанда. "
            "Мерзімі өткен кітап болса, жаңа кітап алуға шектеу: "
            f"{'бар' if policy.block_borrowing_if_overdue else 'жоқ'}; "
            f"броньдауға шектеу: {'бар' if policy.block_reservation_if_overdue else 'жоқ'}."
        )
        self.evidence[ref] = summary
        return {"evidence_ref": ref, "rules": asdict(policy), "summary": summary}
