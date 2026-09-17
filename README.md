<p align="center">
  <h1 align="center">NEXUS Agent OS</h1>
  <p align="center"><strong>Autonomous AI orchestration with memory, tools and real-world execution.</strong></p>
  <p align="center">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python"></a>
    <img src="https://img.shields.io/badge/status-active%20development-orange.svg" alt="Status">
  </p>
</p>

> **NEXUS Agent OS** is an experimental autonomous-agent platform being built to understand goals, plan workflows, use specialized capabilities, retain operational memory and progressively improve automations over time.

The project started as a fork of **Nerfed-Lab/forage** and is being evolved from an economic survival-agent experiment into a general-purpose AI orchestration layer.

## Vision

NEXUS is not intended to be just a chatbot or a single-purpose funnel generator.

The long-term goal is to build an **Agent Operating System** where one orchestration core can coordinate specialized agents for business automation, infrastructure, data and operations.

```text
                         NEXUS CORE
                             │
             ┌───────────────┼───────────────┐
             │               │               │
          BUSINESS         DEVOPS           DATA
             │               │               │
       Funnel Architect   VPS / Docker    Analytics
       CRM Agent          APIs            Metrics
       Copy Agent         Monitoring      Reports
       Support Agent      n8n             Experiments
             │               │               │
             └───────────────┼───────────────┘
                             │
                       MEMORY LAYER
                             │
                     LEARN → ACT → ADAPT
```

## What exists today

NEXUS is already running as an autonomous process on a VPS and currently includes:

- **Persistent agent state** across restarts.
- **Experience memory** used by the decision loop.
- **LLM routing** with Groq support.
- **Structured JSON output** for reliable machine-readable actions.
- **Funnel Architect** capability.
- **FlowSpec generation** with nodes, connections, conditions, delays, tags, metrics and integrations.
- **Protected Funnel API** using `X-API-Key`.
- **Spending limits and emergency reserve controls** inherited from the original Forage architecture.
- **Audit logging** for agent actions and LLM calls.
- **Web dashboard** through FastAPI.
- **Docker / EasyPanel deployment**.

### Current primary capability

The first custom capability is `funnel_architect`.

It converts a natural-language objective into a structured FlowSpec that can later be translated into executable workflows.

Example idea:

```text
User request
    ↓
NEXUS
    ↓
Funnel Architect
    ↓
FlowSpec JSON
    ↓
n8n / APIs / external platforms
```

Example FlowSpec concepts:

```text
ENTRY
  ↓
WELCOME
  ↓
WARMUP
  ↓
OFFER
  ↓
CHECKOUT
  ├── PAYMENT → DELIVERY → UPSELL → RETENTION
  └── NO PAYMENT → RECOVERY → REMARKETING
```

## Protected Funnel API

NEXUS exposes a protected endpoint:

```text
POST /api/funnel/analyze
```

Example request:

```bash
curl -X POST "https://YOUR-NEXUS-DOMAIN/api/funnel/analyze" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FORAGE_API_KEY" \
  -d '{
    "description": "Create a funnel with entry, warm-up, offer, checkout, recovery, upsell and retention."
  }'
```

Example response shape:

```json
{
  "success": true,
  "cost": 0.0001,
  "description": "FlowSpec criado pelo Funnel Architect.",
  "flowspec": {
    "name": "...",
    "objective": "...",
    "nodes": [],
    "connections": [],
    "conditions": [],
    "delays": [],
    "tags": [],
    "metrics": [],
    "integrations": []
  }
}
```

## Agent loop

NEXUS retains the autonomous execution loop inherited from Forage:

```text
WAKE
  ↓
CHECK STATE / VITALS
  ↓
READ RECENT EXPERIENCE
  ↓
DECIDE
  ↓
SELECT CAPABILITY
  ↓
ACT
  ↓
REFLECT
  ↓
STORE EXPERIENCE
  ↓
SLEEP
  ↺
```

The memory layer matters because the system should not treat every cycle as a blank slate. Outcomes can be stored and reused as context for later decisions.

## Why FlowSpec?

NEXUS should not be permanently tied to one automation provider.

The target architecture is:

