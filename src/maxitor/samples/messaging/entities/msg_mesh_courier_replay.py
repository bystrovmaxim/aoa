# src/maxitor/samples/messaging/entities/msg_mesh_courier_replay.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_courier_attempt_ledger import CourierAttemptLedgerEntity
from maxitor.samples.messaging.entities.msg_dense_lifecycle import MsgDenseLifecycle
from maxitor.samples.messaging.entities.msg_replay_ticket import ReplayTicketEntity


@entity(description="Short-circuit between courier delivery spine and replay coordination queue", domain=MessagingDomain)
class MsgCourierReplayCorrelateEntity(BaseEntity):
    id: str = Field(description="Correlator id")
    lifecycle: MsgDenseLifecycle = Field(description="Correlator lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    courier_ledger: Annotated[
        AssociationOne[CourierAttemptLedgerEntity],
        NoInverse(),
    ] = Rel(description="Courier attempt ledger linkage")  # type: ignore[assignment]

    replay_ticket: Annotated[
        AssociationOne[ReplayTicketEntity],
        NoInverse(),
    ] = Rel(description="Replay ticket linkage")  # type: ignore[assignment]


MsgCourierReplayCorrelateEntity.model_rebuild()
