# packages/maxitor/front/src/maxitor/front/model/diagrams/actions/map_area_action.py
"""
MapAreaAction — one area of a version's map, as far as a level shows it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

When an area comes into view the browser reads it (spec 040, FR-010): its nodes at their
places, the links inside it, and the links to other areas, which are drawn once both ends
are loaded. Level 2 stops at entities and operations; level 3 holds everything.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/map/area?source=<version>&id=<area>&level=<2|3> ──► MapStore.area(id) ──► up to that level
"""

from __future__ import annotations

from typing import Any, cast

from maxitor.front.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.front.model.diagrams.resources.map_store import MAP_STORE_CONNECTION_KEY, MapStore
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class MapAreaNotFoundError(LookupError):
    """The version's map has no such area; answered as "not found"."""


class MapAreaParams(BaseParams):
    """Which area, and how far."""

    id: str = Field(min_length=1, max_length=2000, description="The area's id, as the overview gives it")
    level: int = Field(ge=2, le=3, description="2 for entities and operations, 3 for everything")


class MapAreaResult(BaseResult):
    """One area up to a level."""

    nodes: list[dict[str, Any]] = Field(description="Each node: id, label, type, level, and its place on the map")
    edges: list[dict[str, Any]] = Field(description="Each link inside the area whose ends both show")
    across: list[dict[str, Any]] = Field(description="Each link to another area, drawn once both ends are loaded")


@meta(description="Read one area of a version's map", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(MapStore, key=MAP_STORE_CONNECTION_KEY, description="The maps of versions")
class MapAreaAction(BaseAction[MapAreaParams, MapAreaResult]):
    """
    AI-CORE-BEGIN
    ROLE: Answer one area of a version's map, as far as a level shows it.
    CONTRACT: Nodes and links of that area up to ``level``; an unknown area raises ``MapAreaNotFoundError``.
    INVARIANTS: Reads what ``MapStore`` keeps; computes nothing of its own.
    AI-CORE-END
    """

    @summary_aspect("Give one area of the map")
    async def area_summary(
        self,
        params: MapAreaParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> MapAreaResult:
        """Read the area and keep what the level shows."""
        _ = (state, box)
        detail = await cast(MapStore, connections[MAP_STORE_CONNECTION_KEY]).area(params.id)
        if detail is None:
            raise MapAreaNotFoundError("not found")
        return MapAreaResult(
            nodes=[item for item in detail["nodes"] if item["level"] <= params.level],
            edges=[item for item in detail["edges"] if item["level"] <= params.level],
            across=[item for item in detail["across"] if item["level"] <= params.level],
        )
