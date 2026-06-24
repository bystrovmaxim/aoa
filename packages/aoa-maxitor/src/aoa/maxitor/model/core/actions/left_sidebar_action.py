# packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/left_sidebar_action.py
"""
GetLeftMenuSidebarDataAction — left menu rows for diagrams from DuckDB.

════════════════════════════════════════════════════════════════════════════════
PURPOSE
════════════════════════════════════════════════════════════════════════════════

Four-aspect pipeline that builds flat ``NodeEntity`` lists (by depth / role)
from a DuckDB graph resource so the UI can render roots, per-root diagrams,
interchange nodes, and level-3 diagram rows using ``parent_id`` links only.

Aspect sequence:
  1. build_level1    — hardcoded root bucket nodes
  2. build_level2_diagrams — hardcoded "Full graph" + "Entity all domains" rows
  3. build_level2_nodes   — all coordinator nodes from DuckDB, grouped under roots
  4. build_level3_diagrams — per-domain ERD rows + per-entity class/lifecycle rows
  5. build_result (summary) — assemble Result from accumulated state

**Level-1 order matches** ``_ROOT_SECTIONS`` (Applications through Resources);
clients must preserve ``Result.level1_nodes`` order. Level-3 rows use ``ordinal``
for stable sibling order; otherwise alphabetical by label, then id.
"""

from __future__ import annotations

from typing import Any, cast

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.core.entities.node_entity import NodeEntity
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)

_ROOT_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("applications_root", "Applications", "Application"),
    ("domains_root", "Domains", "Domain"),
    ("roles_root", "Roles", "Role"),
    ("actions_root", "Actions", "Action"),
    ("entities_root", "Entities", "Entity"),
    ("resources_root", "Resources", "Resource"),
)

# DuckDB node types (lowercase) → Title-case sidebar type labels.
_DUCKDB_TO_SIDEBAR_TYPE: dict[str, str] = {
    "action": "Action",
    "application": "Application",
    "checker": "Checker",
    "compensator": "Compensator",
    "domain": "Domain",
    "entity": "Entity",
    "entity_field": "EntityField",
    "error_handler": "ErrorHandler",
    "field": "Field",
    "lifecycle": "Lifecycle",
    "property_field": "PropertyField",
    "regular_aspect": "RegularAspect",
    "required_context": "RequiredContext",
    "resource": "Resource",
    "result": "Result",
    "role": "Role",
    "params": "Params",
    "sensitive": "Sensitive",
    "state_final": "StateFinal",
    "state_initial": "StateInitial",
    "state_intermediate": "StateIntermediate",
    "summary_aspect": "SummaryAspect",
}


