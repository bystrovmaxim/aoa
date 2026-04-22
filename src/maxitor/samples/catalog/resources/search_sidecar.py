# src/maxitor/samples/catalog/resources/search_sidecar.py
from typing import Any

from action_machine.intents.meta.meta_decorator import meta
from action_machine.resources.sql import SqlManager
from maxitor.samples.catalog.domain import CatalogDomain


@meta(description="Search sidecar index (stub)", domain=CatalogDomain)
class CatalogSearchSidecar(SqlManager):
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
