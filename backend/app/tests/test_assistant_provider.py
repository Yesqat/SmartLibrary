"""Mock only the external HTTP provider; exercise the production adapter/parser."""

import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.ai.assistant.contracts import AnswerPlan
from app.ai.assistant.provider import OpenAIResponses, provider
from app.ai.assistant.tools import definitions
from app.core.errors import AppError


def adapter(settings, monkeypatch, handler):
    client_class = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: client_class(**kwargs, transport=httpx.MockTransport(handler)),
    )
    configured = settings.model_copy(
        update={
            "llm_provider": "openai",
            "llm_model": "test-model",
            "llm_api_key": SecretStr("test-external-boundary-only"),
        }
    )
    return OpenAIResponses(configured)


def test_responses_tool_contract_has_no_arbitrary_identity_or_write(settings, monkeypatch):
    def handler(request):
        assert str(request.url) == "https://api.openai.com/v1/responses"
        body = json.loads(request.content)
        assert body["store"] is False and body["parallel_tool_calls"] is False
        assert body["text"]["format"]["strict"] is True
        for tool in body["tools"]:
            assert tool["parameters"]["additionalProperties"] is False
            assert set(tool["parameters"].get("required", [])) == set(
                tool["parameters"].get("properties", {})
            )
            assert "user_id" not in tool["parameters"].get("properties", {})
        assert {tool["name"] for tool in body["tools"]} == {
            "search_books",
            "semantic_search_books",
            "get_book_details",
            "check_book_availability",
            "get_similar_books",
            "get_recommendations",
            "get_my_borrowings",
            "get_my_reservations",
            "get_library_rules",
        }
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call1",
                        "name": "get_library_rules",
                        "arguments": "{}",
                    }
                ],
                "usage": {"input_tokens": 12, "output_tokens": 5},
            },
        )

    result = adapter(settings, monkeypatch, handler).respond(
        [{"role": "user", "content": "rules"}], definitions(), 20
    )
    assert result.calls[0].name == "get_library_rules" and result.input_tokens == 12


def test_structured_plan_parses_but_cannot_add_invented_prose(settings, monkeypatch):
    output = AnswerPlan(kind="clarify_topic", book_refs=[], evidence_refs=[])
    client = adapter(
        settings,
        monkeypatch,
        lambda request: httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": output.model_dump_json()}],
                    }
                ],
            },
        ),
    )
    assert client.respond([], definitions(), 20).answer == output
    with pytest.raises(ValidationError):
        AnswerPlan.model_validate(
            {**output.model_dump(), "content": "Invented physical availability"}
        )


@pytest.mark.parametrize(
    "failure", ["http", "timeout", "invalid_json", "refusal", "incomplete", "oversize", "bad_plan"]
)
def test_external_failures_are_safe(settings, monkeypatch, failure):
    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("private provider detail")
        if failure == "http":
            return httpx.Response(401, text="private API key error")
        if failure == "invalid_json":
            return httpx.Response(200, text="bad JSON")
        if failure == "oversize":
            return httpx.Response(200, content=b"x" * 262145)
        return httpx.Response(
            200,
            json={
                "status": "incomplete" if failure == "incomplete" else "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "refusal" if failure == "refusal" else "output_text",
                                "text": "{}",
                            }
                        ],
                    }
                ],
            },
        )

    with pytest.raises(AppError) as error:
        adapter(settings, monkeypatch, handler).respond([], definitions(), 20)
    assert error.value.code == "AI_SERVICE_UNAVAILABLE" and "private" not in error.value.message


def test_missing_or_unsupported_provider_is_unavailable(settings):
    for name in ("", "unregistered"):
        with pytest.raises(AppError) as error:
            provider(settings.model_copy(update={"llm_provider": name}))
        assert error.value.status == 503
