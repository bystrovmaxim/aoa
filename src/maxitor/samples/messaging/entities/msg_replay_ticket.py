# src/maxitor/samples/messaging/entities/msg_replay_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from maxitor.samples.messaging.entities.msg_downstream_watermark import DownstreamWatermarkEntity


@entity(description="Replay ticket hanging off watermark segment", domain=MessagingDomain)
class ReplayTicketEntity(BaseEntity):
    id: str = Field(description="Ticket id")
    lifecycle: MsgDenseLifecycle = Field(description="Replay lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    watermark: Annotated[
        AssociationOne[DownstreamWatermarkEntity],
        NoInverse(),
    ] = Rel(description="Parent watermark row")  # type: ignore[assignment]

    billing_parse_pass: Annotated[
        AssociationOne["BillingParsePassEntity"],  # noqa: UP037
        NoInverse(),
    ] = Rel(description="Billing parse artifact correlated with replay bookkeeping")  # type: ignore[assignment]


from maxitor.samples.billing.entities.billing_parse_pass import (  # noqa: E402
    BillingParsePassEntity,
)

ReplayTicketEntity.model_rebuild()
