# NEXUS Multi-Agent Foundation Design

Date: 2026-09-17
Status: Proposed for implementation

## Purpose

Evolve NEXUS from a single autonomous Forage-derived agent with pluggable capabilities into a multi-agent orchestration platform while preserving the existing Forage survival, memory, economy, evolution, dashboard, API, and deployment behavior.

This phase establishes the architectural foundation only. It does not add a local LLM yet, does not enable self-evolution by default, and does not replace the current public API contract.

## Current State

The current runtime is centered on `forage.agent.core.Agent`. It owns the lifecycle loop, wallet, ledger, memory, survival engine, genome, organism, LLM router, and enabled capabilities. The main loop decides one capability, executes it, stores the outcome as experience, and optionally runs the existing evolution engine.

The current memory implementation stores experiences in SQLite and optionally indexes them in ChromaDB. The current LLM layer already supports provider routing and has an Ollama code path, so a local model can be added later without redesigning the orchestration layer.

The custom `funnel_architect` capability is currently the only NEXUS-specific operational capability enabled in production configuration.

## Goals

1. Preserve existing Forage behavior and data.
2. Add a first-class concept of specialized agents.
3. Add a registry that can discover and address specialized agents by stable ID.
4. Add an orchestrator that routes explicit tasks to specialized agents.
5. Add a persistent knowledge layer with global and per-agent namespaces.
6. Make LLM choice a dependency of the agent, not a hard-coded implementation detail.
7. Keep the existing `/api/funnel/analyze` endpoint compatible.
8. Prepare the system for future local LLMs, RAG, document ingestion, metrics-driven learning, and additional agents.

## Non-Goals for This Phase

- No local model installation or Ollama deployment.
- No automatic document ingestion pipeline.
- No autonomous creation of new agents.
- No autonomous code rewriting.
- No enabling `evolution.enabled` by default.
- No replacement of `forage.agent.core.Agent` with a new runtime.
- No repository/package rename.
- No breaking changes to EasyPanel, Docker, current environment variables, or `/api/funnel/analyze`.

## Approaches Considered

### A. Rewrite the runtime around multi-agent orchestration now

Replace `forage.agent.core.Agent` with a new NEXUS runtime and move survival/evolution logic into the new core.

Advantages: clean conceptual architecture.

Disadvantages: highest regression risk; likely to break existing state, wallet, lifecycle, dashboard, and deployed behavior. Too much change for the current maturity level.

### B. Compatibility-layer migration — selected

Keep the existing Forage runtime as the lifecycle owner and introduce multi-agent orchestration beside it. Specialized agents wrap capabilities and shared services. Existing entry points continue to work while new entry points use the orchestrator.

Advantages: preserves working behavior, supports incremental migration, and gives a clear path to local LLMs and additional agents.

Disadvantages: the system temporarily contains both legacy direct-capability execution and orchestrated execution.

### C. Independent agent microservices

Run each specialized agent in a separate container/service with network APIs.

Advantages: strong isolation and independent scaling.

Disadvantages: unnecessary operational complexity now; shared memory, auth, deployment, and coordination would become harder before the agent set is large enough to justify it.

## Selected Architecture

```text
                         NEXUS RUNTIME
                              |
                Existing Forage Lifecycle Core
                              |
                    +---------+---------+
                    |                   |
             Legacy capability      NEXUS Orchestrator
                 execution                |
                                      Agent Registry
                                          |
                           +--------------+--------------+
                           |                             |
                      Funnel Agent                 Future Agents
                           |                    DevOps / Data / etc.
                    Funnel Architect
                           |
                           +--------------+
                                          |
                                  Shared Services
                         +----------------+----------------+
                         |                |                |
                    LLM Router       Knowledge Store   Audit/Safety
                         |                |
                 APIs / Local LLM   Global + Agent scopes
```

The existing runtime remains responsible for survival, economy, scheduling, genome state, experience memory, and optional evolution. NEXUS orchestration becomes a task-routing layer rather than a replacement runtime.

## Components

### 1. Specialized Agent Contract

Add a small interface for specialized agents. A specialized agent represents a role, not a separate process.

Each agent exposes:

- `agent_id`: stable machine-readable ID, for example `funnel`.
- `name`: human-readable name.
- `role`: purpose and operating boundary.
- `memory_scope`: namespace used for agent-specific knowledge.
- `capabilities`: capability IDs owned by the agent.
- `preferred_tier`: default LLM reasoning tier, not a hard-coded vendor/model.
- `execute(task, context)`: executes one task and returns a normalized outcome.

The contract must not depend directly on Groq, OpenAI, or Ollama. It receives the shared `LLMRouter` and other dependencies through construction.

