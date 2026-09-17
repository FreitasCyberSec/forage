"""Deterministic task routing for NEXUS specialized agents."""

from forage.knowledge.store import KnowledgeStore
from forage.orchestration.base import ExecutionContext
from forage.orchestration.registry import AgentRegistry
from forage.safety.audit import AuditLog


class UnknownAgentError(LookupError):
    pass


class NexusOrchestrator:
    def __init__(
        self,
        *,
        registry: AgentRegistry,
        knowledge: KnowledgeStore,
        audit: AuditLog,
    ):
        self.registry = registry
        self.knowledge = knowledge
        self.audit = audit

    def execute(self, agent_id: str, task: dict) -> dict:
        agent = self.registry.get(agent_id)
        if agent is None:
            raise UnknownAgentError(f"Unknown NEXUS agent: {agent_id}")

        query = str(task.get("description", "")).strip() or agent.role
        context = ExecutionContext(
            global_knowledge=self.knowledge.search(
                query,
                ["global"],
                limit=5,
            ),
            agent_knowledge=self.knowledge.search(
                query,
                [agent.memory_scope],
                limit=5,
            ),
        )

        try:
            result = agent.execute(task, context)
        except Exception as exc:
            self.audit.log(
                "nexus_agent_error",
                f"Agent '{agent_id}' failed: {type(exc).__name__}",
                level="error",
                details={"agent_id": agent_id, "error_type": type(exc).__name__},
            )
            raise

        self.audit.log(
            "nexus_agent_execute",
            f"Agent '{agent_id}' executed a task",
            cost_usd=float(result.get("cost", 0) or 0),
            revenue_usd=float(result.get("revenue", 0) or 0),
            details={
                "agent_id": agent_id,
                "success": bool(result.get("success")),
            },
        )
        return result
