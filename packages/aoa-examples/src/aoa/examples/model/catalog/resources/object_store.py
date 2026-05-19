# packages/aoa-examples/src/aoa/examples/model/catalog/resources/object_store.py
from typing import Any

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.sql import SqlResource
from aoa.examples.model.catalog.domain import CatalogDomain


@meta(description="Media/object store for catalog (stub)", domain=CatalogDomain)
class CatalogObjectStore(SqlResource):
    def __init__(self, rollup: bool = False) -> None:
        super().__init__(rollup=rollup)

    async def open(self) -> None:
        return None

    async def begin(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        return None
