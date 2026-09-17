# NEXUS Autonomous Multi-Agent Survival System Design

Date: 2026-09-17
Status: Proposed for implementation

## Purpose

Evolve NEXUS from a single autonomous Forage-derived agent into an autonomous multi-agent system that keeps the original survival/economy/evolution idea while adding specialized agents, shared knowledge, agent-specific memory, future local LLMs, and eventually safe agent creation.

The goal is not to replace Forage's core idea. The goal is to make that idea stronger: instead of one general agent trying to survive alone, NEXUS becomes the coordinating organism that can delegate work to specialized agents, learn from outcomes, accumulate knowledge, and improve how it allocates intelligence, tools, and money.

## Product Vision

NEXUS should eventually behave like an autonomous organization:

```text
                         NEXUS CORE
                  survive + grow + learn
                              |
        +---------------------+---------------------+
        |                     |                     |
     ECONOMY               MEMORY               KNOWLEDGE
 wallet / budget       experiences / reward   global + per-agent
        |                     |                     |
        +---------------------+---------------------+
                              |
                       ORCHESTRATOR
                              |
         +--------------------+--------------------+
         |                    |                    |
    Funnel Agent         DevOps Agent        Research Agent
         |                    |                    |
   own knowledge          own knowledge         own knowledge
   own tools              own tools             own tools
         |                    |                    |
         +--------------------+--------------------+
                              |
                          EXECUTION
                              |
                     cost / revenue / result
                              |
                    reflection + measurement
                              |
                    memory + evolution loop
                              |
                             repeat
```

NEXUS remains the lifecycle owner. Specialized agents are workers with bounded roles, tools, knowledge, permissions, and budgets.

## Current State

The current runtime is centered on `forage.agent.core.Agent`. It already owns:

- the autonomous wake/decide/act/reflect loop;
- wallet, spending limits, ledger, and revenue handling;
- survival logic and runway checks;
- persistent experience memory in SQLite;
- optional ChromaDB indexing for semantic recall;
- genome state and the existing Forage evolution engine;
- the LLM router;
- capabilities, including the custom `funnel_architect` capability;
- dashboard/API startup.

The current runtime therefore already contains the parts we want to preserve: autonomy, survival, memory, economy, and evolution.

The new architecture must add specialization without discarding these strengths.

## Design Principles

1. **Preserve the working Forage core.** No full rewrite.
2. **NEXUS owns the global objective.** Specialized agents do not independently control survival state or the master wallet.
3. **Agents are bounded specialists.** Each agent gets a role, tools, memory scope, knowledge scope, preferred reasoning tier, permissions, and optional budget.
4. **Knowledge is external to model weights.** Operational facts, documents, metrics, and experiences belong in memory/RAG first.
5. **LLMs are replaceable brains.** Agents depend on `LLMRouter`, not on Groq/OpenAI/Ollama directly.
6. **Autonomy is earned progressively.** New autonomous behaviors are enabled only after deterministic tests, evaluation, and rollback paths exist.
7. **Agent creation is controlled.** NEXUS may eventually create agents, but only from approved templates and permission sets.
8. **No destructive migration.** Existing DB data, Chroma experience memory, APIs, EasyPanel deployment, and CLI behavior remain compatible.

## Scope of the Full Vision

The full system is larger than one implementation step. It will be built in phases.

### Phase 1 — Multi-Agent Foundation

Build the minimum architecture required for specialized agents without changing the current autonomous lifecycle.

Includes:

- `SpecializedAgent` contract;
- `AgentRegistry`;
- `NexusOrchestrator`;
- `KnowledgeStore` with global and per-agent scopes;
- first `FunnelAgent` adapter around `FunnelArchitectCapability`;
- funnel API routed internally through the orchestrator;
- compatibility with the current Forage loop.

### Phase 2 — Autonomous Delegation

Connect the existing Forage decision loop to the orchestrator so the NEXUS core can choose a specialist rather than choosing only a capability.

Includes:

- deterministic routing rules first;
- LLM-based schema-constrained routing only when multiple agents exist;
- task-level budgets;
- per-agent result metrics;
- shared outcome recording;
- fallback to legacy capability execution during migration.

### Phase 3 — Knowledge and Learning Expansion

Turn accumulated information into useful operational context.

Includes:

- text/document ingestion;
- chunking and metadata;
- semantic retrieval;
- knowledge promotion from successful experiences;
- metrics summaries;
- per-agent expertise stores;
- global knowledge shared across agents;
- source tracking and deduplication.

