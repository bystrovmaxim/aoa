# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/full_graph_action.py
"""
FullGraphAction — G6 payload from DuckDB ``nodes`` / ``edges``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

All interchange vertex types materialized in the DuckDB ``nodes`` view participate
in the payload (including ``EntityField`` rows, slug ``entity_field``, and
``entity_field_edges`` in ``edges``). The viewer tightens force links between
``Entity`` and ``EntityField`` so scalar attributes stay near their host entity.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.graph.core.edge_relationship import GENERALIZATION
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.diagrams.actions.list_domains_action import _LIST_DOMAINS_DISTINCT_COLORS
from aoa.maxitor.model.diagrams.actions.list_node_types_action import (
    DEFAULT_NODE_TYPE_COLOR,
    fill_color_for_node_type,
    interchange_node_type_from_duck,
)
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY, DuckDBGraphResource

G6_CDN_URL = "https://unpkg.com/@antv/g6@5/dist/g6.min.js"
DAG_CYCLE_VIOLATION_COLOR = "#E41A1C"
GRAPH_NODE_VISUAL_PX = 24

# DuckDB ``nodes.type`` slug for :class:`~aoa.action_machine.graph.nodes.entity_field_graph_node.EntityFieldGraphNode`.
FULL_GRAPH_ENTITY_FIELD_DUCK_SLUG = "entity_field"

# Interchange ``node_type`` after :func:`~aoa.maxitor.model.diagrams.actions.list_node_types_action.interchange_node_type_from_duck`.
FULL_GRAPH_ENTITY_FIELD_INTERCHANGE_TYPE = "EntityField"

# d3-force link tuning for Entity ↔ EntityField (same kind of link strength as same-type clusters).
LAYOUT_ENTITY_SCALAR_LINK: dict[str, float] = {
    "distance": 84.0,
    "strength": 0.8,
}

# ---------------------------------------------------------------------------
# SQL — single round-trip (nodes + edges + domains); no PyArrow dependency.
# ---------------------------------------------------------------------------

# Full-graph viewer omits UML generalization links (``parent_*`` wire edges); they remain in DuckDB.
_FULL_GRAPH_SQL_EXCLUDED_RELATIONSHIP = GENERALIZATION.archimate_name

_FULL_GRAPH_SQL = f"""
WITH
  node_rows AS (
    SELECT
      id,
      label,
      type
    FROM nodes
    ORDER BY lower(type), lower(label), id
  ),
  edge_rows AS (
    SELECT
      row_number() OVER (ORDER BY source_id, target_id, type, relationship) - 1 AS idx,
      source_id,
      target_id,
      relationship,
      type
    FROM edges
    WHERE relationship <> '{_FULL_GRAPH_SQL_EXCLUDED_RELATIONSHIP}'
    ORDER BY source_id, target_id, type, relationship
  ),
  domain_rows AS (
    SELECT id AS qualname
    FROM domain
    WHERE id NOT LIKE 'tests.%'
      AND strpos(id, '<locals>') = 0
    ORDER BY lower(label), lower(COALESCE(NULLIF(name, ''), label, id)), id
  )
SELECT
  'nodes'   AS result_type,
  id        AS pk,
  label,
  type,
  CAST(NULL AS BIGINT) AS idx,
  NULL      AS source_id,
  NULL      AS target_id,
  NULL      AS relationship,
  NULL      AS is_dag,
  NULL      AS payload
FROM node_rows
UNION ALL
SELECT
  'edges'         AS result_type,
  CAST(idx AS VARCHAR) AS pk,
  NULL            AS label,
  type,
  idx,
  source_id,
  target_id,
  relationship,
  NULL            AS is_dag,
  NULL            AS payload
FROM edge_rows
UNION ALL
SELECT
  'domain'  AS result_type,
  qualname  AS pk,
  NULL      AS label,
  NULL      AS type,
  NULL      AS idx,
  NULL      AS source_id,
  NULL      AS target_id,
  NULL      AS relationship,
  NULL      AS is_dag,
  NULL      AS payload
