"""Scoped persistent knowledge for NEXUS specialized agents."""

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
