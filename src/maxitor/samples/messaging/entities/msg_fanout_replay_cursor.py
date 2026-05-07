# src/maxitor/samples/messaging/entities/msg_fanout_replay_cursor.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from maxitor.samples.messaging.entities.msg_webhook_signature_envelope import WebhookSignatureEnvelopeEntity


@entity(description="Fanout replay cursor on verified webhook signatures", domain=MessagingDomain)
class FanoutReplayCursorEntity(BaseEntity):
    id: str = Field(description="Cursor id")
    lifecycle: MsgDenseLifecycle = Field(description="Cursor lifecycle")

    signature_envelope: Annotated[
        AssociationOne[WebhookSignatureEnvelopeEntity],
        NoInverse(),
    ] = Rel(description="Verified webhook signature row")  # type: ignore[assignment]


FanoutReplayCursorEntity.model_rebuild()
