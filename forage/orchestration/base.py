"""Core contracts for NEXUS specialized agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExecutionContext:
    global_knowledge: list[dict] = field(default_factory=list)
    agent_knowledge: list[dict] = field(default_factory=list)


class SpecializedAgent(ABC):
    agent_id: str
    name: str
    role: str
    memory_scope: str
    capabilities: tuple[str, ...] = ()
    preferred_tier: str = "routine"

    @abstractmethod
    def execute(self, task: dict, context: ExecutionContext) -> dict:
        raise NotImplementedError
