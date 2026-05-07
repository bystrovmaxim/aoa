# src/maxitor/samples/messaging/entities/msg_recipient_device_seen.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from maxitor.samples.messaging.entities.msg_hop_latency_sample import HopLatencySampleEntity


@entity(description="Recipient device acknowledgement linked to latency hop", domain=MessagingDomain)
class RecipientDeviceSeenEntity(BaseEntity):
    id: str = Field(description="Device row id")
    lifecycle: MsgDenseLifecycle = Field(description="Device seen lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    hop_sample: Annotated[
        AssociationOne[HopLatencySampleEntity],
        NoInverse(),
    ] = Rel(description="Upstream hop sample")  # type: ignore[assignment]


RecipientDeviceSeenEntity.model_rebuild()
