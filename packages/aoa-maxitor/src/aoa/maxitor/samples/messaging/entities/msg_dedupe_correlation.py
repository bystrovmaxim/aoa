# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/entities/msg_dedupe_correlation.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.messaging.domain import MessagingDomain
from aoa.maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from aoa.maxitor.samples.messaging.entities.msg_dispatcher_cursor_shard import DispatcherCursorShardEntity


@entity(description="Dedupe correlation chaining from dispatcher watermark", domain=MessagingDomain)
class DedupeCorrelationEntity(BaseEntity):
    id: str = Field(description="Dedupe id")
    lifecycle: MsgDenseLifecycle = Field(description="Dedupe lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    dispatcher_cursor: Annotated[
        AssociationOne[DispatcherCursorShardEntity],
        NoInverse(),
    ] = Rel(description="Owning dispatcher shard")  # type: ignore[assignment]


DedupeCorrelationEntity.model_rebuild()
