# packages/aoa-demo/src/aoa/demo/model/data_sources/messaging_data_source.py
"""MessagingDataSource — the one database of the transactional outbox and the dead-letter queue."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseDataSource


@meta(description="The messaging database — transactional outbox and dead-letter queue")
class MessagingDataSource(BaseDataSource):
    """A demo database: the resources that name it share one store, and their entities may relate."""
