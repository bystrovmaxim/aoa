# src/maxitor/samples/messaging/resources/outbox_primary.py
from typing import Any

from action_machine.intents.meta import meta
from action_machine.resources.sql import SqlResource
from maxitor.samples.messaging.domain import MessagingDomain


@meta(description="Transactional outbox primary DB (stub)", domain=MessagingDomain)
class OutboxPrimaryDatabase(SqlResource):
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