### 2. Agent Registry

Add a registry responsible only for registration and lookup.

Required operations:

- register an agent by unique `agent_id`;
- reject duplicate IDs;
- fetch an agent by ID;
- list registered agents;
- inspect which capabilities an agent owns.

The registry does not make LLM calls and does not execute business logic.

### 3. NEXUS Orchestrator

Add an orchestrator that coordinates task execution.

Phase-one routing is deterministic:

- explicit `agent_id` routes directly to that agent;
- existing funnel API routes to `funnel`;
- unknown or disabled agent IDs fail clearly instead of silently selecting another agent.

Automatic LLM-based routing is deferred until there are at least two production agents. This avoids paying for routing decisions that currently provide no value.

The orchestrator responsibilities are:

1. validate the requested agent;
2. retrieve relevant global and agent knowledge;
3. construct an execution context;
4. invoke the specialized agent;
5. record a structured audit event;
6. store useful execution knowledge/experience when appropriate;
7. return a normalized result.

### 4. Funnel Agent Adapter

Create the first specialized agent as an adapter around the existing `FunnelArchitectCapability`.

The capability remains the implementation that generates FlowSpec. The Funnel Agent adds role identity, memory scope, retrieved knowledge context, and orchestrator integration.

The existing `FunnelArchitectCapability` is not deleted in this phase.

### 5. Knowledge Layer

Add a separate knowledge subsystem rather than modifying the existing Forage experience-memory table in place.

The existing `AgentMemory` remains authoritative for the original Forage learning loop. This prevents migration risk and preserves historical data.

The new knowledge layer stores reusable knowledge such as:

- user-provided facts and instructions;
- reusable operating rules;
- successful patterns;
- agent-specific domain knowledge;
- future document chunks;
- future metrics summaries.

Namespaces:

- `global`: visible to all specialized agents;
- `agent:<agent_id>`: visible only to that specialized agent unless explicitly promoted.

Persistence:

- SQLite is the authoritative store;
- ChromaDB is an optional semantic index;
- a Chroma failure must not make the main request fail;
- if vector search is unavailable, exact/recent SQLite retrieval remains available.

Suggested table:

```text
knowledge_items
- id
- scope
- kind
- title
- content
- metadata_json
- embedding_id
- created_at
- updated_at
```

The first implementation supports text insertion and semantic retrieval. File/PDF ingestion is a later phase.

### 6. Memory and Learning Relationship

The system will intentionally have two memory layers:

1. `AgentMemory`: existing Forage experience loop used for action, outcome, reward, reflection, success-rate calculations, and evolution fitness.
2. `KnowledgeStore`: NEXUS shared/per-agent semantic knowledge used as context by specialized agents.

They solve different problems and must not be conflated.

Future work can promote high-value Forage experiences into NEXUS knowledge, but phase one will not automatically copy every experience.

### 7. LLM Architecture

The existing `LLMRouter` remains the single LLM abstraction.

Specialized agents request a reasoning tier; they do not directly call a provider.

This preserves the future path:

```text
routine task  -> local Ollama model
important     -> stronger local model or Groq
complex       -> Groq/OpenAI/etc.
critical      -> strongest configured provider
```

Adding a local LLM later should therefore be primarily configuration/deployment work plus provider validation, not an agent rewrite.

## Data Flow

Example for the existing funnel endpoint after migration:

```text
POST /api/funnel/analyze
        |
        v
API-key validation
        |
        v
NexusOrchestrator.execute(agent_id="funnel", task=...)
        |
        +--> Registry -> FunnelAgent
        |
        +--> KnowledgeStore.search("global")
        |
        +--> KnowledgeStore.search("agent:funnel")
        |
        v
FunnelAgent
        |
        v
FunnelArchitectCapability
        |
        v
LLMRouter
        |
        v
FlowSpec result
        |
        +--> audit log
        +--> optional knowledge/experience record
        v
same API response shape as today
```

## Compatibility Rules

The implementation must preserve all of the following:

- `forage start` continues to start the existing runtime.
- `config.yaml` remains valid.
- `funnel_architect: true` remains the feature flag for the current funnel function.
- `/api/funnel/analyze` keeps its current request and response shape.
- `FORAGE_API_KEY` remains the API authentication variable.
- existing SQLite data remains readable.
- existing Chroma `experiences` collection remains untouched.
- the existing Forage evolution engine remains available and disabled/enabled only by current configuration.
- the Docker/EasyPanel service names and package imports remain unchanged.

## Error Handling

