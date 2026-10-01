import logging
import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from redis import Redis
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint

from app.api.v1.routes.admin import router as admin_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.assistant import router as assistant_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.borrowings import router as borrowings_router
from app.api.v1.routes.catalog import router as catalog_router
from app.api.v1.routes.categorization import router as categorization_router
from app.api.v1.routes.circulation import router as circulation_router
from app.api.v1.routes.health import router
from app.api.v1.routes.librarian import router as librarian_router
from app.api.v1.routes.reader import router as reader_router
from app.api.v1.routes.recommendations import router as recommendations_router
from app.api.v1.routes.reports import router as reports_router
from app.api.v1.routes.reservations import router as reservations_router
from app.api.v1.routes.search import router as search_router
from app.api.v1.routes.taxonomy import router as taxonomy_router
from app.core.config import Settings, get_settings
from app.core.errors import (
    AppError,
    application_error,
    error_response,
    http_error,
    validation_error,
)
from app.core.logging import configure_logging
from app.db.session import create_db_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.db = create_db_engine(settings)
        app.state.redis = Redis.from_url(
            settings.redis_dsn, socket_connect_timeout=3, socket_timeout=3
        )
        try:
            yield
        finally:
            app.state.redis.close()
            app.state.db.dispose()

    app = FastAPI(
        title="SmartLibrary API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
    )
    app.state.settings = settings
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(AppError, application_error)

    @app.middleware("http")
    async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            logging.getLogger("smartlibrary").error(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "error_type": type(exc).__name__,
                    "error_frames": [
                        f"{frame.name}:{frame.lineno}"
                        for frame in traceback.extract_tb(exc.__traceback__)[-8:]
                    ],
                    "sqlstate": getattr(getattr(exc, "orig", None), "sqlstate", None),
                },
            )
            response = error_response("INTERNAL_ERROR", "Ішкі қате пайда болды.", 500)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.headers.get("authorization") or request.url.path.startswith(
            (
                "/api/v1/auth",
                "/api/v1/reservations",
                "/api/v1/librarian",
                "/api/v1/borrowings",
                "/api/v1/favorites",
                "/api/v1/notifications",
                "/api/v1/reader",
                "/api/v1/users",
                "/api/v1/admin",
                "/api/v1/recommendations",
                "/api/v1/ai",
            )
        ):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        route = getattr(request.scope.get("route"), "path", "unmatched")
        logging.getLogger("smartlibrary").info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "route": route,
                "status": response.status_code,
                "duration_ms": round((perf_counter() - start) * 1000, 2),
            },
        )
        return response

    app.include_router(router)
    app.include_router(router, prefix="/api/v1")
    app.include_router(auth_router)
    app.include_router(recommendations_router)
    app.include_router(catalog_router)
    app.include_router(taxonomy_router)
    app.include_router(search_router)
    app.include_router(reservations_router)
    app.include_router(circulation_router)
    app.include_router(borrowings_router)
    app.include_router(reader_router)
    app.include_router(librarian_router)
    app.include_router(admin_router)
    app.include_router(categorization_router)
    app.include_router(assistant_router)
    app.include_router(analytics_router)
    app.include_router(reports_router)
    return app
