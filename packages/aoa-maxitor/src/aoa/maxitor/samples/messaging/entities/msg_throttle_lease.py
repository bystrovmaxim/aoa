# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/entities/msg_throttle_lease.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.messaging.domain import MessagingDomain
from aoa.maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from aoa.maxitor.samples.messaging.entities.msg_replay_ticket import ReplayTicketEntity


@entity(description="Throttle lease chaining from replay facilitation row", domain=MessagingDomain)
class ThrottleLeaseEntity(BaseEntity):
    id: str = Field(description="Lease id")
    lifecycle: MsgDenseLifecycle = Field(description="Throttle lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    replay_ticket: Annotated[
        AssociationOne[ReplayTicketEntity],
        NoInverse(),
    ] = Rel(description="Upstream replay ticket")  # type: ignore[assignment]


ThrottleLeaseEntity.model_rebuild()
