from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy.orm import Session

from app.ai.recommendations.service import personalized, popular, similar
from app.ai.recommendations.tracking import click, impression, offer
from app.api.dependencies import OptionalPrincipal
from app.api.v1.routes.catalog import Reader, mutations
from app.api.v1.routes.search import enforce_limit
from app.core.auth_http import client_ip
from app.schemas.auth import ErrorResponse
from app.schemas.recommendations import ImpressionInput, ImpressionRead, RecommendationPage

router = APIRouter(
    prefix="/api/v1",
    tags=["Recommendations"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 422, 429, 503)},
)
Limit = Annotated[int, Query(ge=1, le=20)]


def limit_request(request: Request, response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    enforce_limit(request, "recommendations", client_ip(request), 60)


@router.get("/books/popular", response_model=RecommendationPage)
def popular_books(
    request: Request, response: Response, principal: OptionalPrincipal, limit: Limit = 8
) -> RecommendationPage:
    limit_request(request, response)
    with Session(request.app.state.db) as db:
        return offer(request.app.state.settings, principal, popular(db, limit))


@router.get("/books/{book_id}/similar", response_model=RecommendationPage)
def similar_books(
    book_id: UUID,
    request: Request,
    response: Response,
    principal: OptionalPrincipal,
    limit: Limit = 6,
) -> RecommendationPage:
    limit_request(request, response)
    with Session(request.app.state.db) as db:
        return offer(
            request.app.state.settings,
            principal,
            similar(db, request.app.state.settings, book_id, limit),
        )


@router.get("/recommendations/me", response_model=RecommendationPage)
def my_recommendations(
    request: Request, response: Response, principal: Reader, limit: Limit = 8
) -> RecommendationPage:
    limit_request(request, response)
    with Session(request.app.state.db) as db:
        return offer(
            request.app.state.settings,
            principal,
            personalized(db, request.app.state.settings, principal.user.id, limit),
        )


@router.post("/recommendations/impressions", response_model=ImpressionRead, dependencies=mutations)
def record_impression(data: ImpressionInput, request: Request, principal: Reader) -> ImpressionRead:
    enforce_limit(request, "recommendation-events", str(principal.user.id), 180)
    return ImpressionRead(
        id=impression(request.app.state.db, request.app.state.settings, principal, data)
    )


@router.post(
    "/recommendations/impressions/{identity}/click", status_code=204, dependencies=mutations
)
def record_click(identity: UUID, request: Request, principal: Reader) -> Response:
    enforce_limit(request, "recommendation-events", str(principal.user.id), 180)
    click(request.app.state.db, request.app.state.settings, principal, identity)
    return Response(status_code=204)
