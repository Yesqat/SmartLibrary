"""Mock only the external HTTP provider; exercise the production adapter/parser."""

import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.ai.assistant.contracts import AnswerPlan
from app.ai.assistant.provider import GroqChat, provider
from app.ai.assistant.tools import definitions
from app.core.errors import AppError


def adapter(settings, monkeypatch, handler, name="openai"):
    client_class = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: client_class(**kwargs, transport=httpx.MockTransport(handler)),
    )
    configured = settings.model_copy(
        update={
            "llm_provider": name,
            "llm_model": "test-model" if name == "openai" else "",
            "llm_api_key": SecretStr("test-external-boundary-only"),
            "groq_api_key": SecretStr("test-groq-boundary-only"),
        }
    )
    return provider(configured)


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
    output = AnswerPlan(
        kind="clarify_topic", book_refs=[], evidence_refs=[], language="kk", presentation="search"
    )
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


def groq_call(name, arguments, identity="first"):
    return {
        "id": identity,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def groq_result(calls):
    return {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {"role": "assistant", "content": None, "tool_calls": calls},
            }
        ],
        "usage": {"prompt_tokens": 45, "completion_tokens": 6},
    }


def test_groq_round_trip_uses_catalog_tool_output_then_validates_plan(settings, monkeypatch):
    question = {"role": "user", "content": "What are the library rules?"}
    first_call = groq_call("get_library_rules", {})
    evidence = json.dumps({"evidence_ref": "result1", "rules": {"max_loans": 5}})
    output = AnswerPlan(
        kind="results",
        language="en",
        presentation="search",
        book_refs=[],
        evidence_refs=["result1"],
    )

    def handler(request):
        assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-groq-boundary-only"
        body = json.loads(request.content)
        assert body["model"] == "openai/gpt-oss-120b"
        assert body["tool_choice"] == "required" and body["parallel_tool_calls"] is False
        assert body["messages"][0]["role"] == "system" and body["messages"][1] == question
        functions = {t["function"]["name"]: t["function"] for t in body["tools"]}
        assert set(functions) == {tool["name"] for tool in definitions()} | {"present_answer"}
        assert functions["present_answer"]["parameters"] == AnswerPlan.model_json_schema()
        if len(body["messages"]) == 2:
            return httpx.Response(200, json=groq_result([first_call]))
        assert body["messages"][2:] == [
            {"role": "assistant", "tool_calls": [first_call]},
            {"role": "tool", "tool_call_id": "first", "content": evidence},
        ]
        final_call = groq_call("present_answer", output.model_dump(), "second")
        return httpx.Response(200, json=groq_result([final_call]))

    client = adapter(settings, monkeypatch, handler, "groq")
    first = client.respond([question], definitions(), 20)
    assert first.calls[0].name == "get_library_rules" and first.input_tokens == 45
    history = [
        question,
        *first.continuation,
        {"type": "function_call_output", "call_id": first.calls[0].id, "output": evidence},
    ]
    final = client.respond(history, definitions(), 20)
    assert final.answer == output and not final.calls and final.output_tokens == 6


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(429, text="private quota details"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json=groq_result([])),
        httpx.Response(
            200, json=groq_result([groq_call("present_answer", {"content": "invented"})])
        ),
    ],
)
def test_groq_failures_are_safe(settings, monkeypatch, response):
    client = adapter(settings, monkeypatch, lambda _: response, "groq")
    with pytest.raises(AppError) as error:
        client.respond([], definitions(), 20)
    assert error.value.code == "AI_SERVICE_UNAVAILABLE" and "private" not in error.value.message


def test_groq_retries_rejected_tool_generation_before_running_a_tool(settings, monkeypatch):
    attempts = []

    def handler(request):
        attempts.append(request)
        if len(attempts) == 1:
            return httpx.Response(
                400, json={"error": {"code": "tool_use_failed", "failed_generation": "private"}}
            )
        return httpx.Response(200, json=groq_result([groq_call("get_library_rules", {})]))

    reply = adapter(settings, monkeypatch, handler, "groq").respond([], definitions(), 20)
    assert len(attempts) == 2 and reply.calls[0].name == "get_library_rules"
    assert json.loads(attempts[1].content) == {
        **json.loads(attempts[0].content),
        "temperature": 0.2,
    }
    assert attempts[1].extensions["timeout"]["read"] <= attempts[0].extensions["timeout"]["read"]


@pytest.mark.parametrize(
    ("status", "code", "expected_calls"),
    [
        (400, "tool_use_failed", 2),
        (400, "other", 1),
        (401, "invalid_api_key", 1),
        (429, "rate_limit_exceeded", 1),
    ],
)
def test_groq_retry_is_specific_and_bounded(settings, monkeypatch, status, code, expected_calls):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, json={"error": {"code": code}})

    client = adapter(settings, monkeypatch, handler, "groq")
    with pytest.raises(AppError) as error:
        client.respond([], definitions(), 20)
    assert error.value.code == "AI_SERVICE_UNAVAILABLE" and len(requests) == expected_calls


def test_groq_uses_only_a_groq_key(settings):
    configured = settings.model_copy(
        update={"llm_provider": "", "llm_model": "", "groq_api_key": SecretStr("test-only-groq")}
    )
    assert isinstance(provider(configured), GroqChat)
    with pytest.raises(AppError):
        provider(
            configured.model_copy(
                update={
                    "llm_provider": "groq",
                    "groq_api_key": SecretStr(""),
                    "llm_api_key": SecretStr("other-provider-key"),
                }
            )
        )
