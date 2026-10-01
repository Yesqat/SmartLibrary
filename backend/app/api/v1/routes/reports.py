import logging

from fastapi import APIRouter, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.routes.admin import MonitoringAdmin
from app.api.v1.routes.catalog import mutations
from app.core.auth_http import audit_context
from app.core.errors import AppError
from app.core.permissions import Permission, authorize
from app.core.rate_limit import consume
from app.schemas.auth import ErrorResponse
from app.schemas.reports import ReportInput
from app.services.analytics.definitions import period
from app.services.audit.events import record
from app.services.auth.service import AuthService
from app.services.reports.data import collect
from app.services.reports.render import pdf, spreadsheet

MIME = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
router = APIRouter(
    prefix="/api/v1/admin/reports",
    tags=["Reports"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 422, 429, 503)},
)


@router.post(
    "",
    response_class=Response,
    dependencies=mutations,
    responses={
        200: {
            "description": "Private structured report download",
            "content": {
                value: {"schema": {"type": "string", "format": "binary"}} for value in MIME.values()
            },
        }
    },
)
def generate(data: ReportInput, request: Request, principal: MonitoringAdmin) -> Response:
    consume(request, "reports", str(principal.user.id), 6, 60)
    window = period(data, request.app.state.settings.library_timezone)
    try:
        with Session(request.app.state.db) as db, db.begin():
            db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            db.execute(text("SET LOCAL statement_timeout = '15s'"))
            report = collect(
                db, data, window, f"{principal.user.first_name} {principal.user.last_name}"
            )
        content = pdf(report) if data.format == "pdf" else spreadsheet(report)
    except AppError:
        raise
    except Exception as exc:
        logging.getLogger(__name__).error(
            "report_generation_failed", extra={"exception_type": type(exc).__name__}
        )
        raise AppError(
            "REPORT_GENERATION_FAILED", "Есепті жасау мүмкін болмады. Қайта көріңіз.", 503
        ) from None
    # Rendering happens without row locks; re-check privilege/session before release.
    with Session(request.app.state.db) as db, db.begin():
        user = AuthService(
            request.app.state.db, request.app.state.settings, audit_context(request)
        ).require_live(db, principal.user.id, principal.family_id)
        authorize(user.role, Permission.VIEW_ANALYTICS)
        record(
            db,
            "REPORT_GENERATED",
            audit_context(request),
            user.id,
            reason=f"{data.report_type}:{data.format}:{len(report.rows)}",
            entity_type="REPORT",
        )
    name = (
        f"smartlibrary_{data.report_type}_"
        f"{window.meta.date_from}_{window.meta.date_to}.{data.format}"
    )
    return Response(
        content,
        media_type=MIME[data.format],
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Report-Rows": str(len(report.rows)),
        },
    )
