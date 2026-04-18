# src/maxitor/samples/messaging/resources/dlq_store.py
from typing import Any

from action_machine.intents.meta.meta_decorator import meta
from action_machine.resources.sql_connection_manager import SqlConnectionManager
from maxitor.samples.messaging.domain import MessagingDomain


@meta(description="Dead-letter queue store (stub)", domain=MessagingDomain)
class MessagingDeadLetterStore(SqlConnectionManager):
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
