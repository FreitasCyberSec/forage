"""Tests for LLM structured-output routing."""

import httpx

import forage.infra.llm as llm_module
from forage.infra.llm import LLMRouter


class DummyAudit:
    def log(self, *args, **kwargs):
        pass


class DummyHTTPResponse:
    def __init__(self, payload):
        self._payload = payload
        self.text = str(payload)

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_groq_structured_output_uses_direct_api(config, monkeypatch):
    """Groq JSON Schema calls must bypass LiteLLM and hit Groq directly."""
    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return DummyHTTPResponse(
            {
                "choices": [
                    {"message": {"content": '{"action":"idle"}'}},
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                },
            }
        )

    def fail_litellm(**kwargs):
        raise AssertionError("Structured Groq calls must not use LiteLLM")

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(llm_module.litellm, "completion", fail_litellm)

    router = LLMRouter(config, DummyAudit())
    schema = {
        "type": "object",
        "properties": {"action": {"type": "string"}},
        "required": ["action"],
        "additionalProperties": False,
    }

    response = router.complete(
        "Pick an action",
        json_schema=schema,
        json_schema_name="agent_decision",
    )

    assert response.content == '{"action":"idle"}'
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["json"]["model"] == "llama-3.1-8b-instant"
    assert captured["json"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "agent_decision",
            "strict": True,
            "schema": schema,
        },
    }
    assert captured["json"]["reasoning_format"] == "hidden"
