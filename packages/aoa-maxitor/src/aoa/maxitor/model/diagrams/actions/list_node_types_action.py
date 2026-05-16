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
from aoa.maxitor.model.diagrams.actions.list_node_types_action_schema import ListNodeTypesJson
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)

DEFAULT_NODE_TYPE_COLOR = "#95a5a6"

# DuckDB ``nodes.type`` uses lowercase SQL literals for most kinds; ``state`` rows use ``kind`` (PascalCase).
_DUCK_SLUG_TO_INTERCHANGE: dict[str, str] = {
    "action": "Action",
    "application": "Application",
    "domain": "Domain",
    "entity": "Entity",
    "entity_field": "EntityField",
    "resource": "Resource",
    "params": "Params",
    "result": "Result",
    "field": "Field",
    "property_field": "PropertyField",
    "regular_aspect": "RegularAspect",
    "summary_aspect": "SummaryAspect",
    "compensator": "Compensator",
    "error_handler": "ErrorHandler",
    "checker": "Checker",
    "required_context": "RequiredContext",
    "lifecycle": "Lifecycle",
    "sensitive": "Sensitive",
    "role": "Role",
}

# Fixed fill per interchange graph-node ``node_type`` (matches G6 client icon keys).
NODE_TYPE_FILL_COLORS: dict[str, str] = {
    "Application": "#000000",
    "Action": "#4F46E5",
    "Domain": "#377EB8",
    "Resource": "#7570B3",
    "RequiredContext": "#4DAF4A",
    "RegularAspect": "#FF7F00",
    "SummaryAspect": "#FF7F00",
    "Checker": "#A65628",
    "Compensator": "#F781BF",
    "ErrorHandler": "#FCD34D",
    "Entity": "#1B9E77",
    "EntityField": "#5AB4AC",
    "Lifecycle": "#00798C",
    "StateInitial": "#9575CD",
    "StateIntermediate": "#6A51A3",
    "StateFinal": "#452E7A",
    "Role": "#66A61E",
    "Sensitive": "#A855F7",
    "Params": "#CAB2D6",
    "Result": "#B2DF8A",
    "Field": "#6B5B95",
    "PropertyField": "#6B5B95",
}


def interchange_node_type_from_duck(duck_type: str) -> str:
    """Map DuckDB ``nodes.type`` string to interchange ``node_type`` (PascalCase) for G6."""
    raw = str(duck_type).strip()
    if not raw or raw == "unknown":
        return "unknown"
    if raw in NODE_TYPE_FILL_COLORS:
        return raw
    mapped = _DUCK_SLUG_TO_INTERCHANGE.get(raw.casefold())
    if mapped:
        return mapped
    return raw


def fill_color_for_node_type(node_type: str) -> str:
    """Return the G6 disk fill for a DuckDB or interchange ``node_type`` string."""
    canonical = interchange_node_type_from_duck(node_type)
    if canonical == "unknown":
        return DEFAULT_NODE_TYPE_COLOR
    return NODE_TYPE_FILL_COLORS.get(canonical, DEFAULT_NODE_TYPE_COLOR)


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
    CONTRACT: Rows come from DuckDB ``nodes`` grouped by ``type``; ``node_type`` is normalized to interchange PascalCase for G6; colours use the shared resolver.
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
                "node_type": interchange_node_type_from_duck(str(row["node_type"])),
                "color": fill_color_for_node_type(str(row["node_type"])),
            }
            for row in raw
        ]
        return ListNodeTypesAction.Result(list_node_types=rows)
