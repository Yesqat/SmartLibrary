from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.enums import (
    InteractionType,
    MessageRole,
    PredictionReview,
    RecommendationType,
    SearchType,
)
from app.db.models import (
    AIConversation,
    AIMessage,
    CategoryPrediction,
    CategoryPredictionRun,
    RecommendationImpression,
    SearchEvent,
    UserInteraction,
)
from app.schemas.analytics import (
    AIAnalytics,
    NamedCount,
    QueryCount,
    RecommendationMetric,
    SearchAnalytics,
)
from app.services.analytics.definitions import Period, count, percentage, series


def search_metrics(db: Session, window: Period) -> SearchAnalytics:
    modes: dict[SearchType, int] = dict(
        db.execute(
            select(SearchEvent.search_type, func.count())
            .where(window.contains(SearchEvent.created_at))
            .group_by(SearchEvent.search_type)
        )
        .tuples()
        .all()
    )
    total = sum(modes.values())
    zero = count(
        db, SearchEvent, window.contains(SearchEvent.created_at), SearchEvent.result_count == 0
    )
    queries = db.execute(
        select(SearchEvent.query, func.count())
        .where(window.contains(SearchEvent.created_at), SearchEvent.result_count == 0)
        .group_by(SearchEvent.query)
        .order_by(func.count().desc(), SearchEvent.query)
        .limit(15)
    )
    return SearchAnalytics(
        period=window.meta,
        total_searches=total,
        zero_result_searches=zero,
        zero_result_rate=percentage(zero, total),
        modes=[NamedCount(key=mode.value, count=modes.get(mode, 0)) for mode in SearchType],
        trend=series(db, SearchEvent, SearchEvent.created_at, window),
        zero_result_queries=[QueryCount(query=q, count=n) for q, n in queries],
    )


def recommendations(db: Session, window: Period) -> list[RecommendationMetric]:
    counts: dict[RecommendationType, int] = dict(
        db.execute(
            select(RecommendationImpression.recommendation_type, func.count())
            .where(window.contains(RecommendationImpression.shown_at))
            .group_by(RecommendationImpression.recommendation_type)
        )
        .tuples()
        .all()
    )
    clicks: dict[RecommendationType, int] = dict(
        db.execute(
            select(
                RecommendationImpression.recommendation_type,
                func.count(func.distinct(RecommendationImpression.id)),
            )
            .join(
                UserInteraction,
                UserInteraction.recommendation_impression_id == RecommendationImpression.id,
            )
            .where(
                window.contains(RecommendationImpression.shown_at),
                UserInteraction.interaction_type == InteractionType.RECOMMENDATION_CLICK,
                UserInteraction.created_at <= window.meta.generated_at,
            )
            .group_by(RecommendationImpression.recommendation_type)
        )
        .tuples()
        .all()
    )
    return [
        RecommendationMetric(
            kind=kind.value,
            impressions=counts.get(kind, 0),
            clicks=clicks.get(kind, 0),
            ctr=percentage(clicks.get(kind, 0), counts.get(kind, 0)),
        )
        for kind in RecommendationType
    ]


def ai_metrics(db: Session, window: Period) -> AIAnalytics:
    reviewed = count(db, CategoryPrediction, window.contains(CategoryPrediction.reviewed_at))
    accepted = count(
        db,
        CategoryPrediction,
        window.contains(CategoryPrediction.reviewed_at),
        CategoryPrediction.accepted.is_(True),
    )
    outcomes: dict[PredictionReview, int] = dict(
        db.execute(
            select(CategoryPredictionRun.review_status, func.count())
            .where(window.contains(CategoryPredictionRun.reviewed_at))
            .group_by(CategoryPredictionRun.review_status)
        )
        .tuples()
        .all()
    )
    responses = [window.contains(AIMessage.created_at), AIMessage.role == MessageRole.ASSISTANT]
    usage = db.execute(
        select(
            func.avg(AIMessage.latency_ms),
            func.sum(AIMessage.input_tokens),
            func.sum(AIMessage.output_tokens),
        ).where(*responses)
    ).one()
    owners = db.execute(
        select(
            func.count(func.distinct(AIMessage.conversation_id)),
            func.count(func.distinct(AIConversation.user_id)),
        )
        .join(AIConversation, AIMessage.conversation_id == AIConversation.id)
        .where(window.contains(AIMessage.created_at), AIMessage.role == MessageRole.USER)
    ).one()
    return AIAnalytics(
        period=window.meta,
        prediction_runs=count(
            db, CategoryPredictionRun, window.contains(CategoryPredictionRun.created_at)
        ),
        predictions=count(db, CategoryPrediction, window.contains(CategoryPrediction.created_at)),
        reviewed_predictions=reviewed,
        accepted_predictions=accepted,
        prediction_acceptance_rate=percentage(accepted, reviewed),
        review_outcomes=[
            NamedCount(key=state.value, count=outcomes.get(state, 0))
            for state in PredictionReview
            if state != PredictionReview.PENDING
        ],
        assistant_questions=count(
            db, AIMessage, window.contains(AIMessage.created_at), AIMessage.role == MessageRole.USER
        ),
        assistant_successes=count(db, AIMessage, *responses, AIMessage.error_code.is_(None)),
        assistant_failures=count(db, AIMessage, *responses, AIMessage.error_code.is_not(None)),
        assistant_conversations=owners[0],
        assistant_readers=owners[1],
        assistant_average_latency_ms=float(usage[0]) if usage[0] is not None else None,
        input_tokens=usage[1],
        output_tokens=usage[2],
        responses_without_usage=count(db, AIMessage, *responses, AIMessage.input_tokens.is_(None)),
        assistant_trend=series(
            db, AIMessage, AIMessage.created_at, window, AIMessage.role == MessageRole.USER
        ),
        recommendations=recommendations(db, window),
    )
