# packages/maxitor/front/src/maxitor/front/model/diagrams/actions/map_overview_action.py
"""
MapOverviewAction — what the browser reads first of a version's map.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The full graph is read in parts (spec 040, FR-010): this read gives the areas, the bundles
between them, and what a filter needs without another read. While a version is being laid
out it answers ``state: laying-out`` and the client asks again.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/map/overview?source=<version> ──► GraphSourceMiddleware ──► MapStore.overview()
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


class MapOverviewResult(BaseResult):
    """A version's map, without its nodes."""

    state: str = Field(description="'ready', or 'laying-out' while the map is made")
    types: list[str] = Field(description="The node types of the graph; a sketch's cells index into this list")
    areas: list[dict[str, Any]] = Field(description="Each area: id, name, colour, place, counts by type and sketch")
    bundles: list[list[Any]] = Field(description="Each pair of linked areas: both ids, the number of links, links by the types of their ends")
    shared: list[dict[str, Any]] = Field(description="Each node in more than one domain, with its domains")
    type_colours: dict[str, str] = Field(default_factory=dict, description="Each node type's colour")
    chains: list[list[str]] = Field(default_factory=list, description="The distinct lists of types above a node; a sketch's chain index reads here")
    links_changed: int | None = Field(default=None, description="In a comparison, how many drawn links changed; absent for one version")


@meta(description="Read the overview of a version's map", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(MapStore, key=MAP_STORE_CONNECTION_KEY, description="The maps of versions")
class MapOverviewAction(BaseAction[ParamsStub, MapOverviewResult]):
    """
    AI-CORE-BEGIN
    ROLE: Answer what the browser reads first of a version's map.
    CONTRACT: A ready map's overview, or ``state: laying-out`` with nothing in it while the map is made.
    INVARIANTS: Laid out once by ``MapStore``; names no address and no key in its log.
    AI-CORE-END
    """

    @summary_aspect("Give the map's overview")
    async def overview_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> MapOverviewResult:
        """Read the bound version's overview."""
        _ = (params, state, box)
        return MapOverviewResult(**await cast(MapStore, connections[MAP_STORE_CONNECTION_KEY]).overview())
