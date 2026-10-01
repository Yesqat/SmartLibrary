"""Explicit download/init/generate/check commands; runtime never fetches models."""

import argparse
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings.encoder import download, encoder, profile
from app.ai.embeddings.pipeline import generate_one
from app.core.config import Settings
from app.db.models import Book
from app.db.session import create_db_engine


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["download", "generate"])
    parser.add_argument("--book", type=UUID)
    args = parser.parse_args()
    settings = Settings()
    item = profile(settings.embedding_model, settings.embedding_model_revision)
    if args.command == "download":
        download(item, settings.model_cache_directory)
        model = encoder(item.name, item.revision, settings.model_cache_directory)
        model.encode(["Кітапхана. Библиотека. Library."], query=True)
        print(
            json.dumps({"model": item.name, "revision": item.revision, "dimension": item.dimension})
        )
        return
    engine = create_db_engine(settings)
    counts: dict[str, int] = {}
    cursor: UUID | None = None
    try:
        while True:
            with Session(engine) as db:
                query = (
                    select(Book.id).where(Book.archived_at.is_(None)).order_by(Book.id).limit(100)
                )
                if args.book:
                    query = query.where(Book.id == args.book)
                if cursor:
                    query = query.where(Book.id > cursor)
                identities = list(db.scalars(query))
            if not identities:
                break
            for identity in identities:
                result = generate_one(engine, settings, identity)
                counts[result] = counts.get(result, 0) + 1
            cursor = identities[-1]
        print(json.dumps(counts))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
