# packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_mesh_courier_replay.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.messaging.entities.msg_dead_letter_lifecycle import MsgDeadLetterLifecycle
from aoa.demo.model.messaging.entities.msg_replay_ticket import ReplayTicketCoreEntity
from aoa.demo.model.messaging.resources.dlq_store import MessagingDeadLetterStore


@entity(
    description="Short-circuit between courier delivery spine and replay coordination queue", resource=MessagingDeadLetterStore
)
class MsgCourierReplayCorrelateCoreEntity(BaseCoreEntity):
    id: str = Field(description="Correlator id")
    lifecycle: MsgDeadLetterLifecycle = Field(description="Correlator lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")

    replay_ticket: Annotated[
        AssociationOne[ReplayTicketCoreEntity],
        NoInverse(),
    ] = Field(
        description="Replay ticket linkage"
    )


MsgCourierReplayCorrelateCoreEntity.model_rebuild()