### Phase 4 — Local LLM Support

Add a local model without changing the agent architecture.

Includes:

- Ollama or another local OpenAI-compatible provider;
- model/tier selection rules;
- local-first routing for low-cost tasks;
- API fallback for tasks requiring stronger reasoning;
- health checks and provider fallback.

### Phase 5 — Agent Factory

Allow NEXUS to propose and create new specialists when no existing agent is suitable.

The factory does not create arbitrary source code or grant arbitrary permissions.

A generated agent definition contains:

- stable `agent_id`;
- role and objective;
- approved capability set;
- approved tool set;
- memory scope;
- knowledge scope;
- preferred reasoning tier/model policy;
- spending/budget limit;
- permissions;
- evaluation criteria;
- lifespan: permanent or temporary.

### Phase 6 — Teacher / Evaluator

Before a generated agent is registered for production use, a Teacher/Evaluator prepares and tests it.

The evaluator:

1. identifies required knowledge;
2. retrieves or attaches approved knowledge;
3. creates representative test tasks;
4. runs the candidate in a sandboxed execution context;
5. scores results against explicit criteria;
6. approves, rejects, or requests another candidate configuration.

A candidate agent is never assumed competent merely because it was generated.

### Phase 7 — Specialized Evolution

Extend the Forage evolution concept from one global genome to versioned specialist policies/prompts.

Evolution targets should initially be:

- prompts;
- routing policies;
- retrieval strategies;
- model-tier preferences;
- task decomposition policies.

Arbitrary self-modification of source code is out of scope until there is a much stronger sandbox, test, and rollback system.

### Phase 8 — Optional Fine-Tuning / LoRA

Once NEXUS has enough high-quality examples and measurable outcomes, export curated training datasets for optional fine-tuning.

Operational knowledge remains in RAG/memory because frequently changing information should not require weight retraining.

## Selected Architecture

```text
                    EXISTING FORAGE LIFECYCLE
             wake -> survive -> decide -> act -> reflect
                              |
                              v
                         NEXUS CORE
                              |
         +--------------------+--------------------+
         |                    |                    |
      ECONOMY              MEMORY             ORCHESTRATOR
 wallet / ledger      AgentMemory              |
 survival limits      reward/reflection         |
         |                    |             Agent Registry
         |                    |                    |
         |                    |         +----------+----------+
         |                    |         |                     |
         |                    |    Funnel Agent          Future Agents
         |                    |         |                     |
         |                    |         +----------+----------+
         |                    |                    |
         |                    |             Knowledge Store
         |                    |          global + per-agent
         |                    |                    |
         +--------------------+--------------------+
                              |
                          LLM ROUTER
                    local / Groq / APIs
                              |
                           EXECUTION
                              |
                     cost / result / revenue
                              |
                     reflection + metrics
                              |
                   evolution / better routing
```

## Component Design

### 1. Specialized Agent Contract

A specialized agent represents a role, not a separate process.

Required metadata:

- `agent_id`: stable machine ID;
- `name`: display name;
- `role`: operating purpose;
- `memory_scope`: knowledge namespace;
- `capabilities`: capability IDs available to the agent;
- `preferred_tier`: default LLM reasoning tier;
- `permissions`: approved classes of action;
- optional `budget_policy`;
- `execute(task, context)` returning a normalized outcome.

Agents receive dependencies through construction. They do not directly own provider credentials or the master wallet.

### 2. Agent Registry

Responsibilities:

- register agents by unique ID;
- reject duplicate IDs;
- fetch an agent by ID;
- list agents;
- expose role/capability metadata;
- expose whether an agent is enabled;
- later support temporary agents and versioned agent definitions.

The registry performs no LLM calls.

### 3. NEXUS Orchestrator

Responsibilities:

1. receive a task;
2. choose or validate the target agent;
3. retrieve relevant global knowledge;
4. retrieve relevant agent knowledge;
5. construct execution context;
6. enforce task budget/permissions;
7. invoke the agent;
8. normalize the result;
9. audit the action;
10. record metrics and useful knowledge/experience.

Phase 1 uses explicit routing. Autonomous routing comes later.

### 4. Funnel Agent

The first specialist wraps the existing `FunnelArchitectCapability`.

The existing capability remains the implementation that creates FlowSpec. The new Funnel Agent adds:

