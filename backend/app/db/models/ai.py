"""Versioned vector spaces, human category review and owned AI conversation history."""

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Created, Identity, Updated
from app.db.enums import MessageRole, PredictionReview, ScoreKind
from app.db.models.catalog import Book


class EmbeddingModel(Identity, Created, Base):
    __tablename__ = "embedding_models"
    __table_args__ = (
        UniqueConstraint(
            "model_name", "revision", "source_recipe", name="uq_embedding_models_space"
        ),
        UniqueConstraint("id", "dimension", name="uq_embedding_models_dimension"),
        CheckConstraint("dimension BETWEEN 1 AND 16000", name="dimension"),
        CheckConstraint(
            "length(btrim(model_name)) > 0 AND length(btrim(revision)) > 0 "
            "AND length(btrim(source_recipe)) > 0",
            name="provenance",
        ),
        CheckConstraint("jsonb_typeof(configuration) = 'object'", name="configuration"),
    )
    model_name: Mapped[str] = mapped_column(String(250))
    revision: Mapped[str] = mapped_column(String(150))
    dimension: Mapped[int]
    source_recipe: Mapped[str] = mapped_column(String(100))
    normalized: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    configuration: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )


class BookEmbedding(Identity, Base):
    __tablename__ = "book_embeddings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["model_id", "dimension"],
            ["embedding_models.id", "embedding_models.dimension"],
            ondelete="RESTRICT",
            name="fk_book_embeddings_model_dimension",
        ),
        UniqueConstraint("book_id", "model_id"),
        CheckConstraint("vector_dims(embedding) = dimension", name="dimension"),
        CheckConstraint("vector_norm(embedding) > 0", name="nonzero_vector"),
        CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="source_hash"),
        Index("ix_book_embeddings_model", "model_id", "book_id"),
    )
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    model_id: Mapped[UUID]
    dimension: Mapped[int]
    # Dimensions are enforced against the immutable model space, not an unbenchmarked constant.
    embedding: Mapped[list[float]] = mapped_column(Vector())
    source_hash: Mapped[str] = mapped_column(String(64))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    model: Mapped[EmbeddingModel] = relationship(lazy="raise")


class CategoryPredictionRun(Identity, Created, Base):
    __tablename__ = "category_prediction_runs"
    __table_args__ = (
        UniqueConstraint("id", "book_id", name="uq_category_prediction_runs_identity_book"),
        CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="source_hash"),
        CheckConstraint("jsonb_typeof(configuration) = 'object'", name="configuration"),
        CheckConstraint(
            "(review_status = 'PENDING' AND reviewed_by IS NULL AND reviewed_at IS NULL) OR "
            "(review_status <> 'PENDING' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL "
            "AND reviewed_at >= created_at)",
            name="review",
        ),
        Index("ix_category_prediction_runs_review_time", "review_status", "created_at"),
        Index("ix_category_prediction_runs_created", "created_at"),
        Index(
            "ix_category_prediction_runs_reviewed",
            "reviewed_at",
            postgresql_where=text("reviewed_at IS NOT NULL"),
        ),
    )
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="RESTRICT"), index=True)
    requested_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    model_name: Mapped[str] = mapped_column(String(250))
    model_revision: Mapped[str] = mapped_column(String(150))
    source_hash: Mapped[str] = mapped_column(String(64))
    configuration: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    review_status: Mapped[PredictionReview] = mapped_column(
        Enum(PredictionReview, name="prediction_review"), server_default="PENDING"
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CategoryPrediction(Identity, Created, Base):
    __tablename__ = "category_predictions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "book_id"],
            ["category_prediction_runs.id", "category_prediction_runs.book_id"],
            ondelete="RESTRICT",
            name="fk_category_predictions_run_book",
        ),
        UniqueConstraint("run_id", "category_id"),
        CheckConstraint(
            "confidence > '-Infinity'::float8 AND confidence < 'Infinity'::float8 "
            "AND (score_kind = 'DECISION_FUNCTION' OR "
            "(score_kind = 'PROBABILITY' AND confidence BETWEEN 0 AND 1) OR "
            "(score_kind = 'COSINE_SIMILARITY' AND confidence BETWEEN -1 AND 1))",
            name="score",
        ),
        CheckConstraint(
            "(accepted IS NULL AND reviewed_by IS NULL AND reviewed_at IS NULL) OR "
            "(accepted IS NOT NULL AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL "
            "AND reviewed_at >= created_at)",
            name="review",
        ),
        Index("ix_category_predictions_review_time", "accepted", "created_at"),
        Index("ix_category_predictions_created", "created_at"),
        Index(
            "ix_category_predictions_reviewed",
            "reviewed_at",
            postgresql_where=text("reviewed_at IS NOT NULL"),
        ),
    )
    run_id: Mapped[UUID]
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="RESTRICT"), index=True)
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    confidence: Mapped[float] = mapped_column(Float)
    score_kind: Mapped[ScoreKind] = mapped_column(Enum(ScoreKind, name="score_kind"))
    accepted: Mapped[bool | None]
    reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run: Mapped[CategoryPredictionRun] = relationship(lazy="raise")


class CategoryPredictionSelection(Identity, Base):
    """The reviewed set, including manually added categories, retained for set-level metrics."""

    __tablename__ = "category_prediction_selections"
    __table_args__ = (UniqueConstraint("run_id", "category_id"),)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("category_prediction_runs.id", ondelete="RESTRICT")
    )
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )


class AIConversation(Identity, Updated, Base):
    __tablename__ = "ai_conversations"
    __table_args__ = (Index("ix_ai_conversations_user_updated", "user_id", "updated_at"),)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    title: Mapped[str | None] = mapped_column(String(300))
    messages: Mapped[list["AIMessage"]] = relationship(
        back_populates="conversation", lazy="raise", passive_deletes="all"
    )


class AIMessage(Identity, Created, Base):
    __tablename__ = "ai_messages"
    __table_args__ = (
        CheckConstraint("length(btrim(content)) > 0", name="content"),
        CheckConstraint("jsonb_typeof(tool_metadata) = 'object'", name="tool_metadata"),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="latency"),
        CheckConstraint("input_tokens IS NULL OR input_tokens >= 0", name="input_tokens"),
        CheckConstraint("output_tokens IS NULL OR output_tokens >= 0", name="output_tokens"),
        Index("ix_ai_messages_conversation_time", "conversation_id", "created_at", "id"),
        Index("ix_ai_messages_role_time", "role", "created_at"),
    )
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_conversations.id", ondelete="CASCADE")
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(Text)
    tool_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    model_name: Mapped[str | None] = mapped_column(String(250))
    latency_ms: Mapped[int | None]
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    error_code: Mapped[str | None] = mapped_column(String(100))
    conversation: Mapped[AIConversation] = relationship(back_populates="messages", lazy="raise")
    books: Mapped[list[Book]] = relationship(
        secondary="ai_message_books", lazy="raise", viewonly=True
    )


class AIMessageBook(Identity, Base):
    """Structured assistant book references must identify actual catalog records."""

    __tablename__ = "ai_message_books"
    __table_args__ = (
        UniqueConstraint("message_id", "book_id"),
        UniqueConstraint("message_id", "position", name="uq_ai_message_books_position"),
        CheckConstraint("position >= 1", name="position"),
    )
    message_id: Mapped[UUID] = mapped_column(ForeignKey("ai_messages.id", ondelete="CASCADE"))
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="RESTRICT"), index=True)
    position: Mapped[int]
