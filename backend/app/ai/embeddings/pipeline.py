"""Durable pending state is the absence of a current book/model vector."""

from typing import Any
from uuid import UUID

from sqlalchemy import Engine, Select, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.ai.embeddings.encoder import ModelProfile, encoder, profile
from app.ai.embeddings.source import RECIPE, book_source, source_hash
from app.core.config import Settings
from app.core.security import now
from app.db.models import (
    Author,
    Book,
    BookAuthor,
    BookCategory,
    BookEmbedding,
    Category,
    EmbeddingModel,
    Publisher,
)
from app.repositories.catalog import get_book


def model_record(db: Session, item: ModelProfile) -> EmbeddingModel:
    db.execute(
        insert(EmbeddingModel)
        .values(
            model_name=item.name,
            revision=item.revision,
            dimension=item.dimension,
            source_recipe=RECIPE,
            normalized=True,
            configuration={
                "query_prefix": item.query_prefix,
                "passage_prefix": item.passage_prefix,
                "max_tokens": item.max_tokens,
                "pooling": "model-defined",
                "device": "cpu",
            },
        )
        .on_conflict_do_nothing(constraint="uq_embedding_models_space")
    )
    row = db.scalar(
        select(EmbeddingModel).where(
            EmbeddingModel.model_name == item.name,
            EmbeddingModel.revision == item.revision,
            EmbeddingModel.source_recipe == RECIPE,
        )
    )
    if row is None or row.dimension != item.dimension or not row.normalized:
        raise ValueError("Stored model space does not match the configured encoder")
    return row


def invalidate(db: Session, book_ids: list[UUID] | Select[Any]) -> None:
    # The deletion commits with metadata: stale vectors never remain searchable.
    db.execute(delete(BookEmbedding).where(BookEmbedding.book_id.in_(book_ids)))


def lock_source(db: Session, identity: UUID) -> bool:
    book = db.scalar(select(Book).where(Book.id == identity).with_for_update())
    if not book or book.archived_at:
        return False
    # Match catalog's Book -> Author -> Category -> Publisher order. Reference
    # changes invalidate embeddings without locking Books, so no reverse edge.
    for model, identities in (
        (Author, select(BookAuthor.author_id).where(BookAuthor.book_id == identity)),
        (Category, select(BookCategory.category_id).where(BookCategory.book_id == identity)),
        (Publisher, select(Book.publisher_id).where(Book.id == identity)),
    ):
        list(
            db.scalars(
                select(model)
                .where(model.id.in_(identities))
                .order_by(model.id)
                .with_for_update(read=True)
            )
        )
    return True


def generate_one(engine: Engine, settings: Settings, identity: UUID) -> str:
    item = profile(settings.embedding_model, settings.embedding_model_revision)
    with Session(engine) as db, db.begin():
        space = model_record(db, item)
        space_id = space.id
        book = db.get(Book, identity)
        if not book or book.archived_at:
            return "archived"
        source = book_source(get_book(db, identity))
        digest = source_hash(source)
        existing = db.scalar(
            select(BookEmbedding.source_hash).where(
                BookEmbedding.book_id == identity, BookEmbedding.model_id == space_id
            )
        )
        if existing == digest:
            return "unchanged"
    vector = encoder(item.name, item.revision, settings.model_cache_directory).encode([source])[0]
    return persist_vector(engine, identity, item, space_id, digest, vector)


def persist_vector(
    engine: Engine,
    identity: UUID,
    item: ModelProfile,
    space_id: UUID,
    digest: str,
    vector: list[float],
) -> str:
    """Compare the inference snapshot again under metadata locks before publishing."""
    with Session(engine) as db, db.begin():
        if not lock_source(db, identity):
            return "archived"
        if source_hash(book_source(get_book(db, identity))) != digest:
            return "stale"
        statement = insert(BookEmbedding).values(
            book_id=identity,
            model_id=space_id,
            dimension=item.dimension,
            embedding=vector,
            source_hash=digest,
            generated_at=now(),
        )
        updated = db.scalar(
            statement.on_conflict_do_update(
                index_elements=["book_id", "model_id"],
                set_={
                    key: getattr(statement.excluded, key)
                    for key in ("dimension", "embedding", "source_hash", "generated_at")
                },
                where=BookEmbedding.source_hash != digest,
            ).returning(BookEmbedding.id)
        )
    return "generated" if updated else "unchanged"


def generate_batch(engine: Engine, settings: Settings, *, limit: int = 100) -> dict[str, int]:
    item = profile(settings.embedding_model, settings.embedding_model_revision)
    with Session(engine) as db, db.begin():
        space = model_record(db, item)
        identities = list(
            db.scalars(
                select(Book.id)
                .where(
                    Book.archived_at.is_(None),
                    ~select(BookEmbedding.id)
                    .where(BookEmbedding.book_id == Book.id, BookEmbedding.model_id == space.id)
                    .exists(),
                )
                .order_by(Book.created_at, Book.id)
                .limit(limit)
            )
        )
    counts: dict[str, int] = {}
    for identity in identities:
        result = generate_one(engine, settings, identity)
        counts[result] = counts.get(result, 0) + 1
    return counts
