"""Capability para analisar e projetar funis em FlowSpec JSON."""

import json

from forage.capabilities.base import Capability


NODE_TYPES = [
    "ENTRY",
    "WELCOME",
    "CAPTURE",
    "SEGMENT",
    "WARMUP",
    "CONTENT",
    "OFFER",
    "CHECKOUT",
    "PAYMENT",
    "DELIVERY",
    "UPSELL",
    "RECOVERY",
    "REMARKETING",
    "RETENTION",
    "WINBACK",
    "END",
]


FLOW_SPEC_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "objective": {"type": "string"},
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": NODE_TYPES},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "next": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["id", "type", "name", "description", "next"],
                "additionalProperties": False,
            },
        },
        "connections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "condition": {"type": "string"},
                },
                "required": ["from", "to", "condition"],
                "additionalProperties": False,
            },
        },
        "conditions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "expression": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["id", "expression", "description"],
                "additionalProperties": False,
            },
        },
        "delays": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "after_node": {"type": "string"},
                    "seconds": {"type": "integer"},
                    "description": {"type": "string"},
                },
                "required": ["after_node", "seconds", "description"],
                "additionalProperties": False,
            },
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "metrics": {
            "type": "array",
            "items": {"type": "string"},
        },
        "integrations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "name",
        "objective",
        "nodes",
        "connections",
        "conditions",
        "delays",
        "tags",
        "metrics",
        "integrations",
    ],
    "additionalProperties": False,
}


class FunnelArchitectCapability(Capability):
    name = "funnel_architect"

    def can_execute(self, context: dict) -> bool:
        return True

    def estimate_cost(self, task: dict) -> float:
        return 0.01

    def estimate_revenue(self, task: dict) -> float:
        return 0.0

    def execute(self, task: dict, wallet, llm) -> dict:
        description = task.get(
            "description",
            "Crie uma arquitetura profissional de funil.",
        )

        prompt = f"""
Você é um arquiteto especialista em automações e funis.

Analise o pedido abaixo:

{description}

Transforme o pedido em um FlowSpec operacional, coerente e completo.
Use IDs únicos nos nodes e faça todas as conexões apontarem para IDs existentes.
Para conexões sem condição, use uma string vazia em condition.
Quando uma seção não for necessária, retorne um array vazio.
"""

        response = llm.complete(
            prompt,
            tier="important",
            max_tokens=2500,
            temperature=0.2,
            json_schema=FLOW_SPEC_SCHEMA,
            json_schema_name="flow_spec",
        )

        cost = response.cost_usd

        spend = wallet.spend(
            cost,
            "Funnel Architect analysis",
            details={"description": description[:200]},
        )

        if not spend.success:
            return {
                "success": False,
                "revenue": 0,
                "cost": 0,
                "description": f"Sem orçamento: {spend.reason}",
            }

        try:
            flowspec = json.loads(response.content)
        except json.JSONDecodeError:
            return {
                "success": False,
                "revenue": 0,
                "cost": cost,
                "description": "A IA retornou um FlowSpec inválido.",
                "artifacts": {"raw": response.content},
            }

        return {
            "success": True,
            "revenue": 0,
            "cost": cost,
            "description": "FlowSpec criado pelo Funnel Architect.",
            "artifacts": {
                "flowspec": flowspec,
            },
        }
