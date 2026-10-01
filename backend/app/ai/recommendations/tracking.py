"""Signed returned-card receipts; impressions are recorded only after a render signal."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.ai.recommendations.policy import POLICY
from app.api.dependencies import Principal
from app.core.config import Settings
from app.core.errors import AppError
from app.core.permissions import Permission, authorize
from app.core.security import now
from app.db.enums import InteractionSource, InteractionType, RecommendationType, UserRole
from app.db.models import RecommendationImpression, UserInteraction
from app.schemas.recommendations import ImpressionInput, RecommendationPage
from app.services.audit.events import AuditContext
from app.services.auth.service import AuthService

SOURCES = {
    RecommendationType.POPULAR: InteractionSource.POPULAR_BOOKS,
    RecommendationType.SIMILAR_BOOK: InteractionSource.SIMILAR_BOOKS,
    RecommendationType.PERSONALIZED: InteractionSource.RECOMMENDATION,
}


def signature(settings: Settings, body: str) -> str:
    key = hmac.digest(
        settings.jwt_secret.get_secret_value().encode(), b"recommendations-v1", "sha256"
    )
    return hmac.new(key, body.encode(), hashlib.sha256).hexdigest()


def offer(
    settings: Settings, principal: Principal | None, result: RecommendationPage
) -> RecommendationPage:
    if principal is None or principal.user.role != UserRole.READER or not result.items:
        return result
    issued = int(time.time())
    claims = {
        "user": str(principal.user.id),
        "family": str(principal.family_id),
        "id": str(uuid4()),
        "issued": issued,
        "expires": issued + 1800,
        "books": [str(item.book.id) for item in result.items],
        "kind": result.recommendation_type.value,
        "model": POLICY.version,
    }
    body = base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode()).decode()
    result.receipt = body + "." + signature(settings, body)
    return result


def read_offer(settings: Settings, principal: Principal, data: ImpressionInput) -> dict[str, Any]:
    try:
        body, signed = data.receipt.split(".")
        if not hmac.compare_digest(signature(settings, body), signed):
            raise ValueError
        claims = json.loads(base64.urlsafe_b64decode(body))
        if (
            claims["user"] != str(principal.user.id)
            or claims["family"] != str(principal.family_id)
            or not claims["issued"] <= int(time.time()) < claims["expires"]
            or str(data.book_id) not in claims["books"]
        ):
            raise ValueError
        RecommendationType(claims["kind"])
        UUID(claims["id"])
        return dict(claims)
    except (ValueError, TypeError, KeyError):
        raise AppError("INVALID_RECOMMENDATION", "Ұсынысты жаңартыңыз.", 422) from None


def impression(
    engine: Engine, settings: Settings, principal: Principal, data: ImpressionInput
) -> UUID:
    claims = read_offer(settings, principal, data)
    kind = RecommendationType(claims["kind"])
    event_key = f"recommendation:{claims['id']}:{data.book_id}"
    with Session(engine) as db, db.begin():
        user = AuthService(engine, settings, AuditContext()).require_live(
            db, principal.user.id, principal.family_id
        )
        authorize(user.role, Permission.READ_PERSONAL)
        db.execute(
            insert(RecommendationImpression)
            .values(
                user_id=user.id,
                book_id=data.book_id,
                recommendation_type=kind,
                source=SOURCES[kind],
                shown_at=now(),
                position=claims["books"].index(str(data.book_id)) + 1,
                event_key=event_key,
                model_name=claims["model"],
            )
            .on_conflict_do_nothing(index_elements=["event_key"])
        )
        identity = db.scalar(
            select(RecommendationImpression.id).where(
                RecommendationImpression.event_key == event_key
            )
        )
        assert identity is not None
        return identity


def click(engine: Engine, settings: Settings, principal: Principal, identity: UUID) -> None:
    with Session(engine) as db, db.begin():
        user = AuthService(engine, settings, AuditContext()).require_live(
            db, principal.user.id, principal.family_id
        )
        authorize(user.role, Permission.READ_PERSONAL)
        row = db.get(RecommendationImpression, identity)
        if row is None or row.user_id != user.id:
            raise AppError("NOT_FOUND", "Ұсыныс табылмады.", 404)
        db.execute(
            insert(UserInteraction)
            .values(
                user_id=user.id,
                book_id=row.book_id,
                interaction_type=InteractionType.RECOMMENDATION_CLICK,
                source=row.source,
                recommendation_impression_id=row.id,
                event_key=f"recommendation-click:{row.id}",
            )
            .on_conflict_do_nothing()
        )
