# src/maxitor/samples/messaging/entities/msg_downstream_watermark.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dedupe_correlation import DedupeCorrelationEntity
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle


@entity(description="Downstream watermark continuing dispatcher reconciliation backbone", domain=MessagingDomain)
class DownstreamWatermarkEntity(BaseEntity):
    id: str = Field(description="Watermark id")
    lifecycle: MsgDenseLifecycle = Field(description="Watermark lifecycle")

    dedupe: Annotated[
        AssociationOne[DedupeCorrelationEntity],
        NoInverse(),
    ] = Rel(description="Upstream dedupe correlation row")  # type: ignore[assignment]


DownstreamWatermarkEntity.model_rebuild()
