# packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_recipient_device_seen.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.messaging.entities.msg_device_notice_lifecycle import MsgDeviceNoticeLifecycle
from aoa.demo.model.messaging.resources.notification_gateway import NotificationGateway


@entity(description="Recipient device acknowledgement linked to latency hop", resource=NotificationGateway)
class RecipientDeviceSeenCoreEntity(BaseCoreEntity):
    id: str = Field(description="Device row id")
    lifecycle: MsgDeviceNoticeLifecycle = Field(description="Device seen lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")


RecipientDeviceSeenCoreEntity.model_rebuild()
