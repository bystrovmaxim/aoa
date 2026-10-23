# packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_er_cycle_triangle_stub.py
"""
Directed 3-cycle for messaging stubs (alternate narrative from catalog triangle).

Lets ERD tooling show **multiple** cyclic topologies whose interchange shape is identical
but labeling reflects dispatch / watermark vocabulary. One-way links into
``OutboxMessageCoreEntity`` and ``ReplayTicketCoreEntity`` join the hops with mainstream messaging stubs.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseCoreEntity,
    BaseStateEntity,
    Inverse,
    Lifecycle,
    NoInverse,
    value,
)
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.messaging.domain import MessagingDomain
from aoa.demo.model.messaging.entities.msg_replay_ticket import ReplayTicketCoreEntity


class _MsgDirectedCycleSketchStateEntity(BaseStateEntity):
    """Status of the _MsgDirectedCycleSketch axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    OPEN = value(code="open", display_name="Open", sort_order=1)
    SETTLED = value(code="settled", display_name="Settled", sort_order=2)



class _MsgDirectedCycleSketchLifecycle(Lifecycle[_MsgDirectedCycleSketchStateEntity]):
    """Statuses and links of the _MsgDirectedCycleSketchLifecycle axis."""


    _template = Lifecycle().state(_MsgDirectedCycleSketchStateEntity.OPEN).to(_MsgDirectedCycleSketchStateEntity.SETTLED).initial().state(_MsgDirectedCycleSketchStateEntity.SETTLED).final()


@entity(
    description="Messaging triangle hop A (\u2192B, \u2190C reciprocal)",
    domain=MessagingDomain,
)
class MsgDirectedCycleTriangleACoreEntity(BaseCoreEntity):
    id: str = Field(description="Hop A id")
    lifecycle: _MsgDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    follow_b: Annotated[
        AssociationOne[MsgDirectedCycleTriangleBCoreEntity],
        Inverse(MsgDirectedCycleTriangleBCoreEntity, "back_from_a"),
    ] = Field(
        description="Forward hop A\u2192B"
    )

    back_from_c: Annotated[
        AssociationOne[MsgDirectedCycleTriangleCCoreEntity],
        Inverse(MsgDirectedCycleTriangleCCoreEntity, "follow_a"),
    ] = Field(
        description="Return hop C\u2192A pair"
    )


@entity(
    description="Messaging triangle hop B (\u2190A / \u2192C reciprocal)",
    domain=MessagingDomain,
)
class MsgDirectedCycleTriangleBCoreEntity(BaseCoreEntity):
    id: str = Field(description="Hop B id")
    lifecycle: _MsgDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    back_from_a: Annotated[
        AssociationOne[MsgDirectedCycleTriangleACoreEntity],
        Inverse(MsgDirectedCycleTriangleACoreEntity, "follow_b"),
    ] = Field(
        description="Reciprocal B\u2192A"
    )

    follow_c: Annotated[
        AssociationOne[MsgDirectedCycleTriangleCCoreEntity],
        Inverse(MsgDirectedCycleTriangleCCoreEntity, "back_from_b"),
    ] = Field(
        description="Forward hop B\u2192C"
    )

    anchor_replay_ticket: Annotated[
        AssociationOne[ReplayTicketCoreEntity],
        NoInverse(),
    ] = Field(
        description="Ties hop B into watermark replay stub chain"
    )


@entity(
    description="Messaging triangle hop C (\u2190B / \u2192A reciprocal)",
    domain=MessagingDomain,
)
class MsgDirectedCycleTriangleCCoreEntity(BaseCoreEntity):
    id: str = Field(description="Hop C id")
    lifecycle: _MsgDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    traceparent_seed: str = Field(description="Propagation root echoed to downstream carriers")
    dedupe_partition: str = Field(description="Logical inbox partition for idempotent consumers")
    backpressure_budget: int = Field(description="Outstanding backlog units tolerated per lane", ge=0)
    deadline_budget_ms: int = Field(description="End-to-end SLA budget millis", ge=0)
    content_class: str = Field(description="Envelope / codec family moniker")
    retry_policy_slug: str = Field(description="Backoff / retry escalation preset identifier")
    back_from_b: Annotated[
        AssociationOne[MsgDirectedCycleTriangleBCoreEntity],
        Inverse(MsgDirectedCycleTriangleBCoreEntity, "follow_c"),
    ] = Field(
        description="Reciprocal C\u2192B"
    )

    follow_a: Annotated[
        AssociationOne[MsgDirectedCycleTriangleACoreEntity],
        Inverse(MsgDirectedCycleTriangleACoreEntity, "back_from_c"),
    ] = Field(
        description="Forward hop C\u2192A"
    )


MsgDirectedCycleTriangleACoreEntity.model_rebuild()
MsgDirectedCycleTriangleBCoreEntity.model_rebuild()
MsgDirectedCycleTriangleCCoreEntity.model_rebuild()
