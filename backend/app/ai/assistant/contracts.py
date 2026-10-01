from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import AppError


def unavailable() -> AppError:
    return AppError("AI_SERVICE_UNAVAILABLE", "AI көмекшісі уақытша қолжетімсіз.", 503)


class AnswerPlan(BaseModel):
    """No free-form library facts: the server renders only validated evidence."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal[
        "results", "clarify_topic", "clarify_language", "clarify_availability", "unsupported"
    ]
    book_refs: list[str] = Field(max_length=8)
    evidence_refs: list[str] = Field(max_length=6)


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
