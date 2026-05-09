# packages/aoa-maxitor/src/aoa/maxitor/root/app_view/actions/get_left_menu_sidebar_data_action.py
"""
GetLeftMenuSidebarDataAction — left menu rows for app-view from a NetworkX graph.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materialize four flat ``NodeEntity`` lists (by depth / role) from a ``LoadGraphAction``
``DiGraph`` so the UI can render roots, per-root diagrams, coordinator rows, and
per-domain ERD rows using ``parent_id`` links only. Only level-1 order is fixed
(``_ROOT_SECTIONS``); deeper rows are ordered alphabetically by label, then id.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.root.app_view.app_view_domen_domain import AppViewDomenDomain
from aoa.maxitor.root.app_view.entities.node_entity import NodeEntity

_ROOT_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("applications_root", "Applications", "Application"),
    ("domains_root", "Domains", "Domain"),
    ("roles_root", "Roles", "Role"),
    ("actions_root", "Actions", "Action"),
    ("entities_root", "Entities", "Entity"),
    ("resources_root", "Resources", "Resource"),
)

@meta(description="Build left-menu sidebar NodeEntity lists from NetworkX graph view", domain=AppViewDomenDomain)
@check_roles(NoneRole)
class GetLeftMenuSidebarDataAction(
    BaseAction["GetLeftMenuSidebarDataAction.Params", "GetLeftMenuSidebarDataAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Emit four ``NodeEntity`` layers for a simple parent-linked sidebar hierarchy.
    CONTRACT: Params carry ``nx_graph`` from ``LoadGraphAction``; regular aspects leave plain dict rows on state; level-1 order follows ``_ROOT_SECTIONS``, deeper lists sorted by label then id.
    INVARIANTS: Summary maps dict rows to ``NodeEntity``; no coordinator objects on ``BaseResult`` fields.
    AI-CORE-END
    """

    class Params(BaseParams):
        nx_graph: Any = Field(description="networkx.DiGraph from LoadGraphAction (node = node_id, attrs node_type/label)")

        model_config = ConfigDict(arbitrary_types_allowed=True)

    class Result(BaseResult):
        """Four ``NodeEntity`` layers: roots, diagrams under roots, graph nodes under roots, ERD rows under domains."""

        level1_nodes: list[NodeEntity] = Field(default_factory=list, description="Root buckets (parent_id unset)")
        level2_diagrams: list[NodeEntity] = Field(default_factory=list, description="Diagram rows under a root id (parent_id = root key)")
        level2_nodes: list[NodeEntity] = Field(default_factory=list, description="Interchange nodes grouped under a root (parent_id = root key)")
        level3_diagrams: list[NodeEntity] = Field(default_factory=list, description="Per-domain ERD rows (parent_id = domain interchange node id)")

        model_config = ConfigDict(arbitrary_types_allowed=True)

    @result_instance("level1_rows", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-1 root bucket rows")
    async def prepare_level1_aspect(
        self,
        params: GetLeftMenuSidebarDataAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> dict[str, Any]:
        rows = [
            {"id": s[0], "parent_id": None, "label": s[1], "type": s[2]}
            for s in _ROOT_SECTIONS
        ]
        return {"level1_rows": rows}

    @result_instance("level1_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_diagram_rows", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-2 diagram rows under roots")
    async def prepare_level2_diagrams_aspect(
        self,
        params: GetLeftMenuSidebarDataAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> dict[str, Any]:
        rows = [
            {"id": "application_interchange_graph", "parent_id": "applications_root", "label": "Interchange graph", "type": "graph"},
            {"id": "domains_all_erd", "parent_id": "domains_root", "label": "ERD — all domains", "type": "erd_all"},
        ]
        rows.sort(key=lambda r: (r["label"].lower(), r["id"]))
        return {
            "level1_rows": list(state["level1_rows"]),
            "level2_diagram_rows": rows,
        }

    @result_instance("level1_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_diagram_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_node_rows", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-2 interchange node rows under roots")
    async def prepare_level2_nodes_aspect(
        self,
        params: GetLeftMenuSidebarDataAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> dict[str, Any]:
        root_by_node_type = {str(row["type"]): str(row["id"]) for row in state["level1_rows"]}
        fallback_root = str(state["level1_rows"][-1]["id"])
        rows: list[dict[str, Any]] = []
        for node_id, data in params.nx_graph.nodes(data=True):
            node_type = str(data.get("node_type", ""))
            label = str(data.get("label", ""))
            root_key = root_by_node_type.get(node_type, fallback_root)
            rows.append({"id": str(node_id), "parent_id": root_key, "label": label, "type": node_type})
        rows.sort(key=lambda r: (r["label"].lower(), r["id"]))
        return {
            "level1_rows": state["level1_rows"],
            "level2_diagram_rows": list(state["level2_diagram_rows"]),
            "level2_node_rows": rows,
        }

    @result_instance("level1_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_diagram_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_node_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level3_diagram_rows", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-3 per-domain ERD diagram rows")
    async def prepare_level3_diagrams_aspect(
        self,
        params: GetLeftMenuSidebarDataAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for node_id, data in params.nx_graph.nodes(data=True):
            if data.get("node_type") != "Domain":
                continue
            label = str(data.get("label", ""))
            nid = str(node_id)
            rows.append(
                {"id": f"erd_domain:{nid}", "parent_id": nid, "label": f"ERD — {label}", "type": "erd_domain"},
            )
        rows.sort(key=lambda r: (r["label"].lower(), r["id"]))
        return {
            "level1_rows": list(state["level1_rows"]),
            "level2_diagram_rows": list(state["level2_diagram_rows"]),
            "level2_node_rows": list(state["level2_node_rows"]),
            "level3_diagram_rows": rows,
        }

    @summary_aspect("Build NodeEntity sidebar result")
    async def build_result_summary(
        self,
        params: GetLeftMenuSidebarDataAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> GetLeftMenuSidebarDataAction.Result:
        def _entities(key: str) -> list[NodeEntity]:
            raw = list(state[key])
            return [NodeEntity.model_validate(r) for r in raw]

        return GetLeftMenuSidebarDataAction.Result(
            level1_nodes=_entities("level1_rows"),
            level2_diagrams=_entities("level2_diagram_rows"),
            level2_nodes=_entities("level2_node_rows"),
            level3_diagrams=_entities("level3_diagram_rows"),
        )
