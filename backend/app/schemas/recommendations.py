from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import RecommendationType
from app.schemas.catalog import BookRead

Reason = Literal["popular", "similar", "history", "preferences", "recent"]


class RecommendationItem(BaseModel):
    book: BookRead
    reason: Reason


class RecommendationPage(BaseModel):
    items: list[RecommendationItem]
    recommendation_type: RecommendationType
    receipt: str | None = None
    content_available: bool = False
    indexing_pending: bool = False


class ImpressionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    receipt: str = Field(min_length=20, max_length=10000, repr=False)
    book_id: UUID


class ImpressionRead(BaseModel):
    id: UUID
