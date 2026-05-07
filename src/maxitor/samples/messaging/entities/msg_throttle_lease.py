# src/maxitor/samples/messaging/entities/msg_throttle_lease.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from maxitor.samples.messaging.entities.msg_replay_ticket import ReplayTicketEntity


@entity(description="Throttle lease chaining from replay facilitation row", domain=MessagingDomain)
class ThrottleLeaseEntity(BaseEntity):
    id: str = Field(description="Lease id")
    lifecycle: MsgDenseLifecycle = Field(description="Throttle lifecycle")

    replay_ticket: Annotated[
        AssociationOne[ReplayTicketEntity],
        NoInverse(),
    ] = Rel(description="Upstream replay ticket")  # type: ignore[assignment]


ThrottleLeaseEntity.model_rebuild()
