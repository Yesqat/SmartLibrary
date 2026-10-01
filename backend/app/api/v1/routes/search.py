from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import OptionalPrincipal
from app.api.v1.routes.catalog import Reader, check_archived, mutations
from app.core.auth_http import audit_context, client_ip
from app.core.errors import AppError
from app.core.rate_limit import consume
from app.repositories.search import autocomplete
from app.schemas.auth import ErrorResponse
from app.schemas.search import Autocomplete, SearchClick, SearchPage, SearchParams
from app.services.search.service import record_click, search

router = APIRouter(
    prefix="/api/v1/search",
    tags=["Search"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 422, 429, 503)},
)


def enforce_limit(request: Request, scope: str, identity: str, maximum: int) -> None:
    try:
        consume(request, scope, identity, maximum, 60)
    except AppError as exc:
        if exc.code == "AUTH_SERVICE_UNAVAILABLE":
            raise AppError("SEARCH_FAILED", "Іздеу қызметі уақытша қолжетімсіз.", 503) from None
        raise


@router.get("", response_model=SearchPage)
def standard(
    request: Request, principal: OptionalPrincipal, params: Annotated[SearchParams, Query()]
) -> SearchPage:
    enforce_limit(request, "search", client_ip(request), 120)
    if params.mode != "standard" and params.q:
        enforce_limit(request, "vector-search", client_ip(request), 30)
    check_archived(params.include_archived, principal)
    with Session(request.app.state.db) as db, db.begin():
        return search(db, params, principal, request.app.state.settings)


@router.get("/semantic", response_model=SearchPage)
def semantic(
    request: Request, principal: OptionalPrincipal, params: Annotated[SearchParams, Query()]
) -> SearchPage:
    return standard(request, principal, params.model_copy(update={"mode": "semantic"}))


@router.get("/hybrid", response_model=SearchPage)
def hybrid(
    request: Request, principal: OptionalPrincipal, params: Annotated[SearchParams, Query()]
) -> SearchPage:
    return standard(request, principal, params.model_copy(update={"mode": "hybrid"}))


@router.get("/autocomplete", response_model=Autocomplete)
def suggestions(
    request: Request,
    q: Annotated[str, Query(max_length=500)],
    limit: Annotated[int, Query(ge=1, le=10)] = 8,
) -> Autocomplete:
    enforce_limit(request, "autocomplete", client_ip(request), 180)
    with Session(request.app.state.db) as db:
        return autocomplete(db, q.strip(), limit)


@router.post("/{search_id}/click", status_code=204, dependencies=mutations)
def click(search_id: UUID, data: SearchClick, request: Request, principal: Reader) -> Response:
    enforce_limit(request, "search-click", str(principal.user.id), 120)
    record_click(
        request.app.state.db,
        request.app.state.settings,
        audit_context(request),
        principal,
        search_id,
        data,
    )
    return Response(status_code=204)
