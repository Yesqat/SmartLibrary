"""Database aggregation of canonical actions, with daily deduplication of weak signals."""

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Select, case, func, literal, select, union_all
from sqlalchemy.sql.selectable import CTE

from app.ai.recommendations.policy import POLICY, RecommendationPolicy
from app.core.security import now
from app.db.enums import InteractionType
from app.db.models import (
    BookCategory,
    BookCopy,
    Borrowing,
    Category,
    Favorite,
    Reservation,
    UserCategoryPreference,
    UserInteraction,
)


def signals(user_id: UUID | None = None, policy: RecommendationPolicy = POLICY) -> CTE:
    cutoff = now() - timedelta(days=policy.window_days)
    # One weak signal per UTC day/type/user/title limits refresh/click amplification.
    weak = select(
        UserInteraction.book_id,
        case(
            (UserInteraction.interaction_type == InteractionType.VIEW, policy.view),
            else_=policy.click,
        ).label("weight"),
    ).where(
        UserInteraction.created_at >= cutoff,
        UserInteraction.interaction_type.in_(
            [
                InteractionType.VIEW,
                InteractionType.SEARCH_CLICK,
                InteractionType.RECOMMENDATION_CLICK,
            ]
        ),
    )
    if user_id:
        weak = weak.where(UserInteraction.user_id == user_id)
    weak = weak.distinct(
        UserInteraction.user_id,
        UserInteraction.book_id,
        UserInteraction.interaction_type,
        func.date(func.timezone("UTC", UserInteraction.created_at)),
    )
    favorites = select(Favorite.book_id, literal(policy.favorite).label("weight"))
    if user_id:
        favorites = favorites.where(Favorite.user_id == user_id)
    else:
        favorites = favorites.where(Favorite.created_at >= cutoff)
    reserved = select(Reservation.book_id, literal(policy.reserve).label("weight")).where(
        Reservation.reserved_at >= cutoff
    )
    borrowed = (
        select(BookCopy.book_id, literal(policy.borrow).label("weight"))
        .join(Borrowing, Borrowing.book_copy_id == BookCopy.id)
        .where(Borrowing.borrowed_at >= cutoff)
    )
    if user_id:
        reserved = reserved.where(Reservation.user_id == user_id)
        borrowed = borrowed.where(Borrowing.user_id == user_id)
    rows = union_all(weak, favorites, reserved, borrowed).cte("signal_rows")
    return (
        select(rows.c.book_id, func.sum(rows.c.weight).label("weight"))
        .group_by(rows.c.book_id)
        .cte("signals")
    )


def preferences(user_id: UUID) -> CTE:
    return (
        select(BookCategory.book_id, func.sum(UserCategoryPreference.weight).label("weight"))
        .join(
            UserCategoryPreference, UserCategoryPreference.category_id == BookCategory.category_id
        )
        .join(Category, Category.id == BookCategory.category_id)
        .where(UserCategoryPreference.user_id == user_id, Category.archived_at.is_(None))
        .group_by(BookCategory.book_id)
        .cte("preferences")
    )


def consumed(user_id: UUID) -> Select[Any]:
    return select(BookCopy.book_id).join(Borrowing).where(Borrowing.user_id == user_id)
