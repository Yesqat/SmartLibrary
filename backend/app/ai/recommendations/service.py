"""Content recommendations query real model spaces and canonical Reader signals."""

from uuid import UUID

import numpy as np
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.ai.embeddings.encoder import profile
from app.ai.embeddings.source import RECIPE
from app.ai.recommendations.policy import POLICY, RecommendationPolicy
from app.core.config import Settings
from app.core.errors import AppError
from app.db.enums import RecommendationType
from app.db.models import Book, BookEmbedding, EmbeddingModel
from app.repositories.catalog import book_query, get_book, serialize
from app.repositories.recommendations import consumed, preferences, signals
from app.schemas.recommendations import Reason, RecommendationItem, RecommendationPage


def model_space(db: Session, settings: Settings) -> EmbeddingModel | None:
    try:
        item = profile(settings.embedding_model, settings.embedding_model_revision)
    except AppError:
        return None
    return db.scalar(
        select(EmbeddingModel).where(
            EmbeddingModel.model_name == item.name,
            EmbeddingModel.revision == item.revision,
            EmbeddingModel.dimension == item.dimension,
            EmbeddingModel.source_recipe == RECIPE,
            EmbeddingModel.normalized.is_(True),
        )
    )


def interest_vector(
    db: Session, user_id: UUID, space: UUID, policy: RecommendationPolicy = POLICY
) -> list[float] | None:
    interest = signals(user_id, policy)
    rows = db.execute(
        select(BookEmbedding.embedding, interest.c.weight)
        .join(interest, interest.c.book_id == BookEmbedding.book_id)
        .join(Book, Book.id == BookEmbedding.book_id)
        .where(BookEmbedding.model_id == space, Book.archived_at.is_(None))
        .order_by(interest.c.weight.desc(), BookEmbedding.book_id)
        .limit(policy.profile_books)
    ).all()
    if not rows:
        return None
    vectors = np.asarray([row[0] for row in rows], dtype=np.float64)
    weights = np.asarray([row[1] for row in rows], dtype=np.float64)
    vector = np.average(vectors, axis=0, weights=weights)
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(vector).all() or norm < 1e-12:
        return None
    return [float(value) for value in vector / norm]


def popular(db: Session, limit: int) -> RecommendationPage:
    popularity = signals()
    rows = db.execute(
        book_query()
        .join(popularity, popularity.c.book_id == Book.id)
        .where(Book.archived_at.is_(None), popularity.c.weight > 0)
        .order_by(popularity.c.weight.desc(), Book.created_at.desc(), Book.id)
        .limit(limit)
    )
    return RecommendationPage(
        recommendation_type=RecommendationType.POPULAR,
        items=[RecommendationItem(book=serialize(*row), reason="popular") for row in rows],
    )


def similar(db: Session, settings: Settings, identity: UUID, limit: int) -> RecommendationPage:
    get_book(db, identity)
    space = model_space(db, settings)
    vector = (
        db.scalar(
            select(BookEmbedding.embedding).where(
                BookEmbedding.book_id == identity, BookEmbedding.model_id == space.id
            )
        )
        if space
        else None
    )
    result = RecommendationPage(
        recommendation_type=RecommendationType.SIMILAR_BOOK,
        items=[],
        content_available=vector is not None,
        indexing_pending=space is not None and vector is None,
    )
    if vector is None or space is None:
        return result
    rows = db.execute(
        book_query()
        .join(BookEmbedding, BookEmbedding.book_id == Book.id)
        .where(Book.archived_at.is_(None), Book.id != identity, BookEmbedding.model_id == space.id)
        .order_by(BookEmbedding.embedding.cosine_distance(vector), Book.id)
        .limit(limit)
    )
    result.items = [RecommendationItem(book=serialize(*row), reason="similar") for row in rows]
    return result


def personalized(db: Session, settings: Settings, user_id: UUID, limit: int) -> RecommendationPage:
    space = model_space(db, settings)
    vector = interest_vector(db, user_id, space.id) if space else None
    popularity = signals()
    preference = preferences(user_id)
    eligible = Book.archived_at.is_(None) & ~Book.id.in_(consumed(user_id))
    pop_weight = func.coalesce(popularity.c.weight, 0)
    pref_weight = func.coalesce(preference.c.weight, 0)
    ranking = (
        select(
            Book.id,
            pop_weight.label("popularity"),
            pref_weight.label("preference"),
            func.row_number().over(order_by=(pop_weight.desc(), Book.id)).label("pop_rank"),
            func.row_number().over(order_by=(pref_weight.desc(), Book.id)).label("pref_rank"),
        )
        .outerjoin(popularity, popularity.c.book_id == Book.id)
        .outerjoin(preference, preference.c.book_id == Book.id)
        .where(eligible)
        .cte("candidate_ranks")
    )
    query = book_query().join(ranking, ranking.c.id == Book.id)
    if vector is not None and space:
        content = (
            select(
                Book.id,
                func.row_number()
                .over(order_by=(BookEmbedding.embedding.cosine_distance(vector), Book.id))
                .label("rank"),
            )
            .join(BookEmbedding, BookEmbedding.book_id == Book.id)
            .where(eligible, BookEmbedding.model_id == space.id)
            .cte("content_ranks")
        )
        score = (
            func.coalesce(1.0 / (POLICY.rrf_k + content.c.rank), 0)
            + case((ranking.c.preference > 0, 1.0 / (POLICY.rrf_k + ranking.c.pref_rank)), else_=0)
            + case((ranking.c.popularity > 0, 1.0 / (POLICY.rrf_k + ranking.c.pop_rank)), else_=0)
        )
        query = query.outerjoin(content, content.c.id == Book.id).order_by(score.desc())
    else:
        query = query.order_by(ranking.c.preference.desc(), ranking.c.popularity.desc())
    rows = db.execute(
        query.add_columns(ranking.c.preference, ranking.c.popularity)
        .order_by(Book.created_at.desc(), Book.id)
        .limit(limit)
    )
    items = []
    for book, total, available, shelves, pref, pop in rows:
        reason: Reason = (
            "preferences"
            if pref > 0
            else "history"
            if vector is not None
            else "popular"
            if pop > 0
            else "recent"
        )
        items.append(
            RecommendationItem(book=serialize(book, total, available, shelves), reason=reason)
        )
    return RecommendationPage(
        recommendation_type=RecommendationType.PERSONALIZED,
        items=items,
        content_available=vector is not None,
    )
