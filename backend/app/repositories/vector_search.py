"""Exact filtered pgvector retrieval and SQL reciprocal rank fusion."""

from math import ceil
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.models import Book, BookCopy, BookEmbedding, Borrowing
from app.repositories.catalog import book_query, serialize
from app.repositories.search import filtered, standard_query
from app.schemas.search import SearchPage, SearchParams, SearchSort

# Cormack et al., SIGIR 2009: published RRF smoothing, not a similarity threshold.
RRF_K = 60


def vector_search(
    db: Session, params: SearchParams, model_id: UUID, vector: list[float]
) -> SearchPage:
    distance = BookEmbedding.embedding.cosine_distance(vector)
    semantic = filtered(
        select(Book.id, func.row_number().over(order_by=(distance, Book.id)).label("rank"))
        .join(BookEmbedding, BookEmbedding.book_id == Book.id)
        .where(BookEmbedding.model_id == model_id),
        params,
    ).cte("semantic")
    query = book_query()
    if params.mode == "hybrid":
        db.execute(select(func.set_config("pg_trgm.similarity_threshold", "0.3", True)))
        lexical = standard_query(params, rank_only=True).cte("lexical")
        query = query.outerjoin(semantic, semantic.c.id == Book.id).outerjoin(
            lexical, lexical.c.id == Book.id
        )
        query = query.where(semantic.c.id.is_not(None) | lexical.c.id.is_not(None))
        score = func.coalesce(1.0 / (RRF_K + semantic.c.rank), 0) + func.coalesce(
            1.0 / (RRF_K + lexical.c.rank), 0
        )
        query = query.order_by(
            case(
                (Book.isbn == params.q.replace("-", "").replace(" ", "").upper(), 0),
                (func.lower(Book.title) == params.q.lower(), 1),
                else_=2,
            )
        )
        relevance = score.desc()
    else:
        query = query.join(semantic, semantic.c.id == Book.id)
        relevance = semantic.c.rank.asc()
    if params.sort == SearchSort.RELEVANCE:
        query = query.order_by(relevance)
    elif params.sort == SearchSort.RECENT:
        query = query.order_by(Book.created_at.desc())
    elif params.sort in {SearchSort.YEAR_ASC, SearchSort.YEAR_DESC}:
        query = query.order_by(
            Book.publication_year.asc().nulls_last()
            if params.sort == SearchSort.YEAR_ASC
            else Book.publication_year.desc().nulls_last()
        )
    elif params.sort == SearchSort.TITLE_DESC:
        query = query.order_by(func.lower(Book.title).desc())
    elif params.sort == SearchSort.POPULARITY:
        popularity = (
            select(func.count(Borrowing.id))
            .join(BookCopy, BookCopy.id == Borrowing.book_copy_id)
            .where(BookCopy.book_id == Book.id)
            .scalar_subquery()
        )
        query = query.order_by(popularity.desc())
    query = query.order_by(func.lower(Book.title), Book.id)
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = db.execute(query.offset((params.page - 1) * params.page_size).limit(params.page_size))
    pending = (
        db.scalar(
            filtered(select(Book.id), params)
            .where(
                ~select(BookEmbedding.id)
                .where(BookEmbedding.book_id == Book.id, BookEmbedding.model_id == model_id)
                .exists()
            )
            .limit(1)
        )
        is not None
    )
    return SearchPage(
        items=[serialize(*row) for row in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=ceil(total / params.page_size),
        indexing_pending=pending,
    )
