# src/maxitor/samples/messaging/entities/msg_webhook_signature_envelope.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgWebhookLifecycle
from maxitor.samples.messaging.entities.msg_webhook_ingress_receipt import WebhookIngressReceiptEntity


@entity(description="Signature verification envelope chained from webhook receipt", domain=MessagingDomain)
class WebhookSignatureEnvelopeEntity(BaseEntity):
    id: str = Field(description="Envelope id")
    lifecycle: MsgWebhookLifecycle = Field(description="Envelope lifecycle")

    receipt: Annotated[
        AssociationOne[WebhookIngressReceiptEntity],
        NoInverse(),
    ] = Rel(description="Ingress receipt linkage")  # type: ignore[assignment]


WebhookSignatureEnvelopeEntity.model_rebuild()
