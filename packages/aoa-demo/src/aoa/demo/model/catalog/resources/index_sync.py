# packages/aoa-demo/src/aoa/demo/model/catalog/resources/index_sync.py
"""Search index: a stub client and the gateway the domain reaches it through."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway


class IndexSyncClient:
    async def upsert_document(self, doc_id: str, fields: dict[str, str]) -> str:
        return f"IDX-{doc_id}"


@meta(
    description="Search index sync gateway (stub)",
)
class IndexSyncGateway(BaseGateway):
    """The gateway to the search index: its methods are what the domain asks of it."""

    def __init__(self, client: IndexSyncClient) -> None:
        self._client = client

    async def upsert_document(self, doc_id: str, fields: dict[str, str]) -> str:
        """Ask the search index: upsert document."""
        return await self._client.upsert_document(doc_id, fields)
