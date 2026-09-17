<p align="center">
  <h1 align="center">NEXUS Agent OS</h1>
  <p align="center"><strong>Autonomous AI orchestration with memory, specialized agents and survival-driven execution.</strong></p>
  <p align="center">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python"></a>
    <img src="https://img.shields.io/badge/status-active%20development-orange.svg" alt="Status">
  </p>
</p>

> **NEXUS Agent OS** is an experimental autonomous-agent platform that combines the survival/evolution ideas of Forage with a growing multi-agent orchestration layer, persistent knowledge and pluggable LLM providers.

The project began as a fork of **Nerfed-Lab/forage**. The goal is not to discard the original autonomous core, but to expand it into a system where specialized agents can share knowledge, use tools, learn from outcomes and work toward global objectives under centralized safety and budget controls.

## Core idea

NEXUS combines two ideas:

1. **Autonomous survival** — the system has a wallet, limits, memory, a decision loop and optional evolution inherited from Forage.
2. **Specialized intelligence** — tasks can be delegated to agents with their own role, knowledge scope and capabilities.

```text
                         NEXUS CORE
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
       SURVIVAL          ORCHESTRATION       KNOWLEDGE
          │                  │                  │
   wallet / limits      Agent Registry     global memory
   economy / state      Orchestrator       agent memory
   experience loop          │              semantic search
   evolution                │
          │          ┌───────┴────────┐
          │          │                │
          │     Funnel Agent     Future Agents
          │          │          DevOps / Data /
          │          │          Research / etc.
          └──────────┴───────────────┬──────────
                                     │
                                 LLM ROUTER
                              API / local models
```

## What is implemented now

The current codebase includes:

- **Autonomous Forage-derived lifecycle** with wake → decide → act → reflect → sleep.
- **Wallet, spending limits and emergency reserve controls**.
- **Persistent experience memory** with SQLite and optional ChromaDB indexing.
- **Genome/evolution subsystem**, still controlled by configuration and not forced on by NEXUS.
- **LLMRouter** with Groq support and a path for additional providers/local models.
- **Structured JSON outputs** for reliable machine-readable decisions.
- **Funnel Architect** capability that generates FlowSpec.
- **Protected Funnel API** using `X-API-Key`.
- **NEXUS Knowledge Store** with `global` and per-agent scopes.
- **NEXUS Agent Registry** for specialized agents.
- **Deterministic NEXUS Orchestrator** for explicit task routing.
- **Funnel Agent** as the first specialized-agent adapter.
- **Funnel API internally routed through the NEXUS Orchestrator** while preserving the external contract.
- **Audit logging**, FastAPI dashboard, Docker and EasyPanel deployment support.

The multi-agent foundation is implemented in code. Broader production validation and additional agents are still ongoing.

## Preserved from Forage

NEXUS intentionally keeps the useful parts of the original autonomous architecture rather than replacing them.

```text
FORAGE-DERIVED CORE
├── autonomous loop
├── wallet / economy
├── survival logic
├── AgentMemory
├── organism state
├── genome
├── evolution engine
└── capabilities

NEXUS LAYER
├── Agent Registry
├── Orchestrator
├── Knowledge Store
├── specialized agents
└── future agent creation / evaluation
```

This means the project can continue exploring the original idea of giving an agent limited resources and observing whether it can survive, while gradually giving it a richer organization of specialized agents and knowledge.

## Memory and knowledge

NEXUS deliberately separates two kinds of learning context.

### 1. Experience memory

The original `AgentMemory` stores operational experience such as:

- action taken;
- outcome;
- reward;
- context;
- reflection;
- success/failure history.

This remains part of the autonomous Forage-style learning loop.

### 2. NEXUS Knowledge Store

The new knowledge layer stores reusable information for specialized agents.

Scopes:

```text
global
agent:funnel
agent:devops
agent:data
...
```

A specialized agent can receive both global knowledge and knowledge from its own scope without automatically reading another agent's private scope.

SQLite is the source of truth. ChromaDB is an optional semantic index; vector-search failure must fall back to SQLite-backed retrieval instead of taking the agent offline.

## Multi-agent execution

The first implemented specialized agent is the **Funnel Agent**.

```text
Task
  ↓
NEXUS Orchestrator
  ↓
Agent Registry
  ↓
Funnel Agent
  ├── global knowledge
  ├── funnel knowledge
  └── Funnel Architect capability
          ↓
      LLM Router
          ↓
      FlowSpec JSON
```

Routing is intentionally deterministic in the current phase. Automatic LLM-based agent selection will only make sense after multiple production agents exist.

## Funnel Architect and FlowSpec

The Funnel Architect converts a natural-language goal into a structured FlowSpec containing concepts such as:

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

FlowSpec is intended to become an intermediate representation between AI reasoning and external workflow engines.

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

## Protected Funnel API

The current endpoint remains:

```text
POST /api/funnel/analyze
```

Authentication:

```text
X-API-Key: <FORAGE_API_KEY>
```

Example:

```bash
curl -X POST "https://YOUR-NEXUS-DOMAIN/api/funnel/analyze" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FORAGE_API_KEY" \
  -d '{
    "description": "Create a funnel with entry, warm-up, offer, checkout, recovery, upsell and retention."
  }'
```

Response shape:

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

The public API contract is intentionally unchanged even though the internal execution path now goes through the NEXUS orchestration layer.

