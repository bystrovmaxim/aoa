# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/full_graph_action.py
"""
FullGraphAction — G6 graph payload from DuckDB graph views.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Read the interchange topology from DuckDB ``nodes`` / ``edges`` views and emit
the JSON consumed by the React G6 viewer. Colours are shared with
``ListNodeTypesAction``; heavier visual derivations are intentionally kept out
of the backend payload so the client can normalize/render from raw graph rows.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ``connections["DuckDBGraph"]`` (``nodes`` / ``edges`` views)
          |
          v
    @summary_aspect — ``Result(payload=...)``
"""

from __future__ import annotations

from typing import Any, cast

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
from aoa.maxitor.model.diagrams.actions.list_domains_action import ListDomainsAction
from aoa.maxitor.model.diagrams.actions.list_node_types_action import (
    DEFAULT_NODE_TYPE_COLOR,
    fill_color_for_node_type,
    interchange_node_type_from_duck,
)
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain

G6_CDN_URL = "https://unpkg.com/@antv/g6@5/dist/g6.min.js"
DAG_CYCLE_VIOLATION_COLOR = "#E41A1C"
GRAPH_NODE_VISUAL_PX = 24


def _short_label(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return "?"
    return value.rsplit(".", 1)[-1] if "." in value else value


@meta(
    description="Get full interchange graph JSON from DuckDB views (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(NoneRole)
@connection(
    DuckDBGraphResource,
    key=DUCKDB_GRAPH_CONNECTION_KEY,
    description="Coordinator graph in DuckDB (nodes and edges views for full graph)",
)
class FullGraphAction(BaseAction[ParamsStub, "FullGraphAction.Result"]):
    """
    AI-CORE-BEGIN
    ROLE: Emit a G6-oriented full graph payload from DuckDB ``nodes`` / ``edges`` views.
    CONTRACT: Nodes and edges are read with SQL only; node disk colours use ``ListNodeTypesAction`` and domain bubble membership is derived client-side.
    INVARIANTS: No NetworkX or ``NodeGraphCoordinator`` dependency in this action.
    AI-CORE-END
    """

    class Result(BaseResult):
        """HTTP/JSON body is ``model_dump(mode="json")`` of this result (single key ``payload``)."""

        payload: dict[str, Any] = Field(
            description="G6 graph payload built from DuckDB nodes/edges views.",
        )

    @summary_aspect("Build full graph JSON from DuckDB views")
    async def build_full_graph_summary(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> FullGraphAction.Result:
        _ = (state, box)
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])

        node_rows = duck.execute_fetch_dicts(
            """
            SELECT id, label, type, payload
            FROM nodes
            ORDER BY lower(type), lower(label), id
            """
        )
        edge_rows = duck.execute_fetch_dicts(
            """
            SELECT
                row_number() OVER (ORDER BY source_id, target_id, type, relationship) - 1 AS idx,
                source_id,
                target_id,
                relationship,
                is_dag,
                type,
                payload
            FROM edges
            ORDER BY source_id, target_id, type, relationship
            """
        )

        nodes: list[dict[str, Any]] = []
        node_type_map: dict[str, str] = {}
        for row in node_rows:
            node_id = str(row["id"])
            duck_type = str(row["type"])
            node_type = interchange_node_type_from_duck(duck_type)
            label = str(row["label"] or node_id)
            fill = fill_color_for_node_type(duck_type)
            nodes.append(
                {
                    "id": node_id,
                    "data": {
                        "label": _short_label(label),
                        "title": label,
                        "graph_node_subtitle": f"{node_type}\n{_short_label(label)}",
                        "graph_key": node_id,
                        "qualified": node_id,
                        "node_type": node_type,
                        "typeFill": fill,
                        "fill": fill,
                        "isDagCycleViolationIncident": False,
                        "payload": row.get("payload"),
                    },
                }
            )
            node_type_map[node_id] = node_type

        edges = [
            {
                "id": f"e-{row['idx']}",
                "source": str(row["source_id"]),
                "target": str(row["target_id"]),
                "data": {
                    "label": str(row["relationship"]),
                    "isDag": bool(row["is_dag"]),
                    "isForbiddenDagCycle": False,
                    "relationshipName": str(row["relationship"]),
                    "sourceAttachment": "none",
                    "targetAttachment": "arrow",
                    "lineStyle": "solid",
                    "edge_type": str(row["type"]),
                    "payload": row.get("payload"),
                },
            }
            for row in edge_rows
            if str(row["source_id"]) in node_type_map and str(row["target_id"]) in node_type_map
        ]

        used_types = sorted({node_type for node_type in node_type_map.values() if node_type})
        legend_items = [
            {"type": node_type, "color": fill_color_for_node_type(node_type)}
            for node_type in used_types
            if node_type != "unknown"
        ] or [{"type": "unknown", "color": DEFAULT_NODE_TYPE_COLOR}]

        domain_color_map = {
            str(row["qualname"]): str(row["color"])
            for row in ListDomainsAction.domain_accent_rows(duck)
        }
        payload = {
            "title": "Interchange graph",
            "nodes": nodes,
            "edges": edges,
            "legend_items": legend_items,
            "node_type_map": node_type_map,
            "domain_color_map": domain_color_map,
            "bubble_plugins": [],
            "constants": {
                "node_visual_px": GRAPH_NODE_VISUAL_PX,
                "dag_cycle_violation_color": DAG_CYCLE_VIOLATION_COLOR,
                "default_color": DEFAULT_NODE_TYPE_COLOR,
                "g6_cdn_url": G6_CDN_URL,
            },
        }
        return FullGraphAction.Result(payload=payload)
