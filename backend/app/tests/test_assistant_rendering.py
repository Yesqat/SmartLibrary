from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.ai.assistant.contracts import AnswerPlan
from app.ai.assistant.rendering import render
from app.schemas.catalog import BookRead


def catalog_entry(**changes):
    now = datetime.now(UTC)
    return BookRead.model_validate(
        {
            "id": uuid4(),
            "archived_at": None,
            "title": "Python Crash Course",
            "description": "An introduction to Python through practical projects.",
            "authors": [
                {"id": uuid4(), "full_name": "Eric Matthes", "biography": None, "archived_at": None}
            ],
            "categories": [
                {"id": uuid4(), "name": "Programming", "description": None, "archived_at": None}
            ],
            "language": "en",
            "isbn": "9781593279288",
            "publication_year": 2019,
            "page_count": None,
            "cover_url": None,
            "publisher": None,
            "created_at": now,
            "updated_at": now,
            "available_copies": 1,
            "total_copies": 3,
            "shelf_locations": ["B-12"],
            **changes,
        }
    )


def render_search(book, language, presentation):
    context = SimpleNamespace(
        results={
            "result1": {"tool": "search_books", "q": "python", "books": [{"ref": "result1_book1"}]}
        },
        books={"result1_book1": book},
    )
    plan = AnswerPlan(
        kind="results",
        language=language,
        presentation=presentation,
        book_refs=["result1_book1"],
        evidence_refs=["result1"],
    )
    return render(plan, context)[0]


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("kk", "қазір қолжетімдісі — 1 дана"),
        ("ru", "доступно сейчас — 1"),
        ("en", "Available now: 1"),
    ],
)
def test_book_details_use_real_fields_and_localized_availability(language, expected):
    book = catalog_entry()
    content = render_search(book, language, "details")
    for value in [
        book.title,
        "Eric Matthes",
        "Programming",
        book.description,
        book.isbn,
        "2019",
        "B-12",
        expected,
    ]:
        assert value in content


def test_no_physical_copies_is_distinct_from_all_unavailable():
    book = catalog_entry(available_copies=0, shelf_locations=[], isbn=None, publication_year=None)
    content = render_search(book, "en", "details")
    assert "Physical copies: 3. Available now: 0." in content
    assert "ISBN" not in content and "Year published" not in content and "Shelves" not in content
    content = render_search(book.model_copy(update={"total_copies": 0}), "ru", "availability")
    assert "Книга есть в каталоге. Физических экземпляров нет." in content


def test_recommendation_preserves_name_author_and_description_with_grounded_reason():
    book = catalog_entry()
    content = render_search(book, "kk", "recommendation")
    assert book.title in content and "Eric Matthes" in content and book.description in content
    assert "Кітап атауында «Python» кездеседі." in content


@pytest.mark.parametrize(
    ("language", "result", "expected"),
    [
        ("en", {"books": []}, "couldn't find a book matching"),
        ("ru", {"books": [{"ref": "unrelated"}]}, "Среди результатов поиска"),
        ("kk", {"error": "DATA_UNAVAILABLE"}, "қазір қолжетімсіз"),
    ],
)
def test_empty_irrelevant_and_failed_searches_have_distinct_answers(language, result, expected):
    context = SimpleNamespace(results={"r": {"tool": "search_books", **result}}, books={})
    plan = AnswerPlan(
        kind="results",
        language=language,
        presentation="recommendation",
        book_refs=[],
        evidence_refs=["r"],
    )
    content, books = render(plan, context)
    assert expected in content and books == []
