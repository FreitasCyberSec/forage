"""Tests for the NEXUS Funnel Agent adapter."""

from forage.orchestration.base import ExecutionContext
from forage.orchestration.agents.funnel import FunnelAgent


class FakeCapability:
    def __init__(self):
        self.last_task = None

    def execute(self, task, wallet, llm):
        self.last_task = task
        return {
            "success": True,
            "cost": 0.001,
            "revenue": 0,
            "description": "FlowSpec criado.",
            "artifacts": {"flowspec": {"name": "Test"}},
        }


def test_funnel_agent_delegates_and_includes_retrieved_knowledge():
    capability = FakeCapability()
    agent = FunnelAgent(capability=capability, wallet=object(), llm=object())
    context = ExecutionContext(
        global_knowledge=[{"title": "Global rule", "content": "Measure conversion."}],
        agent_knowledge=[{"title": "Funnel rule", "content": "Warm up before offer."}],
    )

    result = agent.execute(
        {"description": "Create a funnel for a course."},
        context,
    )

    assert result["success"] is True
    assert "Create a funnel for a course." in capability.last_task["description"]
    assert "Measure conversion." in capability.last_task["description"]
    assert "Warm up before offer." in capability.last_task["description"]
