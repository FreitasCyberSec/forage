"""Registration and lookup for NEXUS specialized agents."""

from forage.orchestration.base import SpecializedAgent


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, SpecializedAgent] = {}

    def register(self, agent: SpecializedAgent) -> None:
        agent_id = agent.agent_id.strip()
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        if agent_id in self._agents:
            raise ValueError(f"Agent '{agent_id}' is already registered")
        self._agents[agent_id] = agent

    def get(self, agent_id: str) -> SpecializedAgent | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[SpecializedAgent]:
        return list(self._agents.values())
