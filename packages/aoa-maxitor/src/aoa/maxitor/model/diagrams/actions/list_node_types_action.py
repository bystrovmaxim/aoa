# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_node_types_action.py
"""
ListNodeTypesAction — present graph-node types from DuckDB with G6 disk fills.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Read distinct node types from DuckDB ``nodes`` (the unified graph-node view) and
assign the same disk fill colours used by the interchange G6 viewer. The wire
field ``list_node_types`` uses ``ListNodeTypesJson`` from
:mod:`~aoa.maxitor.model.diagrams.actions.list_node_types_action_schema`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ``connections["DuckDBGraph"]`` (``nodes`` view)
          |
          v
    @summary_aspect — ``Result(list_node_types=...)``
"""

from __future__ import annotations

from typing import cast

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.core.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)
from aoa.maxitor.model.diagrams.actions.build_interchange_graph_data_action import (
    _fill_color_for_graph_node_type,
)
from aoa.maxitor.model.diagrams.actions.list_node_types_action_schema import ListNodeTypesJson
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain


@meta(
    description="List present graph-node types from DuckDB with interchange disk fill colours (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(NoneRole)
@connection(
    DuckDBGraphResource,
    key=DUCKDB_GRAPH_CONNECTION_KEY,
    description="Coordinator graph in DuckDB (nodes view for present graph-node types)",
)
class ListNodeTypesAction(BaseAction[ParamsStub, "ListNodeTypesAction.Result"]):
    """
    AI-CORE-BEGIN
    ROLE: Emit present ``nodes.type`` rows with their interchange G6 disk fill colours.
    CONTRACT: Rows come from DuckDB ``nodes`` grouped by ``type``; colours use the graph builder's node-type fill resolver.
    INVARIANTS: Reads ``connections[DuckDBGraph]`` only — no NetworkX scan and no static type inventory.
    AI-CORE-END
    """

    class Result(BaseResult):
        """HTTP/JSON body is ``model_dump(mode="json")`` of this result (single list field)."""

        # [
        #   {"node_type": "application", "color": "#000000"},
        #   {"node_type": "action", "color": "#4F46E5"}
        # ]
        list_node_types: ListNodeTypesJson = Field(
            description="Ordered node_type ids from ``nodes`` with disk fill hex per row.",
        )

    @summary_aspect("Resolve graph-node type list with disk fill colours from DuckDB")
    async def build_list_node_types_summary(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ListNodeTypesAction.Result:
        _ = (state, box)
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        sql = """
        SELECT type AS node_type
        FROM nodes
        GROUP BY type
        ORDER BY lower(type), type
        """
        raw = duck.execute_fetch_dicts(sql)
        rows = [
            {
                "node_type": str(row["node_type"]),
                "color": _fill_color_for_graph_node_type(str(row["node_type"])),
            }
            for row in raw
        ]
        return ListNodeTypesAction.Result(list_node_types=rows)
