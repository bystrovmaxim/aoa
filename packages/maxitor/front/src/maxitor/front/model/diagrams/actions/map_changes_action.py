# packages/maxitor/front/src/maxitor/front/model/diagrams/actions/map_changes_action.py
"""
MapChangesAction — every changed node of a pair, in the order the map steps through them.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Reaching a change must not depend on what the browser has loaded (spec 040, FR-025c), so
the list comes from the server, with each node's place and level.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/map/changes?source=<B>&a=<A> ──► GraphSourceMiddleware ──► MapStore.changes()
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
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class MapChangesResult(BaseResult):
    """A pair's changed nodes."""

    changes: list[dict[str, Any]] = Field(description="Each changed node: id, area, type, status, place and level")


@meta(description="List the changes of two versions, in stepping order", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(MapStore, key=MAP_STORE_CONNECTION_KEY, description="The maps of versions")
class MapChangesAction(BaseAction[ParamsStub, MapChangesResult]):
    """
    AI-CORE-BEGIN
    ROLE: Answer every changed node of the pair a read names, in the order the map steps through them.
    CONTRACT: Domains by size, largest first, then the graph's order; empty before the map is made.
    INVARIANTS: Reads what ``MapStore`` keeps; computes nothing of its own.
    AI-CORE-END
    """

    @summary_aspect("Give the pair's changes")
    async def changes_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> MapChangesResult:
        """Read the bound pair's list."""
        _ = (params, state, box)
        return MapChangesResult(changes=await cast(MapStore, connections[MAP_STORE_CONNECTION_KEY]).changes())
