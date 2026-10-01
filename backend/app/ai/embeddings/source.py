"""Stable bibliographic source, independent of inventory, views or circulation."""

import hashlib
import unicodedata

from app.schemas.catalog import BookRead

RECIPE = "bibliography-v1"


def source_text(
    title: str,
    description: str | None,
    authors: list[str],
    categories: list[str],
    language: str,
    year: int | None,
    publisher: str | None = None,
) -> str:
    def clean(value: str) -> str:
        return " ".join(unicodedata.normalize("NFC", value).split())

    fields = [
        ("Title", title),
        ("Authors", "; ".join(sorted(set(authors)))),
        ("Categories", "; ".join(sorted(set(categories)))),
        ("Language", language),
        ("Year", str(year) if year else ""),
        ("Publisher", publisher or ""),
        ("Description", description or ""),
    ]
    return "\n".join(f"{key}: {clean(value)}" for key, value in fields if value)


def book_source(book: BookRead) -> str:
    return source_text(
        book.title,
        book.description,
        [item.full_name for item in book.authors if item.archived_at is None],
        [item.name for item in book.categories if item.archived_at is None],
        book.language,
        book.publication_year,
        book.publisher.name if book.publisher and book.publisher.archived_at is None else None,
    )


def source_hash(text: str) -> str:
    return hashlib.sha256((RECIPE + "\n" + text).encode()).hexdigest()
