# src/maxitor/samples/messaging/entities/msg_mesh_outbox_webhook.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from maxitor.samples.messaging.entities.msg_webhook_signature_envelope import WebhookSignatureEnvelopeEntity
from maxitor.samples.messaging.entities.outbox_message import OutboxMessageEntity


@entity(description="Correlates isolated webhook verification path with transactional outbox rows", domain=MessagingDomain)
class MsgOutboxWebhookCorrelateEntity(BaseEntity):
    id: str = Field(description="Correlator id")
    lifecycle: MsgDenseLifecycle = Field(description="Correlator lifecycle")

    outbox_row: Annotated[
        AssociationOne[OutboxMessageEntity],
        NoInverse(),
    ] = Rel(description="Upstream outbox linkage")  # type: ignore[assignment]

    signature_envelope: Annotated[
        AssociationOne[WebhookSignatureEnvelopeEntity],
        NoInverse(),
    ] = Rel(description="Verified webhook linkage")  # type: ignore[assignment]


MsgOutboxWebhookCorrelateEntity.model_rebuild()
