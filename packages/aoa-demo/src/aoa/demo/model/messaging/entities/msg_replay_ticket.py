# packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_replay_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.messaging.entities.msg_dead_letter_lifecycle import MsgDeadLetterLifecycle
from aoa.demo.model.messaging.entities.outbox_message import OutboxMessageCoreEntity
from aoa.demo.model.messaging.resources.outbox_primary import OutboxPrimaryDatabase


@entity(description="Replay ticket hanging off watermark segment", resource=OutboxPrimaryDatabase)
class ReplayTicketCoreEntity(BaseCoreEntity):
    id: str = Field(description="Ticket id")
    lifecycle: MsgDeadLetterLifecycle = Field(description="Replay lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    message: Annotated[AssociationOne[OutboxMessageCoreEntity], NoInverse()] = Field(
        description="The outbox message this ticket replays, kept in the same messaging database"
    )



ReplayTicketCoreEntity.model_rebuild()
