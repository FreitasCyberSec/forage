# NEXUS Multi-Agent Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first safe multi-agent foundation to NEXUS: persistent global/per-agent knowledge, a specialized-agent contract and registry, deterministic orchestration, and a Funnel Agent adapter, while preserving the current Forage autonomous runtime and `/api/funnel/analyze` contract.

**Architecture:** Keep `forage.agent.core.Agent` as the lifecycle owner for survival, wallet, memory, genome, organism, and optional evolution. Add a compatibility-layer NEXUS orchestration subsystem beside it: `KnowledgeStore` for reusable semantic knowledge, `AgentRegistry` for specialized agents, `NexusOrchestrator` for deterministic task routing, and `FunnelAgent` as the first adapter around the existing `FunnelArchitectCapability`. The existing dashboard endpoint will call the orchestrator internally without changing its external API.

**Tech Stack:** Python 3.11+, SQLite, ChromaDB, FastAPI, Pydantic, pytest, existing `LLMRouter`, existing `Wallet`, existing `AuditLog`.

**Spec:** `docs/superpowers/specs/2026-09-17-nexus-multi-agent-foundation-design.md`

## Global Constraints

- Preserve `forage start` and the existing `forage.agent.core.Agent` lifecycle.
- Preserve the current `config.yaml` format and `funnel_architect: true` capability flag.
- Preserve `/api/funnel/analyze` request and response shape and `FORAGE_API_KEY` authentication.
- Preserve existing SQLite data and the existing ChromaDB `experiences` collection.
- Keep the existing Forage evolution engine available; do not enable `evolution.enabled` by default.
- Do not rename the repository, Python package, EasyPanel service, Docker service, or existing environment variables.
- No local LLM deployment in this phase; keep `LLMRouter` as the model abstraction.
- No autonomous creation of agents, arbitrary code rewriting, or new shell/filesystem/network privileges in this phase.
- SQLite is authoritative for NEXUS knowledge; ChromaDB is an optional semantic index and must fail open to SQLite-backed behavior.
- No unit test in this phase may require a live Groq call.

---

## File Structure

Files created:

- `forage/knowledge/__init__.py` — exports the NEXUS knowledge API.
- `forage/knowledge/store.py` — SQLite-backed knowledge persistence plus optional Chroma semantic lookup.
- `forage/orchestration/__init__.py` — exports orchestration public types.
- `forage/orchestration/base.py` — specialized-agent contract and normalized execution context.
- `forage/orchestration/registry.py` — registration and lookup of specialized agents.
- `forage/orchestration/orchestrator.py` — deterministic routing plus knowledge retrieval and audit.
- `forage/orchestration/agents/__init__.py` — built-in specialized-agent exports.
- `forage/orchestration/agents/funnel.py` — adapter around `FunnelArchitectCapability`.
- `tests/test_knowledge_store.py` — knowledge persistence, scoping, and fallback tests.
- `tests/test_agent_registry.py` — registry behavior tests.
- `tests/test_orchestrator.py` — routing and context tests.
- `tests/test_funnel_agent.py` — Funnel Agent delegation tests.

Files modified:

- `forage/infra/database.py` — add the additive `knowledge_items` table and indexes.
- `forage/infra/dashboard.py` — build and call the NEXUS orchestrator inside the existing funnel helper.
- `tests/test_funnel_api.py` — assert that the existing API contract still holds with the new internal path.
- `README.md` — mark the multi-agent foundation as implemented only after the code and regression suite pass.

---

### Task 1: Persistent NEXUS Knowledge Store

**Files:**
- Create: `forage/knowledge/__init__.py`
- Create: `forage/knowledge/store.py`
- Modify: `forage/infra/database.py`
- Create: `tests/test_knowledge_store.py`

**Interfaces:**
- Consumes: `NerfedConfig`, `init_db(config)`, `get_connection(config)`.
- Produces: `KnowledgeStore(config)`, `KnowledgeStore.add(...) -> int`, `KnowledgeStore.recent(scopes, limit) -> list[dict]`, `KnowledgeStore.search(query, scopes, limit) -> list[dict]`.

