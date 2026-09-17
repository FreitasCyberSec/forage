"""Tests for LLM structured-output routing."""

from types import SimpleNamespace

import forage.infra.llm as llm_module
from forage.infra.llm import LLMRouter


class DummyAudit:
    def log(self, *args, **kwargs):
        pass


def test_complete_uses_strict_json_schema(config, monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"action":"idle"}'))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

    monkeypatch.setattr(llm_module.litellm, "completion", fake_completion)
    monkeypatch.setattr(llm_module.litellm, "completion_cost", lambda **kwargs: 0.0)

    router = LLMRouter(config, DummyAudit())
    schema = {
        "type": "object",
        "properties": {"action": {"type": "string"}},
        "required": ["action"],
        "additionalProperties": False,
    }

    router.complete(
        "Pick an action",
        json_schema=schema,
        json_schema_name="agent_decision",
    )

    assert captured["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "agent_decision",
            "strict": True,
            "schema": schema,
        },
    }
