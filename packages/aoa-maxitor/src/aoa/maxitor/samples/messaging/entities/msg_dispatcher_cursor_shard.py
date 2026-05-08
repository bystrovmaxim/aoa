# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/entities/msg_dispatcher_cursor_shard.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.messaging.domain import MessagingDomain
from aoa.maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from aoa.maxitor.samples.messaging.entities.outbox_message import OutboxMessageEntity


@entity(description="Dispatcher shard tied to outbox", domain=MessagingDomain)
class DispatcherCursorShardEntity(BaseEntity):
    id: str = Field(description="Cursor id")
    lifecycle: MsgDenseLifecycle = Field(description="Dispatcher cursor lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    outbox_row: Annotated[
        AssociationOne[OutboxMessageEntity],
        NoInverse(),
    ] = Rel(description="Parent outbox envelope")  # type: ignore[assignment]


DispatcherCursorShardEntity.model_rebuild()