- [ ] **Step 1: Write failing persistence and scope-isolation tests**

Create `tests/test_knowledge_store.py` with the following core cases:

```python
from forage.knowledge.store import KnowledgeStore


def test_add_and_read_global_knowledge(initialized_db):
    store = KnowledgeStore(initialized_db)
    item_id = store.add(
        scope="global",
        kind="rule",
        title="Prefer measurable outcomes",
        content="Always attach a measurable success metric to experiments.",
        metadata={"source": "test"},
    )

    rows = store.recent(["global"], limit=10)

    assert item_id > 0
    assert len(rows) == 1
    assert rows[0]["scope"] == "global"
    assert rows[0]["title"] == "Prefer measurable outcomes"
    assert rows[0]["metadata"] == {"source": "test"}


def test_agent_scope_does_not_leak_to_other_agent(initialized_db):
    store = KnowledgeStore(initialized_db)
    store.add(
        scope="agent:funnel",
        kind="pattern",
        title="Funnel pattern",
        content="Warm-up before checkout.",
    )
    store.add(
        scope="agent:devops",
        kind="pattern",
        title="DevOps pattern",
        content="Rollback before risky migration.",
    )

    rows = store.recent(["global", "agent:funnel"], limit=10)

    assert [row["title"] for row in rows] == ["Funnel pattern"]
    assert all(row["scope"] != "agent:devops" for row in rows)
```

Also add a semantic-fallback test by monkeypatching `_get_collection` to return `None` and asserting `search()` still returns SQLite-backed recent items from only the requested scopes.

- [ ] **Step 2: Run the new tests and verify they fail before implementation**

Run:

```bash
pytest tests/test_knowledge_store.py -v
```

Expected: collection failure because `forage.knowledge` does not exist yet.

- [ ] **Step 3: Add the additive SQLite schema**

Append this table and indexes to `_SCHEMA` in `forage/infra/database.py`:

```sql
CREATE TABLE IF NOT EXISTS knowledge_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT,
    embedding_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_knowledge_scope ON knowledge_items(scope);
CREATE INDEX IF NOT EXISTS idx_knowledge_kind ON knowledge_items(kind);
CREATE INDEX IF NOT EXISTS idx_knowledge_created_at ON knowledge_items(created_at);
```

Do not alter or migrate existing tables.

- [ ] **Step 4: Implement `KnowledgeStore` with SQLite authority and optional Chroma**

Create `forage/knowledge/store.py` with this public shape:

