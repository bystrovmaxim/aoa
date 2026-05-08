# src/maxitor/samples/messaging/entities/msg_hop_latency_sample.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_courier_attempt_ledger import CourierAttemptLedgerEntity
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle


@entity(description="Hop latency sample chained from courier ledger", domain=MessagingDomain)
class HopLatencySampleEntity(BaseEntity):
    id: str = Field(description="Sample id")
    lifecycle: MsgDenseLifecycle = Field(description="Sample lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    ledger: Annotated[
        AssociationOne[CourierAttemptLedgerEntity],
        NoInverse(),
    ] = Rel(description="Courier ledger parent")  # type: ignore[assignment]


HopLatencySampleEntity.model_rebuild()
