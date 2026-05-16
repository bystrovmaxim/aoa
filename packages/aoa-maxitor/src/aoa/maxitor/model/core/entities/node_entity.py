# packages/aoa-maxitor/src/aoa/maxitor/model/core/entities/node_entity.py
"""
NodeEntity — sidebar / tree row record for diagrams.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Carry a stable id, optional parent link, display label, and a coarse category string
for hierarchical UI lists. Declared as an ActionMachine entity under ``DiagramsDomain``.
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain


@entity(
    description="Hierarchical UI node row (id, optional parent, label, coarse type)",
    domain=DiagramsDomain,
)
class NodeEntity(BaseEntity):
    """
    AI-CORE-BEGIN
    ROLE: Diagrams entity for a single navigable tree row.
    CONTRACT: ``id``, ``label``, and ``type`` are required; ``parent_id`` is optional for root rows.
    INVARIANTS: Immutable; no coordinator or graph handles on the instance; used by sidebar and ERD tab list actions.
    AI-CORE-END
    """

    id: str = Field(min_length=1, description="Stable node identifier")
    parent_id: str | None = Field(default=None, description="Parent node id when nested under another row")
    label: str = Field(description="Display label")
    type: str = Field(description="Coarse node category (e.g. interchange primary node_type)")
    ordinal: int | None = Field(
        default=None,
        description="Optional sort rank among siblings (lower first); used for level-3 diagram order",
    )
