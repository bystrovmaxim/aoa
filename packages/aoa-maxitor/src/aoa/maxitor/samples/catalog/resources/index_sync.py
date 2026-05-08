# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/resources/index_sync.py
"""Search-index client stub for ``@depends`` and ``connections`` resource manager."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service import ExternalServiceResource
from aoa.maxitor.samples.catalog.domain import CatalogDomain


class IndexSyncClient:
    async def upsert_document(self, doc_id: str, fields: dict[str, str]) -> str:
        return f"IDX-{doc_id}"


@meta(
    description="Search index sync client for aspects/connections (stub)",
    domain=CatalogDomain,
)
class IndexSyncClientResource(ExternalServiceResource[IndexSyncClient]):
    pass
