"""Exercise the reader endpoint through Groq tool calling with a real catalog."""

import json
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.db.enums import UserRole
from app.db.models import AIMessage
from app.tests.database.domain.test_assistant import conversation, send
from app.tests.database.domain.test_catalog import create_book, create_copy

pytestmark = pytest.mark.integration


def test_groq_catalog_turn_persists_the_grounded_reply(staff, actor, domain_db, monkeypatch):
    book = create_book(staff, title="Introduction to Python", language="en")
    create_copy(staff, book, shelf_location="B-14")
    actor(UserRole.READER)
    identity = conversation(staff)
    question = "Where can I find Introduction to Python?"
    settings = staff.app.state.settings
    staff.app.state.settings = settings.model_copy(
        update={"llm_provider": "groq", "groq_api_key": SecretStr("test-only")}
    )
    requests = []

    def groq(request):
        assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
        messages = json.loads(request.content)["messages"]
        requests.append(messages[-1]["role"])
        if messages[-1]["role"] == "user":
            assert messages[-1]["content"] == question
            name = "search_books"
            args = {"q": book["title"], "available": None, "language": None}
        else:
            evidence = json.loads(messages[-1]["content"])
            item = next(item for item in evidence["books"] if item["id"] == book["id"])
            assert item["available_copies"] == 1 and item["shelf_locations"] == ["B-14"]
            name = "present_answer"
            args = {
                "kind": "results",
                "language": "en",
                "presentation": "availability",
                # Groq can return the UUID it just read instead of the display reference.
                "book_refs": [item["id"]],
                "evidence_refs": [evidence["evidence_ref"]],
            }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "tool_calls": [
                                {
                                    "id": f"call-{len(requests)}",
                                    "type": "function",
                                    "function": {"name": name, "arguments": json.dumps(args)},
                                }
                            ]
                        },
                    }
                ]
            },
        )

    client_class = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: client_class(**kwargs, transport=httpx.MockTransport(groq)),
    )
    response = send(staff, identity, question)
    assert response.status_code == 200, response.text
    answer = response.json()
    assert requests == ["user", "tool"]
    assert answer["books"][0]["id"] == book["id"]
    assert book["title"] in answer["content"] and "B-14" in answer["content"]
    assert "available" in answer["content"].lower()
    with Session(domain_db) as db:
        saved = db.get(AIMessage, UUID(answer["id"]))
        assert saved.content == answer["content"] and saved.tool_metadata["provider"] == "groq"
        assert saved.model_name == "openai/gpt-oss-120b"
