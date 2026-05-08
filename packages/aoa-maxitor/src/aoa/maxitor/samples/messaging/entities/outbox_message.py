# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/entities/outbox_message.py
"""Minimal entity for the messaging-domain vertex in the graph."""

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.messaging.domain import MessagingDomain
from aoa.maxitor.samples.messaging.entities.outbox_lifecycle import OutboxMessageLifecycle


@entity(description="Transactional outbox row (sample)", domain=MessagingDomain)
class OutboxMessageEntity(BaseEntity):
    id: str = Field(description="Message id")
    lifecycle: OutboxMessageLifecycle = Field(description="Outbox message lifecycle")
    topic: str = Field(description="Routing topic")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")


OutboxMessageEntity.model_rebuild()