- specialist identity;
- funnel-specific memory scope;
- retrieved knowledge context;
- orchestrator compatibility;
- future metrics and model policy.

No existing funnel behavior is removed.

### 5. Knowledge Store

The knowledge layer is distinct from Forage experience memory.

Scopes:

- `global` — visible to all specialists;
- `agent:<agent_id>` — private to one specialist unless promoted;
- later `task:<task_id>` — short-lived task context;
- later `project:<project_id>` — project-specific shared knowledge.

Suggested persistent schema:

```text
knowledge_items
- id
- scope
- kind
- title
- content
- metadata_json
- source
- embedding_id
- created_at
- updated_at
```

SQLite is authoritative. ChromaDB is optional for semantic retrieval. Vector-index failure must not take the system down.

### 6. Relationship Between Memory, Knowledge, and Evolution

The system intentionally keeps separate concepts:

**AgentMemory**

Stores what happened:

- action;
- outcome;
- reward;
- context;
- reflection;
- success/failure history.

This remains part of the original Forage learning loop.

**KnowledgeStore**

Stores what the system knows:

- instructions;
- domain knowledge;
- successful patterns;
- documents;
- reusable facts;
- metrics summaries;
- agent expertise.

**Evolution**

Uses outcomes and fitness signals to improve behavior/policies over time.

A future promotion process may convert high-value experiences into durable knowledge, but not every experience should become permanent knowledge.

### 7. LLM Router

`LLMRouter` remains the only model abstraction.

Agents ask for reasoning quality/tier, not vendor names.

Future policy example:

```text
routine     -> local model
important   -> local strong model or Groq
complex     -> Groq/OpenAI/etc.
critical    -> strongest approved provider
```

This makes local LLM adoption a provider/configuration change instead of an agent rewrite.

### 8. Global Economy and Budgets

There is one master economy controlled by NEXUS.

Specialized agents do not receive independent unrestricted wallets.

Instead:

```text
NEXUS master wallet
    |
    +-- Funnel task budget
    +-- Research task budget
    +-- DevOps task budget
```

Budget enforcement remains centralized so multiple agents cannot independently overspend.

Future routing can use cost efficiency as one metric when choosing agents/models.

### 9. Agent Factory

When autonomous creation is eventually enabled, the decision flow is:

```text
new task
   |
existing suitable agent?
   | yes -> use it
   |
   no
   |
reusable domain or one-off task?
   | reusable -> propose permanent specialist
   | one-off  -> propose temporary specialist
   |
Agent Factory creates bounded definition
   |
Teacher/Evaluator prepares + tests candidate
   |
pass threshold?
   | no -> reject/revise
   | yes -> register
   |
execute task
```

The Agent Factory may only select from approved capabilities, tools, permissions, and model policies.

It cannot invent unrestricted shell/network/filesystem access.

### 10. Teacher / Evaluator

The evaluator uses explicit test cases and metrics rather than self-declared confidence.

Example for a future DevOps candidate:

- interpret a known container failure log;
- propose a safe diagnosis;
- generate a valid Docker Compose change;
- identify a rollback path;
- avoid unsupported destructive actions.

Evaluation produces a score plus failure reasons. Registration requires the configured threshold.

## Autonomous Survival Flow

The final target behavior is:

```text
1. WAKE
2. CHECK SURVIVAL / WALLET / RUNWAY
3. REVIEW CURRENT GOALS AND OPPORTUNITIES
4. RETRIEVE RELEVANT MEMORY + KNOWLEDGE
5. CHOOSE SPECIALIST OR IDLE
6. ALLOCATE TASK BUDGET
7. EXECUTE
8. MEASURE COST / REVENUE / SUCCESS
9. REFLECT
10. STORE EXPERIENCE
11. PROMOTE USEFUL KNOWLEDGE WHEN JUSTIFIED
12. UPDATE AGENT/MODEL PERFORMANCE METRICS
13. EVOLVE POLICIES WHEN ENABLED
14. SLEEP
```

This preserves the original Forage survival experiment while making the available intelligence modular and expandable.

## Compatibility Rules

The following must remain true throughout the migration:

- `forage start` continues to work;
- current `config.yaml` remains valid;
- `funnel_architect: true` remains valid;
- `/api/funnel/analyze` keeps its current request/response contract;
- `FORAGE_API_KEY` remains valid;
- current SQLite data remains readable;
- current Chroma `experiences` collection remains untouched;
- wallet, ledger, survival, organism, genome, and existing evolution remain available;
- evolution remains disabled/enabled only by explicit configuration;
- Docker/EasyPanel service names do not change during this migration;
- package/import name `forage` remains unchanged for compatibility;
- repository renaming is a separate future operation.

