# src/maxitor/samples/messaging/entities/msg_dispatcher_cursor_shard.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from maxitor.samples.messaging.entities.outbox_message import OutboxMessageEntity


@entity(description="Dispatcher shard tied to outbox", domain=MessagingDomain)
class DispatcherCursorShardEntity(BaseEntity):
    id: str = Field(description="Cursor id")
    lifecycle: MsgDenseLifecycle = Field(description="Dispatcher cursor lifecycle")

    outbox_row: Annotated[
        AssociationOne[OutboxMessageEntity],
        NoInverse(),
    ] = Rel(description="Parent outbox envelope")  # type: ignore[assignment]


DispatcherCursorShardEntity.model_rebuild()
