# src/maxitor/samples/messaging/entities/msg_dedupe_correlation.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from maxitor.samples.messaging.entities.msg_dispatcher_cursor_shard import DispatcherCursorShardEntity


@entity(description="Dedupe correlation chaining from dispatcher watermark", domain=MessagingDomain)
class DedupeCorrelationEntity(BaseEntity):
    lifecycle: MsgDenseLifecycle = Field(description="Dedupe lifecycle")
    id: str = Field(description="Dedupe id")

    dispatcher_cursor: Annotated[
        AssociationOne[DispatcherCursorShardEntity],
        NoInverse(),
    ] = Rel(description="Owning dispatcher shard")  # type: ignore[assignment]


DedupeCorrelationEntity.model_rebuild()
