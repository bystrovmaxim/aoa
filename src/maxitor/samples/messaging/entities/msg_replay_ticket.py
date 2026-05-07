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

    watermark: Annotated[
        AssociationOne[DownstreamWatermarkEntity],
        NoInverse(),
    ] = Rel(description="Parent watermark row")  # type: ignore[assignment]


ReplayTicketEntity.model_rebuild()
