"""PostgreSQL lexical/fuzzy retrieval; no Python-side catalog filtering."""

from math import ceil
from typing import Any

from sqlalchemy import Select, case, func, literal, or_, select, union_all
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.db.enums import CopyStatus
from app.db.models.catalog import (
    Author,
    Book,
    BookAuthor,
    BookCategory,
    BookCopy,
    Category,
    Publisher,
)
from app.db.models.circulation import Borrowing
from app.repositories.catalog import book_query, serialize
from app.schemas.search import Autocomplete, SearchPage, SearchParams, SearchSort, Suggestion


def filtered(query: Select[Any], params: SearchParams) -> Select[Any]:
    if not params.include_archived:
        query = query.where(Book.archived_at.is_(None))
    if params.category:
        query = query.where(
            select(BookCategory.id)
            .where(BookCategory.book_id == Book.id, BookCategory.category_id == params.category)
            .exists()
        )
    if params.author:
        query = query.where(
            select(BookAuthor.id)
            .where(BookAuthor.book_id == Book.id, BookAuthor.author_id == params.author)
            .exists()
        )
    if params.publisher:
        query = query.where(Book.publisher_id == params.publisher)
    if params.language:
        query = query.where(Book.language.in_(params.language))
    if params.year_from:
        query = query.where(Book.publication_year >= params.year_from)
    if params.year_to:
        query = query.where(Book.publication_year <= params.year_to)
    if params.available is not None:
        available = select(BookCopy.id).where(
            BookCopy.book_id == Book.id,
            BookCopy.status == CopyStatus.AVAILABLE,
            BookCopy.archived_at.is_(None),
        ).exists() & Book.archived_at.is_(None)
        query = query.where(available if params.available else ~available)
    return query


def standard_query(params: SearchParams, *, rank_only: bool = False) -> Select[Any]:
    query = filtered(book_query(), params)
    q = params.q
    tier: ColumnElement[int] = literal(0)
    similarity: ColumnElement[float] = literal(0.0)
    if q:
        author_query = (
            select(Author.id)
            .join(BookAuthor, BookAuthor.author_id == Author.id)
            .where(BookAuthor.book_id == Book.id, Author.archived_at.is_(None))
        )
        category_query = (
            select(Category.id)
            .join(BookCategory, BookCategory.category_id == Category.id)
            .where(BookCategory.book_id == Book.id, Category.archived_at.is_(None))
        )
        publisher_query = select(Publisher.id).where(
            Publisher.id == Book.publisher_id, Publisher.archived_at.is_(None)
        )
        exact_isbn = Book.isbn == q.replace("-", "").replace(" ", "").upper()
        exact_title = func.lower(Book.title) == q.lower()
        prefix = Book.title.istartswith(q, autoescape=True)
        contains = Book.title.icontains(q, autoescape=True)
        author = author_query.where(Author.full_name.icontains(q, autoescape=True)).exists()
        category = category_query.where(Category.name.icontains(q, autoescape=True)).exists()
        publisher = publisher_query.where(Publisher.name.icontains(q, autoescape=True)).exists()
        description = Book.description.icontains(q, autoescape=True)
        fuzzy = (
            or_(
                Book.title.bool_op("%")(q),
                author_query.where(Author.full_name.bool_op("%")(q)).exists(),
            )
            if len(q) >= 3
            else literal(False)
        )
        query = query.where(
            or_(exact_isbn, contains, author, category, publisher, description, fuzzy)
        )
        tier = case(
            (exact_isbn, 0),
            (exact_title, 1),
            (prefix, 2),
            (contains, 3),
            (author, 4),
            (category, 5),
            (publisher, 6),
            (description, 7),
            else_=8,
        )
        similarity = func.similarity(Book.title, q)
    if rank_only:
        return query.with_only_columns(
            Book.id,
            func.row_number()
            .over(order_by=(tier, similarity.desc(), func.lower(Book.title), Book.id))
            .label("rank"),
        )
    sort = params.sort
    if q and sort != SearchSort.RELEVANCE:
        # Exact identifiers/titles remain pinned even when the user changes secondary sorting.
        query = query.order_by(case((tier <= 1, tier), else_=2))
    if sort == SearchSort.POPULARITY:
        counts = (
            select(BookCopy.book_id, func.count(Borrowing.id).label("loans"))
            .join(Borrowing, Borrowing.book_copy_id == BookCopy.id)
            .group_by(BookCopy.book_id)
            .subquery()
        )
        query = query.outerjoin(counts, counts.c.book_id == Book.id).order_by(
            func.coalesce(counts.c.loans, 0).desc()
        )
    elif sort == SearchSort.RECENT:
        query = query.order_by(Book.created_at.desc())
    elif sort in {SearchSort.YEAR_ASC, SearchSort.YEAR_DESC}:
        query = query.order_by(
            Book.publication_year.asc().nulls_last()
            if sort == SearchSort.YEAR_ASC
            else Book.publication_year.desc().nulls_last()
        )
    elif sort == SearchSort.TITLE_DESC:
        query = query.order_by(func.lower(Book.title).desc())
    elif sort == SearchSort.RELEVANCE:
        query = query.order_by(tier, similarity.desc())
    return query.order_by(func.lower(Book.title), Book.id)


def standard_search(db: Session, params: SearchParams) -> SearchPage:
    # SET LOCAL keeps the documented pg_trgm cutoff stable without leaking pool state.
    db.execute(select(func.set_config("pg_trgm.similarity_threshold", "0.3", True)))
    query = standard_query(params)
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = db.execute(query.offset((params.page - 1) * params.page_size).limit(params.page_size))
    return SearchPage(
        items=[serialize(*row) for row in rows],
        page=params.page,
        page_size=params.page_size,
        total=total,
        pages=ceil(total / params.page_size),
    )


def autocomplete(db: Session, q: str, limit: int) -> Autocomplete:
    if len(q) < 2:
        return Autocomplete(items=[])
    db.execute(select(func.set_config("pg_trgm.similarity_threshold", "0.3", True)))
    queries = []
    for model, column, kind in ((Book, Book.title, "book"), (Author, Author.full_name, "author")):
        exact = func.lower(column) == q.lower()
        prefix = column.istartswith(q, autoescape=True)
        contains = column.icontains(q, autoescape=True)
        query = select(
            model.id.label("id"),
            column.label("label"),
            literal(kind).label("kind"),
            case((exact, 0), (prefix, 1), (contains, 2), else_=3).label("rank"),
            func.similarity(column, q).label("similarity"),
        ).where(model.archived_at.is_(None), or_(contains, column.bool_op("%")(q)))
        if kind == "author":
            query = query.where(
                select(BookAuthor.id)
                .join(Book, Book.id == BookAuthor.book_id)
                .where(BookAuthor.author_id == Author.id, Book.archived_at.is_(None))
                .exists()
            )
        queries.append(query)
    suggestions = union_all(*queries).subquery()
    rows = db.execute(
        select(suggestions)
        .order_by(
            suggestions.c.rank,
            suggestions.c.similarity.desc(),
            suggestions.c.label,
            suggestions.c.id,
        )
        .limit(limit)
    ).mappings()
    return Autocomplete(
        items=[Suggestion(id=row["id"], label=row["label"], kind=row["kind"]) for row in rows]
    )