- Duplicate agent registration: fail during startup with a clear configuration/programming error.
- Unknown agent ID: return a controlled orchestration error; never route randomly.
- Disabled agent/capability: return a controlled disabled error.
- Specialized-agent exception: audit the type and return a normalized failure without leaking secrets.
- Knowledge semantic-index failure: log warning and continue with SQLite/no semantic context.
- LLM/provider failure: keep existing router behavior and surface a normalized agent failure.
- Knowledge write failure after a successful business action: log it, but do not change the already-completed business result to failure unless SQLite durability itself is required for that operation.

## Safety and Autonomy Boundaries

This phase preserves explicit capability boundaries.

Specialized agents may only use dependencies and capabilities registered for them. The orchestrator does not grant arbitrary filesystem, shell, network, or code-execution access.

The existing evolution engine remains separate from the specialized-agent registry. Evolution stays disabled in production until tests and rollback behavior are strong enough to enable it deliberately.

When evolution is eventually extended to specialized agents, mutations should target versioned prompts/policies first, with evaluation and rollback, rather than arbitrary source-code rewriting.

## Proposed Package Layout

```text
forage/
├── agent/                       # existing Forage runtime, preserved
├── capabilities/                # existing capabilities, preserved
├── orchestration/
│   ├── __init__.py
│   ├── base.py                  # SpecializedAgent contract + task/result types
│   ├── registry.py              # AgentRegistry
│   ├── orchestrator.py          # NexusOrchestrator
│   └── agents/
│       ├── __init__.py
│       └── funnel.py            # FunnelAgent adapter
├── knowledge/
│   ├── __init__.py
│   └── store.py                 # SQLite + optional Chroma knowledge store
└── infra/
    ├── database.py              # add knowledge table only
    ├── llm.py                   # remain provider abstraction
    └── dashboard.py             # funnel API migrates to orchestrator
```

## Testing Strategy

Implementation is test-driven.

Minimum tests:

1. Registry registers and retrieves a specialized agent.
2. Duplicate agent IDs are rejected.
3. Orchestrator executes an explicit registered agent.
4. Unknown agent IDs fail predictably.
5. Knowledge global scope is retrievable by an agent.
6. Agent-specific knowledge is isolated from other agent scopes.
7. Chroma failure does not prevent SQLite-backed operation.
8. Funnel Agent delegates to Funnel Architect and preserves its normalized result.
9. `/api/funnel/analyze` keeps the current authentication and response contract.
10. Existing `AgentMemory` tests/behavior remain unchanged.
11. Existing autonomous core can still load `funnel_architect` directly during the compatibility period.

No test in this phase requires a live Groq call. LLM calls must be mocked at unit-test level.

## Migration Sequence

1. Add tests for registry and knowledge namespaces.
2. Add the knowledge table and KnowledgeStore.
3. Add specialized-agent contract and AgentRegistry.
4. Add NexusOrchestrator.
5. Add FunnelAgent adapter around existing FunnelArchitectCapability.
6. Migrate `/api/funnel/analyze` internally to the orchestrator while preserving the external contract.
7. Run regression tests for the existing core, API, and memory behavior.
8. Update README architecture only after implementation behavior matches the design.

The autonomous main loop will continue to execute capabilities directly in this phase. A later, separate design can migrate the main loop itself to agent-level orchestration after at least two specialized agents exist and routing behavior can be meaningfully tested.

## Future Phases Enabled by This Foundation

### Local LLM

Configure Ollama or another local OpenAI-compatible server through `LLMRouter`. Specialized agents remain unchanged.

### Knowledge Ingestion

Add text/file/PDF ingestion, chunking, metadata, deduplication, and source tracking into `KnowledgeStore`.

### Automatic Agent Routing

Once two or more production agents exist, add deterministic rules plus optional schema-constrained LLM routing.

### Metrics-Driven Learning

Store measurable outcomes and promote high-performing patterns into agent knowledge. Use those metrics to influence future decisions.

### Specialized Evolution

Extend the existing Forage evolution concept to versioned agent prompts/policies with evaluation, rollback, and per-agent fitness metrics.

### Fine-Tuning / LoRA

After sufficient high-quality examples exist, export curated datasets for optional model fine-tuning. Operational knowledge remains in RAG/memory because frequent facts should not require retraining model weights.

## Success Criteria

This phase is complete when:

- NEXUS can register at least one specialized agent (`funnel`);
- the orchestrator can execute that agent explicitly;
- global and per-agent knowledge can be stored and retrieved persistently;
- the current funnel API works through the orchestrator with the same external contract;
- the existing Forage autonomous loop, memory, survival, wallet, and evolution configuration remain functional;
- no local LLM is required for the system to continue working;
- adding a future local provider does not require rewriting specialized agents.
