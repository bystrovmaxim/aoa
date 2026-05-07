# src/maxitor/samples/messaging/entities/msg_er_cycle_triangle_stub.py
"""
Directed 3-cycle for messaging stubs (alternate narrative from catalog triangle).

Lets ERD tooling show **multiple** cyclic topologies whose interchange shape is identical
but labeling reflects dispatch / watermark vocabulary. One-way links into
``OutboxMessageEntity`` and ``ReplayTicketEntity`` join the hops with mainstream messaging stubs.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, Inverse, Lifecycle, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.entities.msg_replay_ticket import ReplayTicketEntity


class _MsgDirectedCycleSketchLifecycle(Lifecycle):
    _template = Lifecycle().state("open", "Open").to("settled").initial().state("settled", "Settled").final()


@entity(
    description="Messaging triangle hop A (\u2192B, \u2190C reciprocal)",
    domain=MessagingDomain,
)
class MsgDirectedCycleTriangleAEntity(BaseEntity):
    id: str = Field(description="Hop A id")
    lifecycle: _MsgDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    follow_b: Annotated[
        AssociationOne[MsgDirectedCycleTriangleBEntity],
        Inverse(MsgDirectedCycleTriangleBEntity, "back_from_a"),
    ] = Rel(description="Forward hop A\u2192B")  # type: ignore[assignment]

    back_from_c: Annotated[
        AssociationOne[MsgDirectedCycleTriangleCEntity],
        Inverse(MsgDirectedCycleTriangleCEntity, "follow_a"),
    ] = Rel(description="Return hop C\u2192A pair")  # type: ignore[assignment]


@entity(
    description="Messaging triangle hop B (\u2190A / \u2192C reciprocal)",
    domain=MessagingDomain,
)
class MsgDirectedCycleTriangleBEntity(BaseEntity):
    id: str = Field(description="Hop B id")
    lifecycle: _MsgDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    back_from_a: Annotated[
        AssociationOne[MsgDirectedCycleTriangleAEntity],
        Inverse(MsgDirectedCycleTriangleAEntity, "follow_b"),
    ] = Rel(description="Reciprocal B\u2192A")  # type: ignore[assignment]

    follow_c: Annotated[
        AssociationOne[MsgDirectedCycleTriangleCEntity],
        Inverse(MsgDirectedCycleTriangleCEntity, "back_from_b"),
    ] = Rel(description="Forward hop B\u2192C")  # type: ignore[assignment]

    anchor_replay_ticket: Annotated[
        AssociationOne[ReplayTicketEntity],
        NoInverse(),
    ] = Rel(description="Ties hop B into watermark replay stub chain")  # type: ignore[assignment]


@entity(
    description="Messaging triangle hop C (\u2190B / \u2192A reciprocal)",
    domain=MessagingDomain,
)
class MsgDirectedCycleTriangleCEntity(BaseEntity):
    id: str = Field(description="Hop C id")
    lifecycle: _MsgDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    back_from_b: Annotated[
        AssociationOne[MsgDirectedCycleTriangleBEntity],
        Inverse(MsgDirectedCycleTriangleBEntity, "follow_c"),
    ] = Rel(description="Reciprocal C\u2192B")  # type: ignore[assignment]

    follow_a: Annotated[
        AssociationOne[MsgDirectedCycleTriangleAEntity],
        Inverse(MsgDirectedCycleTriangleAEntity, "back_from_c"),
    ] = Rel(description="Forward hop C\u2192A")  # type: ignore[assignment]


MsgDirectedCycleTriangleAEntity.model_rebuild()
MsgDirectedCycleTriangleBEntity.model_rebuild()
MsgDirectedCycleTriangleCEntity.model_rebuild()