```python
import json
from typing import Iterable

from forage.infra.config import NerfedConfig
from forage.infra.database import get_connection, init_db


class KnowledgeStore:
    COLLECTION_NAME = "nexus_knowledge"

    def __init__(self, config: NerfedConfig):
        self.config = config
        init_db(config)
        self._chroma = None
        self._collection = None
        self._collection_initialized = False

    def _get_collection(self):
        if self._collection_initialized:
            return self._collection
        self._collection_initialized = True
        try:
            import chromadb

            self._chroma = chromadb.PersistentClient(
                path=str(self.config.data_dir / "chromadb")
            )
            self._collection = self._chroma.get_or_create_collection(
                self.COLLECTION_NAME
            )
        except Exception:
            self._collection = None
        return self._collection

    def add(
        self,
        *,
        scope: str,
        kind: str,
        title: str,
        content: str,
        metadata: dict | None = None,
    ) -> int:
        if not scope.strip():
            raise ValueError("scope must not be empty")
        if not content.strip():
            raise ValueError("content must not be empty")

        conn = get_connection(self.config)
        try:
            cursor = conn.execute(
                """INSERT INTO knowledge_items
                   (scope, kind, title, content, metadata_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    scope,
                    kind,
                    title,
                    content,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
            item_id = int(cursor.lastrowid)

            collection = self._get_collection()
            if collection is not None:
                try:
                    collection.add(
                        ids=[str(item_id)],
                        documents=[f"{title}\n{content}"],
                        metadatas=[{"scope": scope, "kind": kind}],
                    )
                    conn.execute(
                        "UPDATE knowledge_items SET embedding_id = ? WHERE id = ?",
                        (str(item_id), item_id),
                    )
                    conn.commit()
                except Exception:
                    pass

            return item_id
        finally:
            conn.close()

    def recent(self, scopes: Iterable[str], limit: int = 10) -> list[dict]:
        scope_list = list(dict.fromkeys(scopes))
        if not scope_list:
            return []
        placeholders = ",".join("?" for _ in scope_list)
        conn = get_connection(self.config)
        try:
            rows = conn.execute(
                f"""SELECT * FROM knowledge_items
                    WHERE scope IN ({placeholders})
                    ORDER BY id DESC LIMIT ?""",
                (*scope_list, limit),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]
        finally:
            conn.close()

    def search(
        self,
        query: str,
        scopes: Iterable[str],
        limit: int = 5,
    ) -> list[dict]:
        scope_list = list(dict.fromkeys(scopes))
        if not scope_list:
            return []

        collection = self._get_collection()
        if collection is None or collection.count() == 0:
            return self.recent(scope_list, limit)

        try:
            result = collection.query(
                query_texts=[query],
                n_results=min(max(limit * 3, limit), collection.count()),
            )
            ids = [int(value) for value in result.get("ids", [[]])[0]]
        except Exception:
            return self.recent(scope_list, limit)

        if not ids:
            return self.recent(scope_list, limit)

        conn = get_connection(self.config)
        try:
            rows = []
            for item_id in ids:
                row = conn.execute(
                    "SELECT * FROM knowledge_items WHERE id = ?",
                    (item_id,),
                ).fetchone()
                if row and row["scope"] in scope_list:
                    rows.append(self._row_to_dict(row))
                if len(rows) >= limit:
                    break
        finally:
            conn.close()

        return rows or self.recent(scope_list, limit)

    @staticmethod
    def _row_to_dict(row) -> dict:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        return item
```

Create `forage/knowledge/__init__.py`:

```python
from forage.knowledge.store import KnowledgeStore

__all__ = ["KnowledgeStore"]
```

- [ ] **Step 5: Run the knowledge tests**

Run:

```bash
pytest tests/test_knowledge_store.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit the knowledge layer**

```bash
git add forage/infra/database.py forage/knowledge tests/test_knowledge_store.py
git commit -m "feat: add scoped NEXUS knowledge store"
```

---

### Task 2: Specialized Agent Contract and Registry

**Files:**
- Create: `forage/orchestration/__init__.py`
- Create: `forage/orchestration/base.py`
- Create: `forage/orchestration/registry.py`
- Create: `tests/test_agent_registry.py`

**Interfaces:**
- Consumes: no runtime-specific provider implementation.
- Produces: `ExecutionContext`, `SpecializedAgent`, `AgentRegistry.register(agent)`, `AgentRegistry.get(agent_id)`, `AgentRegistry.list_agents()`.

- [ ] **Step 1: Write failing registry tests**

Create `tests/test_agent_registry.py`:

```python
import pytest

from forage.orchestration.base import ExecutionContext, SpecializedAgent
from forage.orchestration.registry import AgentRegistry


class StubAgent(SpecializedAgent):
    agent_id = "stub"
    name = "Stub Agent"
    role = "Test routing"
    memory_scope = "agent:stub"
    capabilities = ("stub_capability",)
    preferred_tier = "routine"

    def execute(self, task: dict, context: ExecutionContext) -> dict:
        return {"success": True, "task": task, "context": context}


def test_registry_registers_and_retrieves_agent():
    registry = AgentRegistry()
    agent = StubAgent()

    registry.register(agent)

    assert registry.get("stub") is agent
    assert registry.list_agents() == [agent]


