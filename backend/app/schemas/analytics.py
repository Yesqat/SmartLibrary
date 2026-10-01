from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalyticsDates(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date_from: date | None = None
    date_to: date | None = None


class PeriodRead(BaseModel):
    date_from: date
    date_to: date
    timezone: str
    bucket: Literal["day", "week", "month"]
    generated_at: datetime


class CountPoint(BaseModel):
    date: date
    count: int


class NamedCount(BaseModel):
    key: str
    count: int


class RankedCount(BaseModel):
    id: UUID
    label: str
    count: int


class InventoryAnalytics(BaseModel):
    period: PeriodRead
    book_titles: int
    physical_copies: int
    status: list[NamedCount]
    added_titles: int
    added_copies: int
    additions: list[CountPoint]


class CirculationAnalytics(BaseModel):
    period: PeriodRead
    active_borrowings: int
    overdue_borrowings: int
    active_reservations: int
    waiting_reservations: int
    ready_reservations: int
    issued: int
    returned: int
    lost: int
    reservations_created: int
    reservations_completed: int
    reservations_cancelled: int
    reservations_expired: int
    reservation_completion_rate: float | None
    reservation_cohort_status: list[NamedCount]
    borrowing_trend: list[CountPoint]
    return_trend: list[CountPoint]
    reservation_trend: list[CountPoint]
    popular_books: list[RankedCount]
    popular_categories: list[RankedCount]


class ReaderAnalytics(BaseModel):
    period: PeriodRead
    total_readers: int
    active_reader_accounts: int
    active_readers: int
    new_readers: int
    registrations: list[CountPoint]


class OverviewAnalytics(BaseModel):
    period: PeriodRead
    inventory: InventoryAnalytics
    circulation: CirculationAnalytics
    readers: ReaderAnalytics


class QueryCount(BaseModel):
    query: str
    count: int


class SearchAnalytics(BaseModel):
    period: PeriodRead
    total_searches: int
    zero_result_searches: int
    zero_result_rate: float | None
    modes: list[NamedCount]
    trend: list[CountPoint]
    zero_result_queries: list[QueryCount]


class RecommendationMetric(BaseModel):
    kind: str
    impressions: int
    clicks: int
    ctr: float | None


class AIAnalytics(BaseModel):
    period: PeriodRead
    prediction_runs: int
    predictions: int
    reviewed_predictions: int
    accepted_predictions: int
    prediction_acceptance_rate: float | None
    review_outcomes: list[NamedCount]
    assistant_questions: int
    assistant_successes: int
    assistant_failures: int
    assistant_conversations: int
    assistant_readers: int
    assistant_average_latency_ms: float | None
    input_tokens: int | None
    output_tokens: int | None
    responses_without_usage: int
    assistant_trend: list[CountPoint]
    recommendations: list[RecommendationMetric]
