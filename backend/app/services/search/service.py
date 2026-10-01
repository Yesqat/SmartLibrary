"""Search event measurement and click attribution share real retrieval results."""

from uuid import UUID

from sqlalchemy import Engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.ai.embeddings.search import semantic_search
from app.api.dependencies import Principal
from app.core.config import Settings
from app.core.errors import AppError
from app.core.permissions import Permission, authorize
from app.db.enums import InteractionSource, InteractionType, SearchType
from app.db.models.engagement import SearchEvent, UserInteraction
from app.repositories.search import standard_search
from app.schemas.search import SearchClick, SearchPage, SearchParams
from app.services.audit.events import AuditContext
from app.services.auth.service import AuthService


def search(
    db: Session, params: SearchParams, principal: Principal | None, settings: Settings | None = None
) -> SearchPage:
    if params.mode != "standard" and params.q:
        if settings is None:
            raise AppError(
                "SEMANTIC_SEARCH_UNAVAILABLE", "Мағыналық іздеу әзірге қолжетімсіз.", 503
            )
        result = semantic_search(db, settings, params)
    else:
        result = standard_search(db, params)
    if params.q:
        event = SearchEvent(
            user_id=principal.user.id if principal else None,
            query=params.q,
            search_type=SearchType(params.mode.upper()),
            result_count=result.total,
            filters={
                **params.model_dump(mode="json", exclude={"q"}),
                "result_ids": [str(book.id) for book in result.items],
            },
        )
        db.add(event)
        db.flush()
        result.search_event_id = event.id
    return result


def record_click(
    engine: Engine,
    settings: Settings,
    context: AuditContext,
    principal: Principal,
    search_id: UUID,
    data: SearchClick,
) -> None:
    with Session(engine) as db, db.begin():
        user = AuthService(engine, settings, context).require_live(
            db, principal.user.id, principal.family_id
        )
        authorize(user.role, Permission.READ_PERSONAL)
        event = db.get(SearchEvent, search_id)
        result_ids = event.filters.get("result_ids") if event else None
        if (
            event is None
            or event.user_id != user.id
            or not isinstance(result_ids, list)
            or str(data.book_id) not in result_ids
        ):
            raise AppError("NOT_FOUND", "Іздеу нәтижесі табылмады.", 404)
        db.execute(
            insert(UserInteraction)
            .values(
                user_id=user.id,
                book_id=data.book_id,
                interaction_type=InteractionType.SEARCH_CLICK,
                source=InteractionSource(event.search_type.value + "_SEARCH"),
                search_event_id=event.id,
                event_key=f"search-click:{user.id}:{data.event_id}",
            )
            .on_conflict_do_nothing(index_elements=["event_key"])
        )
