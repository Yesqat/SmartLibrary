import json
import time
from dataclasses import dataclass
from typing import Any

from app.ai.assistant.contracts import LLMClient, unavailable
from app.ai.assistant.rendering import render
from app.ai.assistant.tools import ToolContext, definitions
from app.schemas.catalog import BookRead


@dataclass
class Answer:
    content: str
    books: list[BookRead]
    kind: str
    input_tokens: int
    output_tokens: int


def respond(client: LLMClient, context: ToolContext, history: list[dict[str, Any]]) -> Answer:
    deadline = time.monotonic() + 60
    input_tokens = output_tokens = 0
    call_ids: set[str] = set()
    for _ in range(4):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise unavailable()
        reply = client.respond(history, definitions(), min(20, remaining))
        input_tokens += reply.input_tokens
        output_tokens += reply.output_tokens
        if time.monotonic() > deadline:
            raise unavailable()
        if reply.calls:
            if reply.answer or len(reply.calls) > 3:
                raise unavailable()
            history.extend(reply.continuation)
            for call in reply.calls:
                if call.id in call_ids or not call.id or len(call.id) > 200:
                    raise unavailable()
                call_ids.add(call.id)
                result = context.execute(call.name, call.arguments)
                history.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
            continue
        plan = reply.answer
        if plan is None:
            raise unavailable()
        # A provider may select the public UUID used by the detail tool instead of
        # its presentation reference. Both must resolve to a book read in this turn.
        current_ids = {str(book.id): ref for ref, book in context.books.items()}
        selected = [current_ids.get(ref, ref) for ref in plan.book_refs]
        if any(ref not in context.books for ref in selected) or any(
            ref not in context.results for ref in plan.evidence_refs
        ):
            raise unavailable()
        if plan.kind == "results":
            if not plan.book_refs and not plan.evidence_refs:
                raise unavailable()
        elif plan.book_refs or plan.evidence_refs:
            raise unavailable()
        content, books = render(plan.model_copy(update={"book_refs": selected}), context)
        return Answer(content, books, plan.kind, input_tokens, output_tokens)
    raise unavailable()
