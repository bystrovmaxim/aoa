# packages/maxitor/front/src/maxitor/front/model/core/actions/left_sidebar_action.py
"""
GetLeftMenuSidebarDataAction — left menu rows for diagrams from DuckDB.

════════════════════════════════════════════════════════════════════════════════
PURPOSE
════════════════════════════════════════════════════════════════════════════════

Four-aspect pipeline that builds flat ``NodeCoreEntity`` lists (by depth / role)
from a DuckDB graph resource so the UI can render roots, per-root diagrams,
domains, and each domain's diagram rows using ``parent_id`` links only. Every row
opens a diagram: what the graph holds is reached through the diagrams (spec 041).

Aspect sequence:
  1. build_level1    — hardcoded root bucket nodes
  2. build_level2_diagrams — hardcoded rows of the whole application
  3. build_level2_nodes   — the domains from DuckDB
  4. build_level3_diagrams — per-domain ERD and use-case rows, and one row per lifecycle
  5. build_result (summary) — assemble Result from accumulated state

**Level-1 order matches** ``_ROOT_SECTIONS``;
clients must preserve ``Result.level1_nodes`` order. Level-3 rows use ``ordinal``
for stable sibling order; otherwise alphabetical by label, then id.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, cast

from maxitor.front.model.core.entities.node_entity import NodeCoreEntity
from maxitor.front.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

_ROOT_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("applications_root", "Applications", "Application"),
    ("domains_root", "Domains", "Domain"),
)

@meta(description="Build left-menu sidebar NodeCoreEntity lists from DuckDB graph.", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(
    DuckDBGraphResource,
    key=DUCKDB_GRAPH_CONNECTION_KEY,
    description="Coordinator graph in DuckDB (sidebar node/edge queries)",
)
class GetLeftMenuSidebarDataAction(BaseAction[ParamsStub, "GetLeftMenuSidebarDataAction.Result"]):
    class Result(BaseResult):
        level1_nodes: list[NodeCoreEntity]
        level2_diagrams: list[NodeCoreEntity]
        level2_nodes: list[NodeCoreEntity]
        level3_diagrams: list[NodeCoreEntity]

    # ─── String helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _diagram_view_label(name: str) -> str:
        """Append ' view' to diagram display names (idempotent)."""
        base = str(name).strip()
        return base if base.endswith(" view") else f"{base} view"

    # ─── Aspect 1 ─────────────────────────────────────────────────────────────

    @result_instance("level1_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-1 root bucket nodes (Applications, Domains).")
    async def build_level1_aspect(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict[str, Any]:
        _ = (state, box, connections)
        return {
            "level1_nodes": [
                NodeCoreEntity(id=root_id, parent_id=None, label=label, type=type_)
                for root_id, label, type_ in _ROOT_SECTIONS
            ],
        }

    # ─── Aspect 2 ─────────────────────────────────────────────────────────────

    @result_instance("level1_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_diagrams", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-2 fixed diagram rows of the whole application.")
    async def build_level2_diagrams_aspect(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict[str, Any]:
        _ = (box, connections)
        rows = sorted(
            [
                NodeCoreEntity(
                    id="application_interchange_graph",
                    parent_id="applications_root",
                    label=self._diagram_view_label("Full graph"),
                    type="graph",
                ),
                NodeCoreEntity(
                    id="application_all_erd",
                    parent_id="applications_root",
                    label=self._diagram_view_label("ERD all domains"),
                    type="erd_all",
                ),
                NodeCoreEntity(
                    id="application_all_use_cases",
                    parent_id="applications_root",
                    label=self._diagram_view_label("Use case all domains"),
                    type="use_case_all",
                ),
            ],
            key=lambda n: (n.label.lower(), n.id),
        )
        return {
            "level1_nodes": cast(list[NodeCoreEntity], state["level1_nodes"]),
            "level2_diagrams": rows,
        }

    # ─── Aspect 3 ─────────────────────────────────────────────────────────────

    @result_instance("level1_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_diagrams", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-2 domain nodes from DuckDB.")
    async def build_level2_nodes_aspect(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict[str, Any]:
        _ = box
        level1 = cast(list[NodeCoreEntity], state["level1_nodes"])
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        rows = [
            NodeCoreEntity(id=str(r["id"]), parent_id="domains_root", label=str(r["label"]), type="Domain")
            for r in duck.execute_fetch_dicts("SELECT id, label FROM domain ORDER BY lower(label), id")
        ]
        return {
            "level1_nodes": level1,
            "level2_diagrams": cast(list[NodeCoreEntity], state["level2_diagrams"]),
            "level2_nodes": rows,
        }

    # ─── Aspect 4 ─────────────────────────────────────────────────────────────

    @result_instance("level1_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_diagrams", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level3_diagrams", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-3 per-domain ERD and use-case rows, and one row per lifecycle, from DuckDB.")
    async def build_level3_diagrams_aspect(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict[str, Any]:
        _ = box
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        rows: list[NodeCoreEntity] = []

        for d in duck.execute_fetch_dicts("SELECT id, label FROM domain ORDER BY lower(label), id"):
            did, dlabel = str(d["id"]), str(d["label"])
            rows.append(NodeCoreEntity(id=f"erd_domain:{did}", parent_id=did, label=self._diagram_view_label(f"Entity domain — {dlabel}"), type="erd_domain", ordinal=0))
            rows.append(NodeCoreEntity(id=f"use_case_domain:{did}", parent_id=did, label=self._diagram_view_label(f"Use case — {dlabel}"), type="use_case_domain", ordinal=1))

        # One row per lifecycle, under the domain of the entity that holds it.
        lifecycles = duck.execute_fetch_dicts("""
            SELECT de.target_id AS domain_id, le.source_id AS entity_id, e.label AS entity_label, lc.id AS lifecycle_id, lc.field_name
            FROM lifecycle_edges le
            JOIN lifecycle lc ON lc.id = le.target_id
            JOIN entity e ON e.id = le.source_id
            JOIN domain_edges de ON de.source_id = le.source_id
            ORDER BY lower(e.label), lc.id
        """)
        per_entity = Counter(str(lc["entity_id"]) for lc in lifecycles)
        for lc in lifecycles:
            several = per_entity[str(lc["entity_id"])] > 1
            name = f"{lc['entity_label']} {str(lc['field_name']).replace('_', ' ')}" if several else f"{lc['entity_label']} lifecycle"
            rows.append(NodeCoreEntity(id=str(lc["lifecycle_id"]), parent_id=str(lc["domain_id"]), label=self._diagram_view_label(name), type="lifecycle_state_diagram", ordinal=2, host_id=str(lc["entity_id"])))

        rows.sort(key=lambda n: (str(n.parent_id).lower(), int(n.ordinal or 10**9), n.label.lower(), n.id))

        return {
            "level1_nodes": cast(list[NodeCoreEntity], state["level1_nodes"]),
            "level2_diagrams": cast(list[NodeCoreEntity], state["level2_diagrams"]),
            "level2_nodes": cast(list[NodeCoreEntity], state["level2_nodes"]),
            "level3_diagrams": rows,
        }

    # ─── Summary ──────────────────────────────────────────────────────────────

    @summary_aspect("Assemble sidebar Result from accumulated state.")
    async def build_result_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> GetLeftMenuSidebarDataAction.Result:
        _ = (box, connections)
        return GetLeftMenuSidebarDataAction.Result(
            level1_nodes=cast(list[NodeCoreEntity], state["level1_nodes"]),
            level2_diagrams=cast(list[NodeCoreEntity], state["level2_diagrams"]),
            level2_nodes=cast(list[NodeCoreEntity], state["level2_nodes"]),
            level3_diagrams=cast(list[NodeCoreEntity], state["level3_diagrams"]),
        )