def test_registry_rejects_duplicate_ids():
    registry = AgentRegistry()
    registry.register(StubAgent())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(StubAgent())


def test_registry_unknown_agent_returns_none():
    registry = AgentRegistry()

    assert registry.get("missing") is None
```

- [ ] **Step 2: Run the registry tests and verify they fail**

Run:

```bash
pytest tests/test_agent_registry.py -v
```

Expected: import failure because orchestration modules do not exist.

- [ ] **Step 3: Implement the specialized-agent contract**

Create `forage/orchestration/base.py`:

```python
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
```

- [ ] **Step 4: Implement `AgentRegistry`**

Create `forage/orchestration/registry.py`:

```python
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
```

Create `forage/orchestration/__init__.py`:

```python
from forage.orchestration.base import ExecutionContext, SpecializedAgent
from forage.orchestration.registry import AgentRegistry

__all__ = ["AgentRegistry", "ExecutionContext", "SpecializedAgent"]
```

- [ ] **Step 5: Run registry tests**

```bash
pytest tests/test_agent_registry.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit the agent contract and registry**

```bash
git add forage/orchestration tests/test_agent_registry.py
git commit -m "feat: add NEXUS agent registry"
```

---

### Task 3: Deterministic NEXUS Orchestrator

**Files:**
- Create: `forage/orchestration/orchestrator.py`
- Create: `tests/test_orchestrator.py`
- Modify: `forage/orchestration/__init__.py`

**Interfaces:**
- Consumes: `AgentRegistry`, `KnowledgeStore`, `AuditLog`, `ExecutionContext`.
- Produces: `NexusOrchestrator.execute(agent_id: str, task: dict) -> dict` and `UnknownAgentError`.

- [ ] **Step 1: Write failing orchestrator tests**

Create `tests/test_orchestrator.py`:

```python
import pytest

from forage.knowledge.store import KnowledgeStore
from forage.orchestration.base import ExecutionContext, SpecializedAgent
from forage.orchestration.orchestrator import NexusOrchestrator, UnknownAgentError
from forage.orchestration.registry import AgentRegistry
from forage.safety.audit import AuditLog


class RecordingAgent(SpecializedAgent):
    agent_id = "recording"
    name = "Recording Agent"
    role = "Capture execution context"
    memory_scope = "agent:recording"
    capabilities = ("record",)

    def __init__(self):
        self.last_context = None

    def execute(self, task: dict, context: ExecutionContext) -> dict:
        self.last_context = context
        return {"success": True, "cost": 0, "revenue": 0, "task": task}


def test_orchestrator_routes_explicit_agent_and_supplies_scoped_knowledge(initialized_db):
    store = KnowledgeStore(initialized_db)
    store.add(scope="global", kind="rule", title="Global", content="Global rule")
    store.add(
        scope="agent:recording",
        kind="pattern",
        title="Private",
        content="Agent-only rule",
    )
    store.add(
        scope="agent:other",
        kind="pattern",
        title="Other",
        content="Must not leak",
    )

    registry = AgentRegistry()
    agent = RecordingAgent()
    registry.register(agent)
    orchestrator = NexusOrchestrator(
        registry=registry,
        knowledge=store,
        audit=AuditLog(initialized_db),
    )

    result = orchestrator.execute("recording", {"description": "test task"})

    assert result["success"] is True
    assert [row["title"] for row in agent.last_context.global_knowledge] == ["Global"]
    assert [row["title"] for row in agent.last_context.agent_knowledge] == ["Private"]


def test_orchestrator_rejects_unknown_agent(initialized_db):
    orchestrator = NexusOrchestrator(
        registry=AgentRegistry(),
        knowledge=KnowledgeStore(initialized_db),
        audit=AuditLog(initialized_db),
    )

    with pytest.raises(UnknownAgentError, match="missing"):
        orchestrator.execute("missing", {"description": "test"})
```

