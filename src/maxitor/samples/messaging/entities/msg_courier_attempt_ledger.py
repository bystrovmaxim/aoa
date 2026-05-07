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
    lifecycle: MsgDenseLifecycle = Field(description="Courier ledger lifecycle")
    id: str = Field(description="Ledger id")

    batching_fence: Annotated[
        AssociationOne[BatchingFenceEntity],
        NoInverse(),
    ] = Rel(description="Owning batch coordination fence row")  # type: ignore[assignment]


CourierAttemptLedgerEntity.model_rebuild()
