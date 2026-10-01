"""Reader preferences, deduplicated notifications and attributable analytics events."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Created, Identity
from app.db.enums import (
    InteractionSource,
    InteractionType,
    NotificationType,
    RecommendationType,
    RelatedEntity,
    SearchType,
)


class Favorite(Identity, Created, Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "book_id"),)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)


class UserCategoryPreference(Identity, Created, Base):
    __tablename__ = "user_category_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id"),
        CheckConstraint("weight >= 0 AND weight < 'Infinity'::numeric", name="weight"),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    weight: Mapped[float] = mapped_column(Numeric(8, 4, asdecimal=False), server_default="1")


class SearchEvent(Identity, Created, Base):
    __tablename__ = "search_events"
    __table_args__ = (
        CheckConstraint("length(btrim(query)) > 0", name="query"),
        CheckConstraint("result_count >= 0", name="result_count"),
        CheckConstraint("jsonb_typeof(filters) = 'object'", name="filters_object"),
        Index("ix_search_events_type_time", "search_type", "created_at"),
        Index("ix_search_events_time", "created_at"),
        Index(
            "ix_search_events_zero_results", "created_at", postgresql_where=text("result_count = 0")
        ),
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    query: Mapped[str] = mapped_column(String(2000))
    search_type: Mapped[SearchType] = mapped_column(Enum(SearchType, name="search_type"))
    result_count: Mapped[int]
    filters: Mapped[dict[str, object]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class RecommendationImpression(Identity, Base):
    __tablename__ = "recommendation_impressions"
    __table_args__ = (
        UniqueConstraint("id", "user_id", "book_id", name="uq_recommendation_impressions_identity"),
        CheckConstraint("position >= 1", name="position"),
        CheckConstraint("length(btrim(event_key)) > 0", name="event_key"),
        Index("ix_recommendation_impressions_type_time", "recommendation_type", "shown_at"),
        Index("ix_recommendation_impressions_user_time", "user_id", "shown_at"),
        Index("ix_recommendation_impressions_time", "shown_at"),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="RESTRICT"), index=True)
    recommendation_type: Mapped[RecommendationType] = mapped_column(
        Enum(RecommendationType, name="recommendation_type")
    )
    source: Mapped[InteractionSource] = mapped_column(
        Enum(InteractionSource, name="interaction_source")
    )
    shown_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    position: Mapped[int]
    event_key: Mapped[str] = mapped_column(String(150), unique=True)
    model_name: Mapped[str | None] = mapped_column(String(250))


class UserInteraction(Identity, Created, Base):
    __tablename__ = "user_interactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["recommendation_impression_id", "user_id", "book_id"],
            [
                "recommendation_impressions.id",
                "recommendation_impressions.user_id",
                "recommendation_impressions.book_id",
            ],
            ondelete="RESTRICT",
            name="fk_user_interactions_impression_owner_book",
        ),
        CheckConstraint(
            "interaction_type <> 'RECOMMENDATION_CLICK' OR "
            "(recommendation_impression_id IS NOT NULL AND source IN "
            "('RECOMMENDATION','SIMILAR_BOOKS','POPULAR_BOOKS'))",
            name="click_attribution",
        ),
        Index(
            "uq_user_interactions_impression_click",
            "recommendation_impression_id",
            unique=True,
            postgresql_where=text("interaction_type = 'RECOMMENDATION_CLICK'"),
        ),
        Index("ix_user_interactions_user_time", "user_id", "created_at"),
        Index("ix_user_interactions_book_time", "book_id", "created_at"),
        Index("ix_user_interactions_type_time", "interaction_type", "created_at"),
        Index("ix_user_interactions_time", "created_at"),
        Index("ix_user_interactions_impression", "recommendation_impression_id"),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="RESTRICT"))
    interaction_type: Mapped[InteractionType] = mapped_column(
        Enum(InteractionType, name="interaction_type")
    )
    source: Mapped[InteractionSource] = mapped_column(
        Enum(InteractionSource, name="interaction_source")
    )
    search_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("search_events.id", ondelete="RESTRICT"), index=True
    )
    recommendation_impression_id: Mapped[UUID | None]
    event_key: Mapped[str | None] = mapped_column(String(150), unique=True)


class Notification(Identity, Created, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "event_key"),
        ForeignKeyConstraint(
            ["reservation_id", "user_id"],
            ["reservations.id", "reservations.user_id"],
            ondelete="RESTRICT",
            name="fk_notifications_reservation_owner",
        ),
        ForeignKeyConstraint(
            ["borrowing_id", "user_id"],
            ["borrowings.id", "borrowings.user_id"],
            ondelete="RESTRICT",
            name="fk_notifications_borrowing_owner",
        ),
        CheckConstraint(
            "length(btrim(title)) > 0 AND length(btrim(message)) > 0 "
            "AND length(btrim(event_key)) > 0",
            name="content",
        ),
        CheckConstraint(
            "(related_entity_type = 'RESERVATION' AND reservation_id IS NOT NULL "
            "AND borrowing_id IS NULL AND book_id IS NULL) OR "
            "(related_entity_type = 'BORROWING' AND borrowing_id IS NOT NULL "
            "AND reservation_id IS NULL AND book_id IS NULL) OR "
            "(related_entity_type = 'BOOK' AND book_id IS NOT NULL "
            "AND borrowing_id IS NULL AND reservation_id IS NULL)",
            name="entity_reference",
        ),
        Index("ix_notifications_user_read_time", "user_id", "is_read", "created_at"),
        Index("ix_notifications_reservation", "reservation_id"),
        Index("ix_notifications_borrowing", "borrowing_id"),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"))
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    event_key: Mapped[str] = mapped_column(String(200))
    related_entity_type: Mapped[RelatedEntity] = mapped_column(
        Enum(RelatedEntity, name="related_entity")
    )
    related_entity_id: Mapped[UUID] = mapped_column(
        Computed("coalesce(reservation_id, borrowing_id, book_id)", persisted=True)
    )
    reservation_id: Mapped[UUID | None]
    borrowing_id: Mapped[UUID | None]
    book_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("books.id", ondelete="RESTRICT"), index=True
    )