## Safety and Autonomy Boundaries

NEXUS should become more autonomous without becoming unbounded.

Rules:

- no arbitrary permissions for generated agents;
- no arbitrary source-code self-rewrite in the early architecture;
- all agent actions are auditable;
- budgets are centralized;
- dangerous/destructive actions require stronger permission policies;
- agent creation uses approved templates/capabilities;
- generated agents are evaluated before production registration;
- model/provider failures never silently grant broader permissions;
- Chroma/RAG failures degrade gracefully;
- evolution changes are versioned and reversible before they are allowed to affect production behavior.

## Proposed Package Layout

```text
forage/
├── agent/                         # existing Forage runtime preserved
├── capabilities/                  # existing capabilities preserved
├── orchestration/
│   ├── __init__.py
│   ├── base.py                    # agent/task/result contracts
│   ├── registry.py                # AgentRegistry
│   ├── orchestrator.py            # NexusOrchestrator
│   ├── routing.py                 # future autonomous routing
│   ├── factory.py                 # future Agent Factory
│   ├── evaluator.py               # future Teacher/Evaluator
│   └── agents/
│       ├── __init__.py
│       └── funnel.py              # first specialist
├── knowledge/
│   ├── __init__.py
│   ├── store.py                   # SQLite + optional Chroma
│   ├── retrieval.py               # future retrieval policy
│   └── ingestion.py               # future text/file ingestion
└── infra/
    ├── database.py                # additive schema changes only
    ├── llm.py                     # model abstraction
    └── dashboard.py               # API integration
```

## Phase 1 Testing Strategy

Implementation is test-driven.

Minimum Phase 1 tests:

1. Registry registers and retrieves an agent.
2. Duplicate agent IDs are rejected.
3. Orchestrator executes an explicit registered agent.
4. Unknown agent IDs fail predictably.
5. Global knowledge is retrievable by an agent.
6. Agent-specific knowledge is isolated from other agent scopes.
7. Chroma failure does not prevent SQLite-backed operation.
8. Funnel Agent delegates to Funnel Architect and preserves normalized output.
9. `/api/funnel/analyze` keeps the current auth and response contract.
10. Existing `AgentMemory` behavior remains unchanged.
11. Existing autonomous core can still load `funnel_architect` directly during compatibility migration.
12. Existing wallet/survival/evolution configuration remains unaffected by the new modules.

No Phase 1 test requires a live Groq call. LLM behavior is mocked in unit tests.

## Implementation Order

Only Phase 1 is implemented in the first code change set.

1. Add registry and knowledge tests.
2. Add the additive knowledge table.
3. Add `KnowledgeStore`.
4. Add specialized-agent contracts.
5. Add `AgentRegistry`.
6. Add `NexusOrchestrator`.
7. Add `FunnelAgent` adapter.
8. Route the existing funnel API through the orchestrator internally.
9. Run regression tests for core, memory, wallet, survival, API, and current funnel behavior.
10. Update README to reflect implemented behavior, not future behavior as if already complete.

Phase 2 begins only after Phase 1 is stable.

## Success Criteria for Phase 1

Phase 1 is complete when:

- NEXUS can register at least one specialist (`funnel`);
- the orchestrator can execute that specialist explicitly;
- global and per-agent knowledge can be stored/retrieved persistently;
- the funnel API works through the orchestrator without changing its external contract;
- the original Forage autonomous loop still works;
- original experience learning still works;
- wallet/survival/evolution state is preserved;
- no local LLM is required;
- adding a local provider later does not require rewriting the specialist architecture.

## Long-Term Success Criteria

The full NEXUS vision is reached when the system can safely:

- survive under centralized economic constraints;
- choose among specialized agents based on task and measured performance;
- share global knowledge while preserving agent-specific expertise;
- use local and remote LLMs interchangeably through routing policy;
- ingest and retrieve large knowledge collections;
- learn from cost, success, revenue, and failure signals;
- propose bounded new agents when existing ones are unsuitable;
- evaluate candidate agents before registration;
- evolve prompts/policies with versioning and rollback;
- optionally export high-quality datasets for fine-tuning/LoRA;
- remain auditable and controllable by the owner throughout the process.
