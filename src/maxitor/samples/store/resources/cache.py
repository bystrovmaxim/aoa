# src/maxitor/samples/store/resources/cache.py
from typing import Any

from action_machine.intents.meta import meta
from action_machine.resources.sql import SqlResource
from maxitor.samples.store.domain import StoreDomain


@meta(description="Session cache (stub)", domain=StoreDomain)
class StorefrontSessionCache(SqlResource):
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