FROM domain_rows
"""


def _short_label(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return "?"
    return value.rsplit(".", 1)[-1] if "." in value else value


def _build_payload_from_duckdb(
    duck: DuckDBGraphResource,
    palette: tuple[str, ...],
) -> dict[str, Any]:
    """Run unified SQL once, split rows by ``result_type``, build G6 payload."""
    rows = duck.execute_fetch_dicts(_FULL_GRAPH_SQL)
    node_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    domain_rows: list[dict[str, Any]] = []
    for row in rows:
        rt = row.get("result_type")
        if rt == "nodes":
            node_rows.append(row)
        elif rt == "edges":
            edge_rows.append(row)
        elif rt == "domain":
            domain_rows.append(row)

    nodes: list[dict[str, Any]] = []
    node_id_set: set[str] = set()
    node_type_map: dict[str, str] = {}
    node_types: list[str] = []

    for row in node_rows:
        nid = str(row["pk"])
        label = row.get("label")
        duck_type = row.get("type")
        node_types.append(str(duck_type or ""))
        duck_s = str(duck_type or "")
        node_type = interchange_node_type_from_duck(duck_s)
        fill = fill_color_for_node_type(duck_s)
        lbl = str(label or nid)
        nodes.append(
            {
                "id": nid,
                "data": {
                    "label": _short_label(lbl),
                    "title": lbl,
                    "node_type": node_type,
                    "fill": fill,
                },
            }
        )
        node_id_set.add(nid)
        node_type_map[nid] = node_type

    edges: list[dict[str, Any]] = []
    for row in edge_rows:
        idx = row.get("idx")
        src = str(row["source_id"]) if row.get("source_id") is not None else ""
        tgt = str(row["target_id"]) if row.get("target_id") is not None else ""
        rel = row.get("relationship")
        etype = row.get("type")
        if not src or not tgt or src not in node_id_set or tgt not in node_id_set:
            continue
        edges.append(
            {
                "id": f"e-{idx}",
                "source": src,
                "target": tgt,
                "data": {
                    "label": str(rel),
                    "edge_type": str(etype),
                },
            }
        )

    qualnames = [str(r["pk"]) for r in domain_rows]
    domain_color_map = {q: palette[i % len(palette)] for i, q in enumerate(qualnames)}

    seen_types: dict[str, str] = {}
    for duck_type in node_types:
        nt = interchange_node_type_from_duck(str(duck_type))
        if nt and nt != "unknown" and nt not in seen_types:
            seen_types[nt] = fill_color_for_node_type(str(duck_type))

    legend_items = [{"type": nt, "color": col} for nt, col in sorted(seen_types.items())] or [
        {"type": "unknown", "color": DEFAULT_NODE_TYPE_COLOR}
    ]

    return {
        "title": "Full graph view",
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
            "entity_field_duck_slug": FULL_GRAPH_ENTITY_FIELD_DUCK_SLUG,
            "entity_field_interchange_type": FULL_GRAPH_ENTITY_FIELD_INTERCHANGE_TYPE,
            "layout_entity_scalar_link": LAYOUT_ENTITY_SCALAR_LINK,
        },
    }


@meta(
    description="Get full interchange graph JSON from DuckDB views (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(GuestRole)
@connection(
    DuckDBGraphResource,
    key=DUCKDB_GRAPH_CONNECTION_KEY,
    description="Coordinator graph in DuckDB (nodes and edges views for full graph)",
)
class FullGraphAction(BaseAction[ParamsStub, "FullGraphAction.Result"]):
    """
    AI-CORE-BEGIN
    ROLE: Emit a G6-oriented full graph payload from DuckDB ``nodes`` / ``edges`` views.
    CONTRACT: One SQL round-trip via ``execute_fetch_dicts`` (no PyArrow); slim ``data`` on
    each node/edge; includes ``EntityField`` when present in ``nodes``; ``constants`` exposes
    layout hints for Entity ↔ EntityField force links and interchange/duck type strings for the viewer.
    INVARIANTS: No NetworkX or ``NodeGraphCoordinator`` dependency.
    AI-CORE-END
    """

    class Result(BaseResult):
        payload: dict[str, Any] = Field(
            description="G6 graph payload built from DuckDB nodes/edges views.",
        )

    @summary_aspect("Build full graph JSON from DuckDB (single unified SQL query)")
    async def build_full_graph_summary(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> FullGraphAction.Result:
        _ = (state, box)
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])

        payload = _build_payload_from_duckdb(
            duck,
            _LIST_DOMAINS_DISTINCT_COLORS,
        )
        return FullGraphAction.Result(payload=payload)
