"""Public vector search uses only the explicitly selected immutable model space."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings.encoder import encoder, profile
from app.ai.embeddings.source import RECIPE
from app.core.config import Settings
from app.core.errors import AppError
from app.db.models import EmbeddingModel
from app.repositories.vector_search import vector_search
from app.schemas.search import SearchPage, SearchParams


def semantic_search(db: Session, settings: Settings, params: SearchParams) -> SearchPage:
    item = profile(settings.embedding_model, settings.embedding_model_revision)
    space = db.scalar(
        select(EmbeddingModel).where(
            EmbeddingModel.model_name == item.name,
            EmbeddingModel.revision == item.revision,
            EmbeddingModel.dimension == item.dimension,
            EmbeddingModel.source_recipe == RECIPE,
            EmbeddingModel.normalized.is_(True),
        )
    )
    if space is None:
        raise AppError("SEMANTIC_SEARCH_UNAVAILABLE", "Мағыналық іздеу әзірге қолжетімсіз.", 503)
    try:
        vector = encoder(item.name, item.revision, settings.model_cache_directory).encode(
            [params.q], query=True
        )[0]
    except Exception:
        logging.getLogger("smartlibrary").warning("query_embedding_unavailable")
        raise AppError(
            "SEMANTIC_SEARCH_UNAVAILABLE", "Мағыналық іздеу әзірге қолжетімсіз.", 503
        ) from None
    return vector_search(db, params, space.id, vector)
