"""Server-only adapters for the library's validated tools and answer plans."""

import json
import time
from typing import Any

import httpx
from pydantic import SecretStr

from app.ai.assistant.contracts import AnswerPlan, LLMClient, ProviderReply, ToolCall, unavailable
from app.ai.assistant.policy import SYSTEM
from app.core.config import Settings


def _post_json(
    url: str,
    payload: dict[str, Any],
    key: SecretStr,
    timeout: float,
    *,
    retry_groq_tool_error: bool = False,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    try:
        with httpx.Client(follow_redirects=False) as client:
            for attempt in range(2 if retry_groq_tool_error else 1):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise unavailable()
                with client.stream(
                    "POST",
                    url,
                    timeout=min(remaining, 20),
                    json=payload,
                    headers={"Authorization": "Bearer " + key.get_secret_value()},
                ) as response:
                    check_tool_error = (
                        retry_groq_tool_error and not attempt and response.status_code == 400
                    )
                    if not check_tool_error:
                        response.raise_for_status()
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 262144 or time.monotonic() > deadline:
                            raise unavailable()
                    data = json.loads(raw)
                    if not isinstance(data, dict):
                        raise unavailable()
                    if not check_tool_error:
                        return data
                    error = data.get("error")
                    if not isinstance(error, dict) or error.get("code") != "tool_use_failed":
                        raise unavailable()
                    # No function ran. Regenerate once with lower temperature, without
                    # sending Groq's failed_generation content back to the model.
                    payload = {**payload, "temperature": 0.2}
    except (httpx.HTTPError, ValueError):
        raise unavailable() from None
    raise unavailable()


def _tokens(usage: dict[str, Any], key: str) -> int:
    value = usage.get(key, 0)
    if type(value) is not int or value < 0:
        raise unavailable()
    return value


class OpenAIResponses:
    def __init__(self, settings: Settings):
        self.settings = settings

    def respond(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], timeout: float
    ) -> ProviderReply:
        payload = {
            "model": self.settings.assistant_model,
            "instructions": SYSTEM,
            "input": messages,
            "tools": tools,
            "parallel_tool_calls": False,
            "store": False,
            "include": ["reasoning.encrypted_content"],
            "max_output_tokens": 2000,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "library_answer",
                    "strict": True,
                    "schema": AnswerPlan.model_json_schema(),
                }
            },
        }
        data = _post_json(
            "https://api.openai.com/v1/responses", payload, self.settings.llm_api_key, timeout
        )
        try:
            if data.get("status") != "completed" or not isinstance(data.get("output"), list):
                raise unavailable()
            reply = ProviderReply()
            text = ""
            for item in data["output"]:
                if item["type"] == "function_call":
                    reply.calls.append(ToolCall(item["call_id"], item["name"], item["arguments"]))
                    reply.continuation.append(item)
                elif item["type"] == "reasoning":
                    reply.continuation.append(item)
                elif item["type"] == "message":
                    for part in item["content"]:
                        if part["type"] != "output_text":
                            raise unavailable()
                        text += part["text"]
                else:
                    raise unavailable()
            if text:
                reply.answer = AnswerPlan.model_validate_json(text)
            if bool(reply.calls) == bool(reply.answer) or len(reply.calls) > 3:
                raise unavailable()
            usage = data.get("usage") or {}
            reply.input_tokens = _tokens(usage, "input_tokens")
            reply.output_tokens = _tokens(usage, "output_tokens")
            return reply
        except (ValueError, KeyError, TypeError, AttributeError):
            raise unavailable() from None


class GroqChat:
    def __init__(self, model: str, key: SecretStr):
        self.model = model
        self.key = key

    def respond(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], timeout: float
    ) -> ProviderReply:
        # Groq supports local function calls. The final function submits a typed
        # answer plan without combining tool use with unsupported structured output mode.
        functions = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
            for tool in tools
        ]
        functions.append(
            {
                "name": "present_answer",
                "description": "Submit the final library presentation plan and finish this turn.",
                "parameters": AnswerPlan.model_json_schema(),
            }
        )
        history = [
            {
                "role": "system",
                "content": SYSTEM + "\nSubmit your final JSON by calling present_answer.",
            }
        ]
        for item in messages:
            if item.get("type") == "function_call_output":
                history.append(
                    {"role": "tool", "tool_call_id": item["call_id"], "content": item["output"]}
                )
            else:
                history.append(item)
        data = _post_json(
            "https://api.groq.com/openai/v1/chat/completions",
            {
                "model": self.model,
                "messages": history,
                "tools": [{"type": "function", "function": fn} for fn in functions],
                "tool_choice": "required",
                "parallel_tool_calls": False,
                "max_completion_tokens": 1200,
            },
            self.key,
            timeout,
            retry_groq_tool_error=True,
        )
        try:
            choice = data["choices"][0]
            if choice["finish_reason"] != "tool_calls":
                raise unavailable()
            calls = choice["message"]["tool_calls"]
            if not isinstance(calls, list) or len(calls) != 1:
                raise unavailable()
            call = calls[0]
            name = call["function"]["name"]
            arguments = call["function"]["arguments"]
            if call["type"] != "function" or not all(
                isinstance(field, str) for field in (call["id"], name, arguments)
            ):
                raise unavailable()
            usage = data.get("usage") or {}
            reply = ProviderReply(
                input_tokens=_tokens(usage, "prompt_tokens"),
                output_tokens=_tokens(usage, "completion_tokens"),
            )
            if name == "present_answer":
                reply.answer = AnswerPlan.model_validate_json(arguments)
            else:
                reply.calls = [ToolCall(call["id"], name, arguments)]
                reply.continuation = [{"role": "assistant", "tool_calls": calls}]
            return reply
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            raise unavailable() from None


def provider(settings: Settings) -> LLMClient:
    if settings.assistant_provider == "groq":
        if settings.groq_api_key.get_secret_value().strip():
            return GroqChat(settings.assistant_model, settings.groq_api_key)
    elif (
        settings.assistant_provider == "openai"
        and settings.assistant_model
        and settings.llm_api_key.get_secret_value().strip()
    ):
        return OpenAIResponses(settings)
    raise unavailable()
