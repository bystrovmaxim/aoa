# packages/aoa-demo/src/aoa/demo/model/messaging/resources/dlq_store.py
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.sql import SqlResource
from aoa.demo.model.data_sources.messaging_data_source import MessagingDataSource
from aoa.demo.model.messaging.domain import MessagingDomain


@meta(description="Dead-letter queue store (stub)", domain=MessagingDomain)
class MessagingDeadLetterStore(SqlResource[MessagingDataSource]):
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