- [ ] **Step 2: Run tests and verify they fail**

```bash
pytest tests/test_orchestrator.py -v
```

Expected: import failure for `NexusOrchestrator`.

- [ ] **Step 3: Implement deterministic orchestration**

Create `forage/orchestration/orchestrator.py`:

```python
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
```

Export it from `forage/orchestration/__init__.py`:

```python
from forage.orchestration.orchestrator import NexusOrchestrator, UnknownAgentError
```

and add both names to `__all__`.

- [ ] **Step 4: Run orchestrator tests**

```bash
pytest tests/test_orchestrator.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run registry and knowledge tests together**

```bash
pytest tests/test_agent_registry.py tests/test_knowledge_store.py tests/test_orchestrator.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit the orchestrator**

```bash
git add forage/orchestration tests/test_orchestrator.py
git commit -m "feat: add deterministic NEXUS orchestrator"
```

---

### Task 4: Funnel Agent Adapter

**Files:**
- Create: `forage/orchestration/agents/__init__.py`
- Create: `forage/orchestration/agents/funnel.py`
- Create: `tests/test_funnel_agent.py`

**Interfaces:**
- Consumes: `FunnelArchitectCapability`, `Wallet`, `LLMRouter`, `ExecutionContext`.
- Produces: `FunnelAgent.execute(task, context) -> dict` with the same normalized outcome shape as the capability.

- [ ] **Step 1: Write failing Funnel Agent delegation tests**

Create `tests/test_funnel_agent.py`:

```python
from forage.orchestration.base import ExecutionContext
from forage.orchestration.agents.funnel import FunnelAgent


class FakeCapability:
    def __init__(self):
        self.last_task = None

    def execute(self, task, wallet, llm):
        self.last_task = task
        return {
            "success": True,
            "cost": 0.001,
            "revenue": 0,
            "description": "FlowSpec criado.",
            "artifacts": {"flowspec": {"name": "Test"}},
        }


def test_funnel_agent_delegates_and_includes_retrieved_knowledge():
    capability = FakeCapability()
    agent = FunnelAgent(capability=capability, wallet=object(), llm=object())
    context = ExecutionContext(
        global_knowledge=[{"title": "Global rule", "content": "Measure conversion."}],
        agent_knowledge=[{"title": "Funnel rule", "content": "Warm up before offer."}],
    )

    result = agent.execute(
        {"description": "Create a funnel for a course."},
        context,
    )

    assert result["success"] is True
    assert "Create a funnel for a course." in capability.last_task["description"]
    assert "Measure conversion." in capability.last_task["description"]
    assert "Warm up before offer." in capability.last_task["description"]
```

- [ ] **Step 2: Run the test and verify it fails**

```bash
pytest tests/test_funnel_agent.py -v
```

Expected: import failure for `forage.orchestration.agents.funnel`.

- [ ] **Step 3: Implement the Funnel Agent adapter**

Create `forage/orchestration/agents/funnel.py`:

```python
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
```

Create `forage/orchestration/agents/__init__.py`:

```python
from forage.orchestration.agents.funnel import FunnelAgent

__all__ = ["FunnelAgent"]
```

- [ ] **Step 4: Run the Funnel Agent tests**

```bash
pytest tests/test_funnel_agent.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run the orchestration unit suite**

```bash
pytest tests/test_agent_registry.py tests/test_orchestrator.py tests/test_funnel_agent.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit the Funnel Agent adapter**

```bash
git add forage/orchestration/agents tests/test_funnel_agent.py
git commit -m "feat: add Funnel Agent adapter"
```

---

### Task 5: Route the Existing Funnel API Through NEXUS

**Files:**
- Modify: `forage/infra/dashboard.py`
- Modify: `tests/test_funnel_api.py`

**Interfaces:**
- Consumes: `NexusOrchestrator`, `AgentRegistry`, `KnowledgeStore`, `FunnelAgent`, existing `FunnelArchitectCapability`, `Wallet`, `LLMRouter`, `AuditLog`.
- Produces: unchanged `POST /api/funnel/analyze` external contract.

