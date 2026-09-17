"""Tests for deterministic NEXUS task orchestration."""

import pytest

from forage.knowledge.store import KnowledgeStore
from forage.orchestration.base import ExecutionContext, SpecializedAgent
from forage.orchestration.orchestrator import NexusOrchestrator, UnknownAgentError
from forage.orchestration.registry import AgentRegistry
from forage.safety.audit import AuditLog


class RecordingAgent(SpecializedAgent):
    agent_id = "recording"
    name = "Recording Agent"
    role = "Capture execution context"
    memory_scope = "agent:recording"
    capabilities = ("record",)

    def __init__(self):
        self.last_context = None

    def execute(self, task: dict, context: ExecutionContext) -> dict:
        self.last_context = context
        return {"success": True, "cost": 0, "revenue": 0, "task": task}


def test_orchestrator_routes_explicit_agent_and_supplies_scoped_knowledge(initialized_db):
    store = KnowledgeStore(initialized_db)
    store.add(scope="global", kind="rule", title="Global", content="Global rule")
    store.add(
        scope="agent:recording",
        kind="pattern",
        title="Private",
        content="Agent-only rule",
    )
    store.add(
        scope="agent:other",
        kind="pattern",
        title="Other",
        content="Must not leak",
    )

    registry = AgentRegistry()
    agent = RecordingAgent()
    registry.register(agent)
    orchestrator = NexusOrchestrator(
        registry=registry,
        knowledge=store,
        audit=AuditLog(initialized_db),
    )

    result = orchestrator.execute("recording", {"description": "test task"})

    assert result["success"] is True
    assert [row["title"] for row in agent.last_context.global_knowledge] == ["Global"]
    assert [row["title"] for row in agent.last_context.agent_knowledge] == ["Private"]


def test_orchestrator_rejects_unknown_agent(initialized_db):
    orchestrator = NexusOrchestrator(
        registry=AgentRegistry(),
        knowledge=KnowledgeStore(initialized_db),
        audit=AuditLog(initialized_db),
    )

    with pytest.raises(UnknownAgentError, match="missing"):
        orchestrator.execute("missing", {"description": "test"})
