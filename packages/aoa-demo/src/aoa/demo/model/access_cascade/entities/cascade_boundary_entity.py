# packages/aoa-demo/src/aoa/demo/model/access_cascade/entities/cascade_boundary_entity.py
"""
CascadeBoundaryEntity — the one-sided boundary extreme of the access-cascade drawing.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A drawing fixture (FR-010): the diagram must show a relation whose reverse
side is deliberately absent — the ``NoInverse`` boundary worth drawing. The
entity carries exactly one relation field, self-referencing, so the fixture
stays self-contained and touches no other domain. It has no business meaning.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    CascadeBoundaryEntity
        └── peer_boundary: AssociationOne[CascadeBoundaryEntity]  (NoInverse)
            →  one entity_relation edge with has_inverse=False
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity

from aoa.demo.model.access_cascade.access_cascade_domain import AccessCascadeDomain


@entity(
    description="Shape: a one-sided relation boundary — the absent reverse side is the drawing",
    domain=AccessCascadeDomain,
)
class CascadeBoundaryEntity(BaseEntity):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture whose only relation deliberately has no reverse side.
    CONTRACT: Exactly one relation field, declared ``NoInverse()``.
    INVARIANTS: No business meaning; the one-sided boundary is the shape being drawn.
    AI-CORE-END
    """

    id: str = Field(description="Boundary row id")

    peer_boundary: Annotated[
        AssociationOne[CascadeBoundaryEntity],
        NoInverse(),
    ] = Rel(
        description="One-sided boundary to a peer row — the absent reverse side is the shape"
    )  # type: ignore[assignment]


CascadeBoundaryEntity.model_rebuild()
