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
from app.schemas.recommendations import RecommendationPage
from app.schemas.search import SearchParams
from app.services.audit.events import AuditContext
from app.services.auth.service import AuthService
from app.services.search.service import search
from app.services.settings.policy import circulation_policy


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchInput(Empty):
    q: str = Field(
        max_length=500, description="Short catalog term, or empty for a filter-only list."
    )
    available: bool | None
    language: str | None = Field(
        pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$",
        max_length=35,
        description="Requested book language (kk, ru, en, etc.), null if unspecified.",
    )


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
        "General recommendations for the authenticated Reader. For a specific topic use search.",
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


def excerpt(description: str, query: str) -> str:
    """Give the model and the reader a short catalog excerpt around the matching term."""
    text = description.strip()
    if len(text) <= 320:
        return text
    position = text.casefold().find(query.casefold()) if query else 0
    start = max(0, position - 80)
    if start and (space := text.rfind(" ", max(0, start - 40), start + 1)) >= 0:
        start = space + 1
    end = start + 320
    return ("…" if start else "") + text[start:end].strip() + ("…" if end < len(text) else "")


class ToolContext:
    def __init__(
        self, engine: Engine, settings: Settings, principal: Principal, context: AuditContext
    ):
        self.engine, self.settings, self.principal = engine, settings, principal
        self.auth = AuthService(engine, settings, context)
        self.books: dict[str, BookRead] = {}
        self.results: dict[str, dict[str, Any]] = {}
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
                result = self.run(db, name, data, ref)
        except AppError as error:
            if error.status in (401, 403):
                raise
            self.trace[-1]["status"] = "unavailable"
            result = {"error": "DATA_UNAVAILABLE"}
        result.update(evidence_ref=ref, tool=name)
        self.results[ref] = result
        return result

    def book_rows(self, books: list[BookRead], ref: str, query: str = "") -> list[dict[str, Any]]:
        items = []
        for index, book in enumerate(books):
            key = f"{ref}_book{index + 1}"
            self.books[key] = book
            items.append(
                {
                    "ref": key,
                    "id": str(book.id),
                    "title": book.title,
                    "description": excerpt(book.description, query) if book.description else None,
                    "authors": [author.full_name for author in book.authors],
                    "categories": [category.name for category in book.categories],
                    "publication_year": book.publication_year,
                    "isbn": book.isbn,
                    "language": book.language,
                    "total_copies": book.total_copies,
                    "available_copies": book.available_copies,
                    "shelf_locations": book.shelf_locations,
                }
            )
        return items

    def recommendation_result(self, result: RecommendationPage, ref: str) -> dict[str, Any]:
        books = self.book_rows([item.book for item in result.items], ref)
        for book, item in zip(books, result.items, strict=True):
            book["reason"] = item.reason
        return {"books": books, "indexing_pending": result.indexing_pending}

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
            return {
                "q": data.q,
                "total": result.total,
                "indexing_pending": result.indexing_pending,
                "books": self.book_rows(result.items, ref, data.q),
            }
        if isinstance(data, BookInput):
            try:
                identity = UUID(data.book_id)
            except ValueError:
                raise unavailable() from None
            if name == "get_similar_books":
                return self.recommendation_result(similar(db, self.settings, identity, 8), ref)
            book = get_book(db, identity)
            return {"books": self.book_rows([book], ref)}
        if name == "get_recommendations":
            recommendations = personalized(db, self.settings, self.principal.user.id, 8)
            return self.recommendation_result(recommendations, ref)
        if isinstance(data, PersonalInput):
            if name == "get_my_borrowings":
                loans = borrowing_page(
                    db, data.page, 10, user_id=self.principal.user.id, active=True
                )
                zone = ZoneInfo(self.settings.library_timezone)
                return {
                    "total": loans.total,
                    "page": data.page,
                    "loans": [
                        {
                            "title": loan.book_title,
                            "due_at": loan.due_at.astimezone(zone).strftime("%d.%m.%Y %H:%M %Z"),
                            "overdue": loan.is_overdue,
                        }
                        for loan in loans.items
                    ],
                }
            reservations = owned_page(db, self.principal.user.id, data.page, 10, None, True)
            entries = []
            for reservation in reservations.items:
                state = "expired"
                if reservation.qr_available:
                    state = "ready"
                elif reservation.status.value == "WAITING":
                    state = "waiting"
                entries.append(
                    {
                        "title": reservation.book_title,
                        "state": state,
                        "queue_position": reservation.queue_position,
                    }
                )
            return {"total": reservations.total, "page": data.page, "reservations": entries}
        return {"rules": asdict(circulation_policy(db))}