```text
Natural-language goal
        ↓
      NEXUS
        ↓
     FlowSpec
     /   |   \
    /    |    \
  n8n   API   Platform Adapter
```

FlowSpec becomes the intermediate representation between AI reasoning and external execution.

That makes it possible to eventually support multiple workflow engines without redesigning the reasoning layer every time.

## Roadmap

### Phase 1 — Core foundation

- [x] Autonomous agent loop
- [x] Persistent state
- [x] Memory layer
- [x] Groq integration
- [x] Structured JSON output
- [x] Funnel Architect capability
- [x] Protected Funnel API
- [x] Docker / EasyPanel deployment

### Phase 2 — Workflow execution

- [ ] n8n integration
- [ ] FlowSpec → n8n translator
- [ ] Webhook execution
- [ ] Workflow validation
- [ ] Dry-run mode
- [ ] Human approval before production changes

### Phase 3 — Specialized agents

Planned capabilities include:

- **Workflow Architect** — design general automations beyond funnels.
- **Analytics Agent** — inspect metrics and identify bottlenecks.
- **Research Agent** — collect and structure information for decisions.
- **CRM Agent** — manage lead/customer state and lifecycle logic.
- **DevOps Agent** — inspect infrastructure, logs and deployments.
- **Monitoring Agent** — detect failures and operational anomalies.
- **Experiment Agent** — create controlled variants and compare outcomes.

### Phase 4 — Closed optimization loop

The target loop is:

```text
BUILD
  ↓
EXECUTE
  ↓
MEASURE
  ↓
ANALYZE
  ↓
PROPOSE IMPROVEMENT
  ↓
HUMAN APPROVAL / SAFETY POLICY
  ↓
DEPLOY
  ↺
```

The system should eventually be able to improve workflows from real metrics while keeping critical actions behind explicit limits and approval gates.

## Safety model

Autonomy does not mean unrestricted access.

The project is being designed around:

- explicit capability enable/disable flags;
- API-key protected external endpoints;
- spending limits;
- emergency reserve limits;
- audit logs;
- allowlisted integrations;
- human approval for critical production changes;
- isolated adapters rather than unrestricted execution.

The current configuration deliberately keeps most original revenue-generating capabilities disabled while the new architecture is being developed and tested.

## Current configuration

The active custom module is currently:

```yaml
capabilities:
  funnel_architect: true
```

Other original Forage capabilities are disabled in the development configuration while NEXUS is being expanded safely.

The current primary LLM provider is Groq using:

```yaml
providers:
  - name: groq
    api_key: "${GROQ_API_KEY}"
    models:
      - "openai/gpt-oss-20b"
    tier: routine
```

## EasyPanel deployment

The current production-style development environment uses Docker Compose on EasyPanel.

Required environment variables:

```text
GROQ_API_KEY=...
FORAGE_API_KEY=...
```

The EasyPanel-specific Compose file is:

```text
docker-compose.easypanel.yaml
```

The application dashboard listens internally on:

```text
3000
```

## Repository naming

The repository and Python package currently retain the technical name `forage` for compatibility with the upstream codebase and existing deployments.

**NEXUS Agent OS is the product/project identity.**

Keeping the technical package name unchanged for now avoids breaking:

- imports such as `from forage...`;
- the existing CLI;
- Docker builds;
- EasyPanel source configuration;
- deployed service names;
- existing automation paths.

A full package/repository migration can be performed later as a dedicated compatibility-safe migration.

## Project status

NEXUS is under active development.

Today it is best described as:

> **A working autonomous-agent core with memory and a first specialized capability, being expanded into a general AI orchestration system.**

It is **not yet** a fully autonomous business operator, universal DevOps agent or self-optimizing production platform. Those are roadmap goals, not current claims.

## Origin and license

NEXUS Agent OS is based on the open-source **Forage** project by **Nerfed-Lab**.

Original project:

`https://github.com/Nerfed-Lab/forage`

This fork preserves the project's MIT license. See [`LICENSE`](LICENSE).

The NEXUS-specific architecture, capabilities and integrations in this fork are being developed in:

`FreitasCyberSec/forage`
