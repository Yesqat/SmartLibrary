from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.routes.admin import MonitoringAdmin
from app.core.rate_limit import consume
from app.schemas.analytics import (
    AIAnalytics,
    AnalyticsDates,
    CirculationAnalytics,
    InventoryAnalytics,
    OverviewAnalytics,
    ReaderAnalytics,
    SearchAnalytics,
)
from app.schemas.auth import ErrorResponse
from app.services.analytics.ai import ai_metrics, search_metrics
from app.services.analytics.catalog import inventory, readers
from app.services.analytics.circulation import circulation
from app.services.analytics.definitions import Period, period

router = APIRouter(
    prefix="/api/v1/admin/analytics",
    tags=["Analytics"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 422, 429, 503)},
)


def snapshot(
    request: Request, principal: MonitoringAdmin, dates: Annotated[AnalyticsDates, Query()]
) -> Iterator[tuple[Session, Period]]:
    consume(request, "analytics", str(principal.user.id), 60, 60)
    window = period(dates, request.app.state.settings.library_timezone)
    with Session(request.app.state.db) as db, db.begin():
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        db.execute(text("SET LOCAL statement_timeout = '10s'"))
        yield db, window


Snapshot = Annotated[tuple[Session, Period], Depends(snapshot)]


@router.get("/overview", response_model=OverviewAnalytics)
def overview(data: Snapshot) -> OverviewAnalytics:
    db, window = data
    return OverviewAnalytics(
        period=window.meta,
        inventory=inventory(db, window),
        circulation=circulation(db, window),
        readers=readers(db, window),
    )


@router.get("/circulation", response_model=CirculationAnalytics)
def circulation_view(data: Snapshot) -> CirculationAnalytics:
    return circulation(*data)


@router.get("/inventory", response_model=InventoryAnalytics)
def inventory_view(data: Snapshot) -> InventoryAnalytics:
    return inventory(*data)


@router.get("/readers", response_model=ReaderAnalytics)
def reader_view(data: Snapshot) -> ReaderAnalytics:
    return readers(*data)


@router.get("/search", response_model=SearchAnalytics)
def search_view(data: Snapshot) -> SearchAnalytics:
    return search_metrics(*data)


@router.get("/ai", response_model=AIAnalytics)
def ai_view(data: Snapshot) -> AIAnalytics:
    return ai_metrics(*data)
