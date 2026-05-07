# src/maxitor/samples/messaging/entities/msg_hop_latency_sample.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from maxitor.samples.messaging.entities.msg_courier_attempt_ledger import CourierAttemptLedgerEntity


@entity(description="Hop latency sample chained from courier ledger", domain=MessagingDomain)
class HopLatencySampleEntity(BaseEntity):
    lifecycle: MsgDenseLifecycle = Field(description="Sample lifecycle")
    id: str = Field(description="Sample id")

    ledger: Annotated[
        AssociationOne[CourierAttemptLedgerEntity],
        NoInverse(),
    ] = Rel(description="Courier ledger parent")  # type: ignore[assignment]


HopLatencySampleEntity.model_rebuild()
