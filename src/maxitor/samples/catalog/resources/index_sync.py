# src/maxitor/samples/catalog/resources/index_sync.py
"""Клиент поискового индекса (stub) для ``@depends`` и ресурсный менеджер для ``connections``."""

from action_machine.intents.meta.meta_decorator import meta
from action_machine.resources.external_service.external_service_manager import (
    ExternalServiceManager,
)
from maxitor.samples.catalog.domain import CatalogDomain


class IndexSyncClient:
    async def upsert_document(self, doc_id: str, fields: dict[str, str]) -> str:
        return f"IDX-{doc_id}"


@meta(
    description="Search index sync client for aspects/connections (stub)",
    domain=CatalogDomain,
)
class IndexSyncClientResource(ExternalServiceManager[IndexSyncClient]):
    pass
