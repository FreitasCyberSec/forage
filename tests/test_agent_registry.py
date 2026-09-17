"""Tests for the NEXUS specialized-agent registry."""

import pytest

from forage.orchestration.base import ExecutionContext, SpecializedAgent
from forage.orchestration.registry import AgentRegistry


class StubAgent(SpecializedAgent):
    agent_id = "stub"
    name = "Stub Agent"
    role = "Test routing"
    memory_scope = "agent:stub"
    capabilities = ("stub_capability",)
    preferred_tier = "routine"

    def execute(self, task: dict, context: ExecutionContext) -> dict:
        return {"success": True, "task": task, "context": context}


def test_registry_registers_and_retrieves_agent():
    registry = AgentRegistry()
    agent = StubAgent()

    registry.register(agent)

    assert registry.get("stub") is agent
    assert registry.list_agents() == [agent]


def test_registry_rejects_duplicate_ids():
    registry = AgentRegistry()
    registry.register(StubAgent())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(StubAgent())


def test_registry_unknown_agent_returns_none():
    registry = AgentRegistry()

    assert registry.get("missing") is None
