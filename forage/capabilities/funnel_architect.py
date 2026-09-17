"""Capability para analisar e projetar funis em FlowSpec JSON."""

import json

from forage.capabilities.base import Capability


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
            "Crie uma arquitetura profissional de funil."
        )

        prompt = f"""
Você é um arquiteto especialista em automações e funis.

Analise o pedido abaixo:

{description}

Transforme o funil em um FlowSpec estruturado.

O resultado deve conter:

- name
- objective
- nodes
- connections
- conditions
- delays
- tags
- metrics
- integrations

Tipos possíveis de nodes:

ENTRY
WELCOME
CAPTURE
SEGMENT
WARMUP
CONTENT
OFFER
CHECKOUT
PAYMENT
DELIVERY
UPSELL
RECOVERY
REMARKETING
RETENTION
WINBACK
END

Cada node deve possuir:

id
type
name
description
next

Responda SOMENTE JSON válido.
"""

        response = llm.complete(
            prompt,
            tier="important",
            max_tokens=2500,
            json_mode=True,
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
            flowspec = {
                "raw": response.content
            }

        return {
            "success": True,
            "revenue": 0,
            "cost": cost,
            "description": "FlowSpec criado pelo Funnel Architect.",
            "artifacts": {
                "flowspec": flowspec
            },
        }