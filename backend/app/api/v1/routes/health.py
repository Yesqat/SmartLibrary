from fastapi import APIRouter, Request, Response

from app.schemas.health import Liveness, Readiness
from app.services.health import readiness

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=Liveness, summary="Process liveness")
def live() -> Liveness:
    return Liveness()


@router.get(
    "/ready",
    response_model=Readiness,
    responses={503: {"model": Readiness}},
    summary="PostgreSQL and Redis readiness",
)
def ready(request: Request, response: Response) -> Readiness:
    result = readiness(request.app.state.db, request.app.state.redis)
    if result.status != "ready":
        response.status_code = 503
    response.headers["Cache-Control"] = "no-store"
    return result
