# src/maxitor/samples/catalog/dependencies/index_sync.py
"""Клиент поискового индекса (stub)."""


class IndexSyncClient:
    async def upsert_document(self, doc_id: str, fields: dict[str, str]) -> str:
        return f"IDX-{doc_id}"
