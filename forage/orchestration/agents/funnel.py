"""NEXUS Funnel Agent adapter around the existing Funnel Architect capability."""

from forage.orchestration.base import ExecutionContext, SpecializedAgent


class FunnelAgent(SpecializedAgent):
    agent_id = "funnel"
    name = "Funnel Agent"
    role = "Design operational funnels and automation flows"
    memory_scope = "agent:funnel"
    capabilities = ("funnel_architect",)
    preferred_tier = "important"

    def __init__(self, *, capability, wallet, llm):
        self.capability = capability
        self.wallet = wallet
        self.llm = llm

    def execute(self, task: dict, context: ExecutionContext) -> dict:
        original = str(task.get("description", "")).strip()
        knowledge = [*context.global_knowledge, *context.agent_knowledge]

        if knowledge:
            knowledge_block = "\n".join(
                f"- {item['title']}: {item['content']}" for item in knowledge
            )
            description = (
                f"{original}\n\n"
                "Relevant NEXUS knowledge:\n"
                f"{knowledge_block}"
            )
        else:
            description = original

        return self.capability.execute(
            {**task, "description": description},
            self.wallet,
            self.llm,
        )
