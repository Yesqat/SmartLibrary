"""Reproducible temporal holdout of real loans; no invented accuracy for sparse data."""

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.recommendations.collaborative import ItemNeighbors
from app.core.config import Settings
from app.db.models import BookCopy, Borrowing
from app.db.session import create_db_engine


def evaluate(histories: dict[UUID, list[UUID]]) -> dict[str, object]:
    # Repeated loans are a single consumed item for this binary baseline.
    eligible = {user: list(dict.fromkeys(books)) for user, books in histories.items()}
    eligible = {user: books for user, books in eligible.items() if len(books) >= 3}
    items = {book for books in eligible.values() for book in books}
    output: dict[str, object] = {
        "readers_with_three_distinct_loans": len(eligible),
        "distinct_titles": len(items),
        "minimum_readers": 20,
        "minimum_titles": 20,
        "method": (
            "binary item cosine; minimum pair support 2; last distinct loan held out per Reader"
        ),
        "serving_enabled": False,
    }
    if len(eligible) < 20 or len(items) < 20:
        return {**output, "status": "INSUFFICIENT_DATA", "metrics": None}
    model = ItemNeighbors(set(books[:-1]) for books in eligible.values())
    hits, covered, reciprocal = 0, 0, 0.0
    for books in eligible.values():
        ranked = model.rank(set(books[:-1]), 10)
        covered += bool(ranked)
        if books[-1] in ranked:
            hits += 1
            reciprocal += 1 / (ranked.index(books[-1]) + 1)
    return {
        **output,
        "status": "EVALUATED",
        "metrics": {
            "recall_at_10": hits / len(eligible),
            "mrr_at_10": reciprocal / len(eligible),
            "coverage": covered / len(eligible),
        },
        "limitation": (
            "Per-Reader temporal split can share wall-clock periods. Validate on a global "
            "time split and against the content baseline before enabling serving."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    engine = create_db_engine(Settings())
    histories: dict[UUID, list[UUID]] = defaultdict(list)
    digest = hashlib.sha256()
    try:
        with Session(engine) as db:
            rows = db.execute(
                select(Borrowing.user_id, BookCopy.book_id, Borrowing.borrowed_at)
                .join(BookCopy)
                .order_by(Borrowing.borrowed_at, Borrowing.id)
                .execution_options(yield_per=1000)
            )
            for user, book, when in rows:
                histories[user].append(book)
                digest.update(f"{user}:{book}:{when.isoformat()}\n".encode())
    finally:
        engine.dispose()
    result = {
        **evaluate(histories),
        "data_sha256": digest.hexdigest(),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
