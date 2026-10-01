from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.ai.categorization.service import CategorizationService, page, serialize_runs
from app.api.v1.routes.catalog import PageNumber, PageSize, Staff, mutations
from app.api.v1.routes.search import enforce_limit
from app.core.auth_http import audit_context
from app.core.errors import AppError
from app.db.enums import PredictionReview
from app.db.models import CategoryPredictionRun
from app.schemas.auth import ErrorResponse
from app.schemas.catalog import Page
from app.schemas.categorization import CategorizeInput, PredictionRunRead, ReviewInput

router = APIRouter(
    prefix="/api/v1/ai",
    tags=["Categorization"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 429, 503)},
)


def service(request: Request, principal: Staff) -> CategorizationService:
    return CategorizationService(
        request.app.state.db, request.app.state.settings, audit_context(request), principal
    )


@router.post(
    "/categorize", response_model=PredictionRunRead, status_code=201, dependencies=mutations
)
def categorize(data: CategorizeInput, request: Request, principal: Staff) -> PredictionRunRead:
    enforce_limit(request, "categorization", str(principal.user.id), 10)
    return service(request, principal).generate(data)


@router.get("/category-predictions", response_model=Page[PredictionRunRead])
def predictions(
    request: Request,
    principal: Staff,
    page_number: PageNumber = 1,
    page_size: PageSize = 20,
    book_id: UUID | None = None,
    status: PredictionReview | None = None,
) -> Page[PredictionRunRead]:
    with Session(request.app.state.db) as db:
        return page(db, page_number, page_size, book_id, status)


@router.get("/category-predictions/{identity}", response_model=PredictionRunRead)
def prediction(identity: UUID, request: Request, principal: Staff) -> PredictionRunRead:
    with Session(request.app.state.db) as db:
        row = db.get(CategoryPredictionRun, identity)
        if row is None:
            raise AppError("NOT_FOUND", "Ұсыныс табылмады.", 404)
        return serialize_runs(db, [row])[0]


@router.post(
    "/category-predictions/{identity}/review",
    response_model=PredictionRunRead,
    dependencies=mutations,
)
def review(
    identity: UUID, data: ReviewInput, request: Request, principal: Staff
) -> PredictionRunRead:
    enforce_limit(request, "categorization-review", str(principal.user.id), 60)
    return service(request, principal).review(identity, data)