## LLM architecture

Specialized agents are not hard-wired to Groq, OpenAI or a specific model. They operate through the existing `LLMRouter` abstraction.

Current development configuration uses Groq, while the architecture is intended to support a future split such as:

```text
routine tasks   → local model / Ollama
important tasks → stronger local model or Groq
complex tasks   → external high-capability model
```

A local LLM is **not deployed as part of the current multi-agent foundation**. The architecture is being prepared so adding one later does not require rewriting every agent.

## Current configuration

The first custom capability remains:

```yaml
capabilities:
  funnel_architect: true
```

Current primary LLM provider:

```yaml
providers:
  - name: groq
    api_key: "${GROQ_API_KEY}"
    models:
      - "openai/gpt-oss-20b"
    tier: routine
```

Most original revenue-generating capabilities remain disabled in the current development configuration while NEXUS is expanded incrementally.

## Roadmap

### Phase 1 — Multi-agent foundation

- [x] Autonomous Forage-derived core preserved
- [x] NEXUS Knowledge Store
- [x] Global + per-agent knowledge scopes
- [x] Specialized Agent contract
- [x] Agent Registry
- [x] Deterministic Orchestrator
- [x] Funnel Agent adapter
- [x] Existing Funnel API routed through NEXUS

### Phase 2 — Broader autonomous delegation

- [ ] Add additional production agents
- [ ] Automatic agent selection once multiple agents exist
- [ ] Shared task/result contracts across domains
- [ ] Metrics for per-agent cost, success rate and value

### Phase 3 — Knowledge ingestion / RAG

- [ ] Text ingestion API
- [ ] PDF/document ingestion
- [ ] Chunking and source metadata
- [ ] Deduplication
- [ ] Retrieval quality evaluation
- [ ] Promotion of useful experience into durable knowledge

### Phase 4 — Local LLM

- [ ] Validate Ollama or another OpenAI-compatible local server
- [ ] Local model for routine tasks
- [ ] Provider fallback rules
- [ ] Cost/quality routing by task tier

### Phase 5 — Agent Factory

The future Agent Factory may create a specialized agent when an appropriate one does not already exist.

Target concept:

```text
New task
   ↓
Existing agent suitable?
   ├── yes → execute
   └── no
        ↓
    Agent Factory
        ↓
 define role / knowledge / tools / limits
        ↓
 Teacher / Evaluator
        ↓
 sandbox tests
        ↓
 register or discard
```

This is a roadmap goal, **not a current capability**.

### Phase 6 — Teacher / Evaluator

- [ ] determine what a new agent needs to know;
- [ ] build evaluation cases;
- [ ] test agents before registration;
- [ ] compare model/tool choices;
- [ ] reject weak or unsafe variants.

### Phase 7 — Metrics-driven specialized evolution

- [ ] per-agent fitness metrics;
- [ ] versioned prompts/policies;
- [ ] controlled mutations;
- [ ] evaluation and rollback;
- [ ] promotion of high-performing patterns into knowledge.

### Phase 8 — Optional fine-tuning / LoRA

Once enough high-quality examples and real outcomes exist, NEXUS may export curated datasets for optional fine-tuning.

Frequent operational facts should remain in memory/RAG instead of requiring constant model retraining.

## Safety model

Autonomy does not mean unrestricted access.

The project is being designed around:

- explicit capability enable/disable flags;
- centralized wallet and spending limits;
- emergency reserve limits;
- API-key protected external endpoints;
- audit logs;
- agent-specific capability boundaries;
- knowledge-scope isolation;
- allowlisted integrations;
- human approval for critical production changes;
- isolated adapters rather than unrestricted execution.

The current multi-agent layer does **not** grant arbitrary shell, filesystem, network or source-code execution privileges to specialized agents.

The evolution engine also remains separate from the new Agent Registry. Future specialized-agent evolution should use versioned prompts/policies, evaluation and rollback instead of uncontrolled source rewriting.

## EasyPanel deployment

The current development deployment uses Docker Compose on EasyPanel.

Required environment variables:

```text
GROQ_API_KEY=...
FORAGE_API_KEY=...
```

EasyPanel Compose file:

```text
docker-compose.easypanel.yaml
```

Internal dashboard/API port:

```text
3000
```

## Repository naming

The repository and Python package still use the technical name `forage` for compatibility.

**NEXUS Agent OS is the project/product identity.**

Keeping the package name unchanged currently protects:

- imports such as `from forage...`;
- the existing CLI;
- Docker builds;
- EasyPanel source configuration;
- deployed service names;
- existing automation paths.

A repository/package migration can be handled later as its own compatibility-safe project.

## Project status

NEXUS is under active development.

A useful description of the current state is:

> **A Forage-derived autonomous survival core with persistent experience learning, now extended with a first multi-agent orchestration and knowledge foundation.**

It is not yet a universal autonomous business operator, automatic Agent Factory, locally hosted intelligence platform or fully self-optimizing production system. Those are explicit roadmap goals.

## Origin and license

NEXUS Agent OS is based on the open-source **Forage** project by **Nerfed-Lab**.

Original project:

`https://github.com/Nerfed-Lab/forage`

This fork preserves the project's MIT license. See [`LICENSE`](LICENSE).

Current fork:

`FreitasCyberSec/forage`