- [ ] **Step 1: Add an API test that proves the helper now returns the orchestrated Funnel Agent result without changing the response shape**

Extend `tests/test_funnel_api.py` with a focused internal integration test that monkeypatches `_build_nexus_orchestrator` rather than bypassing orchestration:

```python
def test_execute_funnel_architect_routes_to_funnel_agent(config, monkeypatch):
    dashboard._config = config
    config.capabilities.funnel_architect = True

    class FakeOrchestrator:
        def execute(self, agent_id, task):
            assert agent_id == "funnel"
            assert task == {"description": "test funnel"}
            return {
                "success": True,
                "cost": 0.001,
                "revenue": 0,
                "description": "FlowSpec criado.",
                "artifacts": {"flowspec": {"name": "Test Funnel"}},
            }

    monkeypatch.setattr(
        dashboard,
        "_build_nexus_orchestrator",
        lambda: FakeOrchestrator(),
    )

    result = dashboard._execute_funnel_architect("test funnel")

    assert result["artifacts"]["flowspec"]["name"] == "Test Funnel"
```

Keep the existing authentication tests and `test_funnel_analyze_returns_flowspec` unchanged so they continue to verify backward compatibility.

- [ ] **Step 2: Run the funnel API tests and verify the new test fails**

```bash
pytest tests/test_funnel_api.py -v
```

Expected: failure because `_build_nexus_orchestrator` does not exist yet.

- [ ] **Step 3: Replace direct capability construction with an orchestrator builder**

In `forage/infra/dashboard.py`, add:

```python
def _build_nexus_orchestrator():
    if _config is None:
        raise RuntimeError("Dashboard is not initialized")

    from forage.capabilities.funnel_architect import FunnelArchitectCapability
    from forage.economy.ledger import Ledger
    from forage.economy.wallet import Wallet
    from forage.infra.llm import LLMRouter
    from forage.knowledge.store import KnowledgeStore
    from forage.orchestration.agents.funnel import FunnelAgent
    from forage.orchestration.orchestrator import NexusOrchestrator
    from forage.orchestration.registry import AgentRegistry
    from forage.safety.audit import AuditLog
    from forage.safety.limits import SpendingLimiter

    audit = AuditLog(_config)
    llm = LLMRouter(_config, audit)
    limiter = SpendingLimiter(_config)
    ledger = Ledger(_config)
    wallet = Wallet(_config, ledger, limiter)

    registry = AgentRegistry()
    if _config.capabilities.funnel_architect:
        registry.register(
            FunnelAgent(
                capability=FunnelArchitectCapability(_config),
                wallet=wallet,
                llm=llm,
            )
        )

    return NexusOrchestrator(
        registry=registry,
        knowledge=KnowledgeStore(_config),
        audit=audit,
    )
```

Then reduce `_execute_funnel_architect` to:

```python
def _execute_funnel_architect(description: str) -> dict:
    orchestrator = _build_nexus_orchestrator()
    return orchestrator.execute(
        "funnel",
        {"description": description},
    )
```

Keep the endpoint's existing API-key check, `_config is None` check, capability-enabled check, HTTP status mapping, and response serialization unchanged.

- [ ] **Step 4: Run the API compatibility tests**

```bash
pytest tests/test_funnel_api.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run the full new foundation suite**

```bash
pytest \
  tests/test_knowledge_store.py \
  tests/test_agent_registry.py \
  tests/test_orchestrator.py \
  tests/test_funnel_agent.py \
  tests/test_funnel_api.py \
  -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit the API migration**

```bash
git add forage/infra/dashboard.py tests/test_funnel_api.py
git commit -m "feat: route funnel API through NEXUS orchestrator"
```

---

### Task 6: Regression Verification and README State Update

**Files:**
- Modify: `README.md`
- Verify only: existing `forage/agent/core.py`, `forage/agent/memory.py`, `forage/evolution/engine.py`, `forage/infra/llm.py`.

