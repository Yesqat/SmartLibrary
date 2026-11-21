from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import AppError


def unavailable() -> AppError:
    return AppError("AI_SERVICE_UNAVAILABLE", "AI көмекшісі уақытша қолжетімсіз.", 503)


Language = Literal["kk", "ru", "en"]


class AnswerPlan(BaseModel):
    """No free-form library facts: the server renders only validated evidence."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal[
        "results", "clarify_topic", "clarify_language", "clarify_availability", "unsupported"
    ]
    language: Language
    presentation: Literal["search", "recommendation", "details", "availability"]
    book_refs: list[str] = Field(max_length=8, description="Selected books[].ref from this turn.")
    evidence_refs: list[str] = Field(
        max_length=6, description="Tool evidence_ref values from this turn."
    )


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass
class ProviderReply:
    calls: list[ToolCall] = field(default_factory=list)
    answer: AnswerPlan | None = None
    continuation: list[dict[str, Any]] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


class LLMClient(Protocol):
    def respond(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], timeout: float
    ) -> ProviderReply: ...
