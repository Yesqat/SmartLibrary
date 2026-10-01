"""Prediction input deliberately excludes existing categories to prevent label leakage."""

import hashlib
import json

from app.ai.embeddings.source import source_text
from app.schemas.catalog import BookRead

RECIPE = "categorization-v1"


def input_text(book: BookRead) -> str:
    return source_text(
        book.title,
        book.description or "",
        [a.full_name for a in book.authors],
        [],
        book.language,
        book.publication_year,
        book.publisher.name if book.publisher else None,
    )


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def source_hash(text: str) -> str:
    return digest([RECIPE, text])