**Interfaces:**
- Consumes: all Phase 1 components.
- Produces: a documented, tested compatibility milestone with no change to the legacy autonomous loop.

- [ ] **Step 1: Run the complete existing test suite before documentation changes**

Run:

```bash
pytest -v
```

Expected: all repository tests PASS. If an unrelated pre-existing failure appears, stop and diagnose it before claiming Phase 1 is complete.

- [ ] **Step 2: Run Ruff on changed Python files**

Run:

```bash
ruff check \
  forage/knowledge \
  forage/orchestration \
  forage/infra/database.py \
  forage/infra/dashboard.py \
  tests/test_knowledge_store.py \
  tests/test_agent_registry.py \
  tests/test_orchestrator.py \
  tests/test_funnel_agent.py \
  tests/test_funnel_api.py
```

Expected: no lint errors.

- [ ] **Step 3: Perform a syntax compilation check**

Run:

```bash
python -m compileall forage tests
```

Expected: command exits with status 0 and reports no syntax failures.

- [ ] **Step 4: Update README to distinguish implemented foundation from future roadmap**

In `README.md`, update the current architecture/status sections so they state that Phase 1 now includes:

```text
Implemented:
- NEXUS Agent Registry
- deterministic NEXUS Orchestrator
- global + per-agent Knowledge Store
- Funnel Agent adapter
- existing Funnel API routed through NEXUS

Preserved:
- Forage autonomous survival loop
- wallet/economy
- AgentMemory experience learning
- genome/evolution subsystem
- Groq/API LLM routing

Next phases:
- automatic agent selection when multiple production agents exist
- document/RAG ingestion
- local LLM validation through Ollama
- Agent Factory + Teacher/Evaluator
- metrics-driven specialized-agent evolution
```

Do not describe Agent Factory, local LLM deployment, autonomous agent creation, or specialized-agent evolution as already implemented.

- [ ] **Step 5: Run a final focused regression after README-only changes**

```bash
pytest tests/test_funnel_api.py tests/test_orchestrator.py tests/test_knowledge_store.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit the documented Phase 1 milestone**

```bash
git add README.md
git commit -m "docs: mark NEXUS multi-agent foundation implemented"
```

---

## Self-Review Checklist

### Spec coverage

- Existing Forage runtime preserved: Task 6 regression verification; no task replaces `Agent`.
- Specialized-agent contract: Task 2.
- Registry: Task 2.
- Deterministic orchestrator: Task 3.
- Global and per-agent knowledge: Task 1 and Task 3.
- Existing Funnel Architect preserved behind an adapter: Task 4.
- Existing funnel API preserved externally and moved internally to orchestration: Task 5.
- LLM provider abstraction preserved: no direct provider dependency is introduced into specialized-agent interfaces.
- Existing experience memory/evolution data preserved: Task 1 adds only a new table and a new Chroma collection.
- Chroma failure fallback: Task 1.
- No live Groq in unit tests: all new tests use fakes/mocks.
- Local LLM, Agent Factory, Teacher/Evaluator, automatic routing, and specialized evolution remain future phases and are not implemented here.

### Type consistency

- `SpecializedAgent.execute(task: dict, context: ExecutionContext) -> dict` is used consistently by registry, orchestrator, and Funnel Agent.
- `KnowledgeStore.search(query: str, scopes: Iterable[str], limit: int = 5) -> list[dict]` is the only semantic retrieval signature used by the orchestrator.
- `NexusOrchestrator.execute(agent_id: str, task: dict) -> dict` is used by the dashboard helper.
- `FunnelAgent.agent_id == "funnel"` matches the dashboard route.

### Safety boundary

- No new arbitrary shell, filesystem, network, or code-execution privilege is introduced.
- Wallet ownership stays centralized in the existing Forage economy layer.
- Evolution remains controlled by existing configuration and is not auto-enabled.
