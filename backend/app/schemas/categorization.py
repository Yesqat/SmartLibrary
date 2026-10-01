from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.enums import PredictionReview, ScoreKind


class CategorizeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    book_id: UUID
    method: Literal["classical", "embedding"] = "embedding"


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category_ids: list[UUID] = Field(max_length=30)

    @field_validator("category_ids")
    @classmethod
    def unique(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Duplicate category")
        return value


class PredictionRead(BaseModel):
    id: UUID
    category_id: UUID
    name: str
    confidence: float
    score_kind: ScoreKind
    accepted: bool | None


class SelectedCategory(BaseModel):
    id: UUID
    name: str


class PredictionRunRead(BaseModel):
    id: UUID
    book_id: UUID
    book_title: str
    model_name: str
    model_revision: str
    review_status: PredictionReview
    created_at: datetime
    reviewed_at: datetime | None
    reviewed_by: UUID | None
    threshold: float
    predictions: list[PredictionRead]
    selected_categories: list[SelectedCategory]
