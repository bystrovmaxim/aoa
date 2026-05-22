# packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/left_sidebar_action.py
"""
GetLeftMenuSidebarDataAction — left menu rows for diagrams from a NetworkX graph.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materialize flat ``NodeEntity`` lists (by depth / role) from a ``LoadGraphAction``
``DiGraph`` so the UI can render roots, per-root diagrams, interchange nodes, and
level-3 diagram rows (per-domain entity diagram, per-entity diagram row, per-lifecycle field
diagram) using ``parent_id`` links only. **Level-1 order matches**
``_ROOT_SECTIONS`` (Applications through Resources); clients must preserve
``Result.level1_nodes`` order. Deeper rows use ``ordinal`` when present (see
``prepare_level3_diagrams_aspect``); otherwise alphabetical by label, then id.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import ConfigDict, Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.core.entities.node_entity import NodeEntity
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain


def _sidebar_row_dicts(state: BaseState, key: str) -> list[dict[str, Any]]:
    """Narrow ``state[key]`` to row dicts (pipeline values are typed as ``object``)."""
    return cast(list[dict[str, Any]], state[key])


_ROOT_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("applications_root", "Applications", "Application"),
    ("domains_root", "Domains", "Domain"),
    ("roles_root", "Roles", "Role"),
    ("actions_root", "Actions", "Action"),
    ("entities_root", "Entities", "Entity"),
    ("resources_root", "Resources", "Resource"),
)


def _diagram_view_label(name: str) -> str:
    """Append `` view`` to diagram display names (sidebar and aligned payloads)."""
    base = str(name).strip()
    if base.endswith(" view"):
        return base
    return f"{base} view"


def _lifecycle_nodes_for_entity(graph: Any, entity_id: str) -> list[tuple[str, str]]:
    """
    Return ``(lifecycle_vertex_id, label)`` for lifecycles owned by this entity, sorted.

    Only ``lifecycle`` composition edges from the entity are counted (see
    :class:`~aoa.action_machine.graph.edges.lifecycle_graph_edge.LifeCycleGraphEdge`
    and :meth:`LoadGraphAction.prepare_topology_aspect`, which sets ``edge_name`` on
    NetworkX edges). A generic 2-hop scan is unsafe: e.g. ``Entity → Domain`` then
    ``Domain → … → Lifecycle`` can reach another host's lifecycle and duplicate rows.
    """
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    eid = str(entity_id)
    if not graph.has_node(eid):
        return []

    for _src, target, attrs in graph.out_edges(eid, data=True):
        if str(attrs.get("edge_name", "")) != "lifecycle":
            continue
        tdata = graph.nodes[target]
        if str(tdata.get("node_type", "")) != "Lifecycle":
            continue
        lid = str(target)
        if lid in seen:
            continue
        seen.add(lid)
        out.append((lid, str(tdata.get("label", lid))))

    if not out:
        # Backward-compatible fallback when edges lack ``edge_name`` (direct Lifecycle only).
        for mid in graph.successors(eid):
            mid_data = graph.nodes[mid]
            if str(mid_data.get("node_type", "")) != "Lifecycle":
                continue
            lid = str(mid)
            if lid in seen:
                continue
            seen.add(lid)
            out.append((lid, str(mid_data.get("label", lid))))

    out.sort(key=lambda t: (t[1].lower(), t[0]))
    return out


def _lifecycle_state_machine_row_title(field_name: str) -> str:
    """
    Sidebar title for one lifecycle field under an entity: first snake segment capitalised,
    remaining segments lowercased, joined with spaces, then trailing `` view``.

    Example: ``counterparty_linkage_lifecycle`` → ``Counterparty linkage lifecycle view``.
    """
    parts = [p for p in str(field_name).strip().split("_") if p]
    if not parts:
        return _diagram_view_label("Lifecycle")
    head = parts[0][:1].upper() + parts[0][1:].lower()
    if len(parts) == 1:
        display = head
    else:
        tail = " ".join(p.lower() for p in parts[1:])
        display = f"{head} {tail}"
    return _diagram_view_label(display)


@meta(description="Build left-menu sidebar NodeEntity lists from NetworkX graph view", domain=DiagramsDomain)
@check_roles(NoneRole)
class GetLeftMenuSidebarDataAction(
    BaseAction["GetLeftMenuSidebarDataAction.Params", "GetLeftMenuSidebarDataAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Emit four ``NodeEntity`` layers for a simple parent-linked sidebar hierarchy.
    CONTRACT: Params carry ``nx_graph`` from ``LoadGraphAction``; regular aspects leave plain dict rows on state; level-1 order is exactly ``_ROOT_SECTIONS`` (do not reorder in clients); level-3 diagram rows use ``ordinal`` for sibling order where required.
    INVARIANTS: Summary maps dict rows to ``NodeEntity``; no coordinator objects on ``BaseResult`` fields.
    AI-CORE-END
    """

    class Params(BaseParams):
        nx_graph: Any = Field(description="networkx.DiGraph from LoadGraphAction (node = node_id, attrs node_type/label)")

        model_config = ConfigDict(arbitrary_types_allowed=True)

    class Result(BaseResult):
        """Four ``NodeEntity`` layers: roots, diagrams under roots, interchange nodes under roots, diagram rows under domains and entities."""

        level1_nodes: list[NodeEntity] = Field(default_factory=list, description="Root buckets (parent_id unset)")
        level2_diagrams: list[NodeEntity] = Field(default_factory=list, description="Diagram rows under a root id (parent_id = root key)")
        level2_nodes: list[NodeEntity] = Field(default_factory=list, description="Interchange nodes grouped under a root (parent_id = root key)")
        level3_diagrams: list[NodeEntity] = Field(
            default_factory=list,
            description=(
                "Diagram rows under a domain or entity interchange node: "
                "``erd_domain`` (parent = domain id; entity domain diagram), ``use_case_domain`` (UML use-case diagram), "
                "``entity_class_diagram`` (id = entity id, parent = entity id), "
                "``lifecycle_state_diagram`` (id = lifecycle vertex id, parent = entity id). "
                "Use ``ordinal`` for stable order: entity row first, then lifecycle rows."
            ),
        )

        model_config = ConfigDict(arbitrary_types_allowed=True)

    @result_instance("level1_rows", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-1 root bucket rows")
    async def prepare_level1_aspect(
        self,
        params: GetLeftMenuSidebarDataAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
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
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        rows = [
            {
                "id": "application_interchange_graph",
                "parent_id": "applications_root",
                "label": _diagram_view_label("Full graph"),
                "type": "graph",
            },
            {
                "id": "domains_all_erd",
                "parent_id": "domains_root",
                "label": _diagram_view_label("Entity all domains"),
                "type": "erd_all",
            },
        ]
        rows.sort(key=lambda r: (r["label"].lower(), r["id"]))
        return {
            "level1_rows": _sidebar_row_dicts(state, "level1_rows"),
            "level2_diagram_rows": rows,
        }

    @result_instance("level1_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_diagram_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_node_rows", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-2 interchange node rows under roots")
    async def prepare_level2_nodes_aspect(
        self,
        params: GetLeftMenuSidebarDataAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        level1 = _sidebar_row_dicts(state, "level1_rows")
        root_by_node_type = {str(row["type"]): str(row["id"]) for row in level1}
        fallback_root = str(level1[-1]["id"])
        rows: list[dict[str, Any]] = []
        for node_id, data in params.nx_graph.nodes(data=True):
            node_type = str(data.get("node_type", ""))
            label = str(data.get("label", ""))
            root_key = root_by_node_type.get(node_type, fallback_root)
            rows.append({"id": str(node_id), "parent_id": root_key, "label": label, "type": node_type})
        rows.sort(key=lambda r: (r["label"].lower(), r["id"]))
        return {
            "level1_rows": level1,
            "level2_diagram_rows": _sidebar_row_dicts(state, "level2_diagram_rows"),
            "level2_node_rows": rows,
        }

    @result_instance("level1_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_diagram_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level2_node_rows", list, required=True)  # type: ignore[untyped-decorator]
    @result_instance("level3_diagram_rows", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Level-3 diagram rows (domain entity diagram, entity diagram, lifecycle field)")
    async def prepare_level3_diagrams_aspect(
        self,
        params: GetLeftMenuSidebarDataAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        graph = params.nx_graph
        for node_id, data in graph.nodes(data=True):
            if data.get("node_type") != "Domain":
                continue
            label = str(data.get("label", ""))
            nid = str(node_id)
            rows.append(
                {
                    "id": f"erd_domain:{nid}",
                    "parent_id": nid,
                    "label": _diagram_view_label(f"Entity domain — {label}"),
                    "type": "erd_domain",
                    "ordinal": 0,
                },
            )
            rows.append(
                {
                    "id": f"use_case_domain:{nid}",
                    "parent_id": nid,
                    "label": _diagram_view_label(f"Use case — {label}"),
                    "type": "use_case_domain",
                    "ordinal": 1,
                },
            )
        for node_id, data in graph.nodes(data=True):
            if data.get("node_type") != "Entity":
                continue
            nid = str(node_id)
            rows.append(
                {
                    "id": nid,
                    "parent_id": nid,
                    "label": _diagram_view_label("Entity"),
                    "type": "entity_class_diagram",
                    "ordinal": 0,
                },
            )
            ordinal = 1
            for lifecycle_id, lifecycle_label in _lifecycle_nodes_for_entity(graph, nid):
                rows.append(
                    {
                        "id": lifecycle_id,
                        "parent_id": nid,
                        "label": _lifecycle_state_machine_row_title(lifecycle_label),
                        "type": "lifecycle_state_diagram",
                        "ordinal": ordinal,
                    },
                )
                ordinal += 1
        rows.sort(key=lambda r: (str(r["parent_id"]).lower(), int(r.get("ordinal", 10**9)), r["label"].lower(), r["id"]))
        return {
            "level1_rows": _sidebar_row_dicts(state, "level1_rows"),
            "level2_diagram_rows": _sidebar_row_dicts(state, "level2_diagram_rows"),
            "level2_node_rows": _sidebar_row_dicts(state, "level2_node_rows"),
            "level3_diagram_rows": rows,
        }

    @summary_aspect("Build NodeEntity sidebar result")
    async def build_result_summary(
        self,
        params: GetLeftMenuSidebarDataAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GetLeftMenuSidebarDataAction.Result:
        return GetLeftMenuSidebarDataAction.Result(
            level1_nodes=[NodeEntity.model_validate(r) for r in _sidebar_row_dicts(state, "level1_rows")],
            level2_diagrams=[NodeEntity.model_validate(r) for r in _sidebar_row_dicts(state, "level2_diagram_rows")],
            level2_nodes=[NodeEntity.model_validate(r) for r in _sidebar_row_dicts(state, "level2_node_rows")],
            level3_diagrams=[NodeEntity.model_validate(r) for r in _sidebar_row_dicts(state, "level3_diagram_rows")],
        )
