# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/entities/msg_webhook_ingress_receipt.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.messaging.domain import MessagingDomain
from aoa.maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgWebhookLifecycle


@entity(description="Webhook ingress subgraph root isolated from reconciliation spine", domain=MessagingDomain)
class WebhookIngressReceiptEntity(BaseEntity):
    id: str = Field(description="Receipt id")
    lifecycle: MsgWebhookLifecycle = Field(description="Receipt lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")


WebhookIngressReceiptEntity.model_rebuild()