@meta(description="Build left-menu sidebar NodeEntity lists from DuckDB graph.", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(
    DuckDBGraphResource,
    key=DUCKDB_GRAPH_CONNECTION_KEY,
    description="Coordinator graph in DuckDB (sidebar node/edge queries)",
)
class GetLeftMenuSidebarDataAction(BaseAction[ParamsStub, "GetLeftMenuSidebarDataAction.Result"]):
    class Result(BaseResult):
        level1_nodes: list[NodeEntity]
        level2_diagrams: list[NodeEntity]
        level2_nodes: list[NodeEntity]
        level3_diagrams: list[NodeEntity]

    # ─── String helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _diagram_view_label(name: str) -> str:
        """Append ' view' to diagram display names (idempotent)."""
        base = str(name).strip()
        return base if base.endswith(" view") else f"{base} view"

    @staticmethod
    def _lifecycle_state_machine_row_title(field_name: str) -> str:
        """
        Sidebar title for one lifecycle field under an entity.

        Example: ``counterparty_linkage_lifecycle`` → ``Counterparty linkage lifecycle view``.
        """
        parts = [p for p in str(field_name).strip().split("_") if p]
        if not parts:
            display = "Lifecycle"
        else:
            head = parts[0][:1].upper() + parts[0][1:].lower()
            display = head if len(parts) == 1 else f"{head} {' '.join(p.lower() for p in parts[1:])}"
        return display if display.endswith(" view") else f"{display} view"

    # ─── Aspect 1 ─────────────────────────────────────────────────────────────

    @result_instance("level1_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-1 root bucket nodes (Applications, Domains, Roles, Actions, Entities, Resources).")
    async def build_level1_aspect(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = (state, box, connections)
        return {
            "level1_nodes": [
                NodeEntity(id=root_id, parent_id=None, label=label, type=type_)
                for root_id, label, type_ in _ROOT_SECTIONS
            ],
        }

    # ─── Aspect 2 ─────────────────────────────────────────────────────────────

    @result_instance("level1_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_diagrams", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-2 fixed diagram rows: Full graph under Applications, Entity all domains under Domains.")
    async def build_level2_diagrams_aspect(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = (box, connections)
        rows = sorted(
            [
                NodeEntity(
                    id="application_interchange_graph",
                    parent_id="applications_root",
                    label=self._diagram_view_label("Full graph"),
                    type="graph",
                ),
                NodeEntity(
                    id="domains_all_erd",
                    parent_id="domains_root",
                    label=self._diagram_view_label("Entity all domains"),
                    type="erd_all",
                ),
            ],
            key=lambda n: (n.label.lower(), n.id),
        )
        return {
            "level1_nodes": cast(list[NodeEntity], state["level1_nodes"]),
            "level2_diagrams": rows,
        }

    # ─── Aspect 3 ─────────────────────────────────────────────────────────────

    @result_instance("level1_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_diagrams", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-2 interchange nodes from DuckDB, each assigned to a root bucket by type.")
    async def build_level2_nodes_aspect(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = box
        level1 = cast(list[NodeEntity], state["level1_nodes"])
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])

        root_by_type = {n.type: n.id for n in level1}
        fallback_root = level1[-1].id
        rows = [
            NodeEntity(
                id=str(r["id"]),
                parent_id=root_by_type.get(
                    _DUCKDB_TO_SIDEBAR_TYPE.get(str(r["type"]), str(r["type"])),
                    fallback_root,
                ),
                label=str(r["label"]),
                type=_DUCKDB_TO_SIDEBAR_TYPE.get(str(r["type"]), str(r["type"])),
            )
            for r in duck.execute_fetch_dicts("SELECT id, label, type FROM nodes ORDER BY lower(label), id")
        ]
        return {
            "level1_nodes": level1,
            "level2_diagrams": cast(list[NodeEntity], state["level2_diagrams"]),
            "level2_nodes": rows,
        }

    # ─── Aspect 4 ─────────────────────────────────────────────────────────────

    @result_instance("level1_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_diagrams", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_nodes", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level3_diagrams", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-3 per-domain ERD rows and per-entity class/lifecycle diagram rows from DuckDB.")
    async def build_level3_diagrams_aspect(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        _ = box
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        rows: list[NodeEntity] = []

        for d in duck.execute_fetch_dicts("SELECT id, label FROM domain ORDER BY lower(label), id"):
            did, dlabel = str(d["id"]), str(d["label"])
            rows.append(NodeEntity(id=f"erd_domain:{did}", parent_id=did, label=self._diagram_view_label(f"Entity domain — {dlabel}"), type="erd_domain", ordinal=0))
            rows.append(NodeEntity(id=f"use_case_domain:{did}", parent_id=did, label=self._diagram_view_label(f"Use case — {dlabel}"), type="use_case_domain", ordinal=1))

        lifecycle_by_entity: dict[str, list[tuple[str, str]]] = {}
        for lc in duck.execute_fetch_dicts("""
            SELECT le.source_id AS entity_id, lc.id AS lifecycle_id, lc.label AS lifecycle_label
            FROM lifecycle_edges le
            JOIN lifecycle lc ON le.target_id = lc.id
            ORDER BY le.source_id, lower(lc.label), lc.id
        """):
            lifecycle_by_entity.setdefault(str(lc["entity_id"]), []).append(
                (str(lc["lifecycle_id"]), str(lc["lifecycle_label"]))
            )

        for e in duck.execute_fetch_dicts("SELECT id FROM entity ORDER BY id"):
            eid = str(e["id"])
            rows.append(NodeEntity(id=eid, parent_id=eid, label=self._diagram_view_label("Entity"), type="entity_class_diagram", ordinal=0))
            for ordinal, (lc_id, lc_label) in enumerate(lifecycle_by_entity.get(eid, []), start=1):
                rows.append(NodeEntity(
                    id=lc_id,
                    parent_id=eid,
                    label=self._lifecycle_state_machine_row_title(lc_label),
                    type="lifecycle_state_diagram",
                    ordinal=ordinal,
                ))

        rows.sort(key=lambda n: (str(n.parent_id).lower(), int(n.ordinal or 10**9), n.label.lower(), n.id))

        return {
            "level1_nodes": cast(list[NodeEntity], state["level1_nodes"]),
            "level2_diagrams": cast(list[NodeEntity], state["level2_diagrams"]),
            "level2_nodes": cast(list[NodeEntity], state["level2_nodes"]),
            "level3_diagrams": rows,
        }

    # ─── Summary ──────────────────────────────────────────────────────────────

    @summary_aspect("Assemble sidebar Result from accumulated state.")
    async def build_result_summary(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GetLeftMenuSidebarDataAction.Result:
        _ = (box, connections)
        return GetLeftMenuSidebarDataAction.Result(
            level1_nodes=cast(list[NodeEntity], state["level1_nodes"]),
            level2_diagrams=cast(list[NodeEntity], state["level2_diagrams"]),
            level2_nodes=cast(list[NodeEntity], state["level2_nodes"]),
            level3_diagrams=cast(list[NodeEntity], state["level3_diagrams"]),
        )
