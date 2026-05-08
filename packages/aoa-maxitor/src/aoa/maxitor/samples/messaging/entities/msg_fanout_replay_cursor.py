# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/entities/msg_fanout_replay_cursor.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.messaging.domain import MessagingDomain
from aoa.maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from aoa.maxitor.samples.messaging.entities.msg_webhook_signature_envelope import WebhookSignatureEnvelopeEntity


@entity(description="Fanout replay cursor on verified webhook signatures", domain=MessagingDomain)
class FanoutReplayCursorEntity(BaseEntity):
    id: str = Field(description="Cursor id")
    lifecycle: MsgDenseLifecycle = Field(description="Cursor lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    signature_envelope: Annotated[
        AssociationOne[WebhookSignatureEnvelopeEntity],
        NoInverse(),
    ] = Rel(description="Verified webhook signature row")  # type: ignore[assignment]


FanoutReplayCursorEntity.model_rebuild()
