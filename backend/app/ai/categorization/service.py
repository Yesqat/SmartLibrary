"""Inference snapshots and explicit atomic staff review; never auto-assign categories."""

import logging
from math import ceil
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.ai.categorization.artifact import load
from app.ai.categorization.inference import CategoryText, predict
from app.ai.categorization.source import RECIPE, digest, input_text, source_hash
from app.ai.embeddings.dispatch import request_generation
from app.ai.embeddings.pipeline import invalidate, lock_source
from app.core.errors import AppError
from app.core.security import now
from app.db.enums import PredictionReview
from app.db.models import (
    Book,
    BookCategory,
    Category,
    CategoryPrediction,
    CategoryPredictionRun,
    CategoryPredictionSelection,
)
from app.repositories.catalog import get_book
from app.schemas.catalog import Page
from app.schemas.categorization import (
    CategorizeInput,
    PredictionRead,
    PredictionRunRead,
    ReviewInput,
    SelectedCategory,
)
from app.services.catalog.service import CatalogService, transaction


def taxonomy(db: Session, *, lock: bool = False) -> tuple[CategoryText, ...]:
    query = select(Category).where(Category.archived_at.is_(None)).order_by(Category.id)
    if lock:
        query = query.with_for_update(read=True)
    return tuple((row.id, row.name, row.description or "") for row in db.scalars(query))


def taxonomy_hash(rows: tuple[CategoryText, ...]) -> str:
    return digest([[str(identity), name, description] for identity, name, description in rows])


def serialize_runs(db: Session, runs: list[CategoryPredictionRun]) -> list[PredictionRunRead]:
    identities = [run.id for run in runs]
    predictions: dict[UUID, list[PredictionRead]] = {identity: [] for identity in identities}
    selections: dict[UUID, list[SelectedCategory]] = {identity: [] for identity in identities}
    titles = {
        identity: title
        for identity, title in db.execute(
            select(Book.id, Book.title).where(Book.id.in_([run.book_id for run in runs]))
        )
    }
    for row, name in db.execute(
        select(CategoryPrediction, Category.name)
        .join(Category)
        .where(CategoryPrediction.run_id.in_(identities))
        .order_by(CategoryPrediction.confidence.desc(), Category.id)
    ):
        predictions[row.run_id].append(
            PredictionRead(
                id=row.id,
                category_id=row.category_id,
                name=name,
                confidence=row.confidence,
                score_kind=row.score_kind,
                accepted=row.accepted,
            )
        )
    for row, name in db.execute(
        select(CategoryPredictionSelection, Category.name)
        .join(Category)
        .where(CategoryPredictionSelection.run_id.in_(identities))
        .order_by(Category.name)
    ):
        selections[row.run_id].append(SelectedCategory(id=row.category_id, name=name))
    return [
        PredictionRunRead(
            id=run.id,
            book_id=run.book_id,
            book_title=titles[run.book_id],
            model_name=run.model_name,
            model_revision=run.model_revision,
            review_status=run.review_status,
            created_at=run.created_at,
            reviewed_at=run.reviewed_at,
            reviewed_by=run.reviewed_by,
            threshold=float(str(run.configuration["threshold"])),
            predictions=predictions[run.id],
            selected_categories=selections[run.id],
        )
        for run in runs
    ]


