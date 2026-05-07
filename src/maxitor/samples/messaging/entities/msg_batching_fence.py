# src/maxitor/samples/messaging/entities/msg_batching_fence.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from maxitor.samples.messaging.entities.msg_throttle_lease import ThrottleLeaseEntity


@entity(description="Batching fence tail on reconciliation filament", domain=MessagingDomain)
class BatchingFenceEntity(BaseEntity):
    id: str = Field(description="Fence id")
    lifecycle: MsgDenseLifecycle = Field(description="Batch fence lifecycle")

    throttle_lease: Annotated[
        AssociationOne[ThrottleLeaseEntity],
        NoInverse(),
    ] = Rel(description="Parent throttle lease row")  # type: ignore[assignment]


BatchingFenceEntity.model_rebuild()
