"""OpenAI Responses adapter. No credentials or provider payloads reach app logs/UI."""

import json
import time
from typing import Any

import httpx
from pydantic import ValidationError

from app.ai.assistant.contracts import AnswerPlan, LLMClient, ProviderReply, ToolCall, unavailable
from app.ai.assistant.policy import SYSTEM
from app.core.config import Settings


class OpenAIResponses:
    def __init__(self, settings: Settings):
        self.settings = settings

    def respond(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], timeout: float
    ) -> ProviderReply:
        deadline = time.monotonic() + timeout
        payload = {
            "model": self.settings.llm_model,
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
        try:
            # Fixed HTTPS destination; user/model cannot choose an endpoint or trigger redirects.
            with (
                httpx.Client(timeout=min(timeout, 20), follow_redirects=False) as client,
                client.stream(
                    "POST",
                    "https://api.openai.com/v1/responses",
                    json=payload,
                    headers={
                        "Authorization": "Bearer " + self.settings.llm_api_key.get_secret_value()
                    },
                ) as response,
            ):
                response.raise_for_status()
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 262144 or time.monotonic() > deadline:
                        raise unavailable()
            data = json.loads(raw)
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
            for key in ("input_tokens", "output_tokens"):
                value = usage.get(key, 0)
                if type(value) is not int or value < 0:
                    raise unavailable()
                setattr(reply, key, value)
            return reply
        except (httpx.HTTPError, ValueError, KeyError, TypeError, ValidationError):
            raise unavailable() from None


def provider(settings: Settings) -> LLMClient:
    if (
        settings.llm_provider != "openai"
        or not settings.llm_model.strip()
        or not settings.llm_api_key.get_secret_value().strip()
    ):
        raise unavailable()
    return OpenAIResponses(settings)
