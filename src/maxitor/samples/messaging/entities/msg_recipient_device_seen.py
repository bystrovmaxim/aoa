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

    hop_sample: Annotated[
        AssociationOne[HopLatencySampleEntity],
        NoInverse(),
    ] = Rel(description="Upstream hop sample")  # type: ignore[assignment]


RecipientDeviceSeenEntity.model_rebuild()