def page(
    db: Session, number: int, size: int, book_id: UUID | None, status: PredictionReview | None
) -> Page[PredictionRunRead]:
    query = select(CategoryPredictionRun)
    if book_id:
        query = query.where(CategoryPredictionRun.book_id == book_id)
    if status:
        query = query.where(CategoryPredictionRun.review_status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(
        db.scalars(
            query.order_by(CategoryPredictionRun.created_at.desc(), CategoryPredictionRun.id)
            .offset((number - 1) * size)
            .limit(size)
        )
    )
    return Page(
        items=serialize_runs(db, rows),
        total=total,
        page=number,
        page_size=size,
        pages=ceil(total / size),
    )


class CategorizationService(CatalogService):
    def generate(self, data: CategorizeInput) -> PredictionRunRead:
        artifact = load(self.settings.model_cache_directory)
        if artifact.source_recipe != RECIPE:
            raise AppError("CATEGORIZATION_UNAVAILABLE", "Санаттау моделі әзірге қолжетімсіз.", 503)
        with Session(self.engine) as db:
            book = get_book(db, data.book_id)
            text = input_text(book)
            source = source_hash(text)
            categories = taxonomy(db)
            original = sorted(str(row.id) for row in book.categories)
        try:
            predictions = predict(
                artifact, self.settings.model_cache_directory, text, categories, data.method
            )
        except Exception:
            logging.getLogger("smartlibrary").warning("categorization_inference_unavailable")
            raise AppError(
                "CATEGORIZATION_UNAVAILABLE", "Санаттау моделі әзірге қолжетімсіз.", 503
            ) from None
        with transaction(self.engine) as db:
            if not lock_source(db, data.book_id):
                raise AppError("BOOK_NOT_FOUND", "Кітап табылмады.", 404)
            current = get_book(db, data.book_id)
            active = taxonomy(db, lock=True)
            self.authorize(db)
            if (
                source_hash(input_text(current)) != source
                or taxonomy_hash(active) != taxonomy_hash(categories)
                or sorted(str(row.id) for row in current.categories) != original
            ):
                raise AppError(
                    "STALE_PREDICTION", "Кітап не санаттар өзгерді. Ұсынысты қайта жасаңыз.", 409
                )
            run = CategoryPredictionRun(
                book_id=data.book_id,
                requested_by=self.principal.user.id,
                model_name="tfidf-ovr-logistic"
                if data.method == "classical"
                else artifact.embedding_model,
                model_revision=artifact.revision,
                source_hash=source,
                configuration={
                    "method": data.method,
                    "threshold": artifact.classical_threshold
                    if data.method == "classical"
                    else artifact.embedding_threshold,
                    "source_recipe": RECIPE,
                    "initial_categories": original,
                    "taxonomy_hash": taxonomy_hash(categories),
                    "embedding_revision": artifact.embedding_revision,
                    "dataset_sha256": artifact.dataset_sha256,
                },
            )
            db.add(run)
            db.flush()
            for identity, score, kind in predictions:
                db.add(
                    CategoryPrediction(
                        run_id=run.id,
                        book_id=data.book_id,
                        category_id=identity,
                        confidence=score,
                        score_kind=kind,
                    )
                )
            self.audit(db, "CATEGORY_PREDICTED", "CATEGORY_PREDICTION", run.id)
            db.flush()
            return serialize_runs(db, [run])[0]

    def review(self, identity: UUID, data: ReviewInput) -> PredictionRunRead:
        with transaction(self.engine) as db:
            initial = db.get(CategoryPredictionRun, identity)
            if initial is None:
                raise AppError("NOT_FOUND", "Ұсыныс табылмады.", 404)
            book = self.lock_book(db, initial.book_id)
            run = db.scalar(
                select(CategoryPredictionRun)
                .where(CategoryPredictionRun.id == identity)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            assert run is not None
            selected = set(data.category_ids)
            if run.review_status != PredictionReview.PENDING:
                self.authorize(db)
                existing = set(
                    db.scalars(
                        select(CategoryPredictionSelection.category_id).where(
                            CategoryPredictionSelection.run_id == identity
                        )
                    )
                )
                if selected != existing:
                    raise AppError("PREDICTION_ALREADY_REVIEWED", "Ұсыныс бұрын қаралған.", 409)
                return serialize_runs(db, [run])[0]
            if not lock_source(db, book.id):
                raise AppError("BOOK_NOT_FOUND", "Кітап табылмады.", 404)
            active = taxonomy(db, lock=True)
            self.authorize(db)
            current = get_book(db, book.id)
            if (
                run.source_hash != source_hash(input_text(current))
                or run.configuration["taxonomy_hash"] != taxonomy_hash(active)
                or run.configuration["initial_categories"]
                != sorted(str(row.id) for row in current.categories)
            ):
                raise AppError(
                    "STALE_PREDICTION", "Кітап не санаттар өзгерді. Ұсынысты қайта жасаңыз.", 409
                )
            if not selected <= {row[0] for row in active}:
                raise AppError("CATEGORY_NOT_FOUND", "Санат табылмады немесе мұрағатта.", 404)
            predictions = list(
                db.scalars(select(CategoryPrediction).where(CategoryPrediction.run_id == identity))
            )
            predicted = {row.category_id for row in predictions}
            status = (
                PredictionReview.REJECTED
                if not selected
                else PredictionReview.ACCEPTED
                if selected == predicted
                else PredictionReview.MODIFIED
            )
            reviewed = now()
            run.review_status, run.reviewed_by, run.reviewed_at = (
                status,
                self.principal.user.id,
                reviewed,
            )
            for row in predictions:
                row.accepted, row.reviewed_by, row.reviewed_at = (
                    row.category_id in selected,
                    self.principal.user.id,
                    reviewed,
                )
            db.execute(delete(BookCategory).where(BookCategory.book_id == book.id))
            for category in sorted(selected):
                db.add(BookCategory(book_id=book.id, category_id=category))
                db.add(CategoryPredictionSelection(run_id=identity, category_id=category))
            book.updated_at = reviewed
            invalidate(db, [book.id])
            self.audit(db, "CATEGORY_REVIEWED", "CATEGORY_PREDICTION", identity)
            self.audit(db, "BOOK_UPDATED", "BOOK", book.id)
            db.flush()
            result = serialize_runs(db, [run])[0]
        request_generation(self.settings)
        return result
