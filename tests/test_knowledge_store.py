"""Tests for the scoped NEXUS knowledge store."""

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


def test_search_falls_back_to_scoped_sqlite_when_vector_store_unavailable(
    initialized_db,
    monkeypatch,
):
    store = KnowledgeStore(initialized_db)
    monkeypatch.setattr(store, "_get_collection", lambda: None)

    store.add(
        scope="global",
        kind="rule",
        title="Global fallback",
        content="Use durable storage as the source of truth.",
    )
    store.add(
        scope="agent:funnel",
        kind="pattern",
        title="Funnel fallback",
        content="Use a warm-up sequence before the offer.",
    )
    store.add(
        scope="agent:devops",
        kind="pattern",
        title="Private devops knowledge",
        content="This must not leak into funnel retrieval.",
    )

    rows = store.search(
        "warm-up",
        ["global", "agent:funnel"],
        limit=10,
    )

    assert {row["title"] for row in rows} == {
        "Global fallback",
        "Funnel fallback",
    }
    assert all(row["scope"] != "agent:devops" for row in rows)


def test_search_falls_back_when_vector_store_count_fails(initialized_db, monkeypatch):
    store = KnowledgeStore(initialized_db)
    store.add(
        scope="global",
        kind="rule",
        title="Durable fallback",
        content="SQLite remains authoritative.",
    )

    class BrokenCollection:
        def count(self):
            raise RuntimeError("vector store unavailable")

    monkeypatch.setattr(store, "_get_collection", lambda: BrokenCollection())

    rows = store.search("durable", ["global"], limit=5)

    assert [row["title"] for row in rows] == ["Durable fallback"]
