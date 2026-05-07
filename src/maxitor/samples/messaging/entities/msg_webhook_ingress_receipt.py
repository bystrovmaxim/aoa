# src/maxitor/samples/messaging/entities/msg_webhook_ingress_receipt.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgWebhookLifecycle


@entity(description="Webhook ingress subgraph root isolated from reconciliation spine", domain=MessagingDomain)
class WebhookIngressReceiptEntity(BaseEntity):
    lifecycle: MsgWebhookLifecycle = Field(description="Receipt lifecycle")
    id: str = Field(description="Receipt id")


WebhookIngressReceiptEntity.model_rebuild()
