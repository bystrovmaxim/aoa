# src/maxitor/samples/messaging/entities/msg_courier_attempt_ledger.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_batching_fence import BatchingFenceEntity
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle


@entity(description="Courier ledger grafted onto reconciliation tail", domain=MessagingDomain)
class CourierAttemptLedgerEntity(BaseEntity):
    id: str = Field(description="Ledger id")
    lifecycle: MsgDenseLifecycle = Field(description="Courier ledger lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    batching_fence: Annotated[
        AssociationOne[BatchingFenceEntity],
        NoInverse(),
    ] = Rel(description="Owning batch coordination fence row")  # type: ignore[assignment]


CourierAttemptLedgerEntity.model_rebuild()
