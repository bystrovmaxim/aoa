# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/build_interchange_graph_data_action.py
# pylint: disable=too-many-branches,too-many-statements
"""
Interchange graph materialization — pure helpers for coordinator / nx graph → G6 JSON.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pure helpers read :class:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator`
or the diagrams ``networkx`` graph and build the JSON consumed by the React G6
viewer: ``nodes``, ``edges``, ``legend_items`` (``type`` + ``color`` only; glyphs
are rendered client-side), ``node_type_map``, ``bubble_plugins``, and ``constants``.

HTTP-facing flow stays in ``GetInterchangeGraphPayloadAction`` with the same
diagrams action pattern as ERD.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import networkx as nx

from aoa.action_machine.graph_model.edges.lifecycle_graph_edge import LifeCycleGraphEdge
from aoa.action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.graph_model.nodes.application_graph_node import ApplicationGraphNode
from aoa.action_machine.graph_model.nodes.checker_graph_node import CheckerGraphNode
from aoa.action_machine.graph_model.nodes.compensator_graph_node import CompensatorGraphNode
from aoa.action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
from aoa.action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.graph_model.nodes.error_handler_graph_node import ErrorHandlerGraphNode
from aoa.action_machine.graph_model.nodes.field_graph_node import FieldGraphNode
from aoa.action_machine.graph_model.nodes.lifecycle_graph_node import LifeCycleGraphNode
from aoa.action_machine.graph_model.nodes.params_graph_node import ParamsGraphNode
from aoa.action_machine.graph_model.nodes.property_field_graph_node import PropertyFieldGraphNode
from aoa.action_machine.graph_model.nodes.regular_aspect_graph_node import RegularAspectGraphNode
from aoa.action_machine.graph_model.nodes.required_context_graph_node import RequiredContextGraphNode
from aoa.action_machine.graph_model.nodes.resource_graph_node import ResourceGraphNode
from aoa.action_machine.graph_model.nodes.result_graph_node import ResultGraphNode
from aoa.action_machine.graph_model.nodes.role_graph_node import RoleGraphNode
from aoa.action_machine.graph_model.nodes.sensitive_graph_node import SensitiveGraphNode
from aoa.action_machine.graph_model.nodes.state_graph_node import StateGraphNode
from aoa.action_machine.graph_model.nodes.summary_aspect_graph_node import SummaryAspectGraphNode
from aoa.graph.association_graph_edge import AssociationGraphEdge
from aoa.graph.base_graph_edge import BaseGraphEdge
from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.edge_relationship import Composition, EdgeRelationship
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator

_INTERNAL_INTERCHANGE_EDGES: frozenset[str] = frozenset({"CHECKS_ASPECT", "COMPENSATES_ASPECT"})

# Seeds ``node_domains`` membership: interchange slot from host row → ``Domain`` graph-node row.
_DOMAIN_EDGE_SLOTS: frozenset[str] = frozenset({"BELONGS_TO", "domain"})

# Host→child interchange slots that are **Composition** or **Aggregation** in the typed
# graph model, used only when G6 edge ``data`` omits ``relationshipName`` (tests / skinny
# payloads). **Association-only** interchange slots (e.g. ``@check_roles``, entity
# ``relations`` navigations, ``@depends`` targets) stay out of this table.
SLOT_ONLY_CONTAINMENT_CHILDREN: frozenset[str] = frozenset(
    {
        "@regular_aspect",
        "@summary_aspect",
        "@result_checker",
        "@compensate",
        "@on_error",
        "@required_context",
        LifeCycleGraphEdge.EDGE_NAME,
        "lifecycle_contains_state",
        "lifecycle_transition",
        "generic:params",
        "generic:result",
        "field",
        "property",
    },
)


def canonical_g6_edge_slot(edge_data: dict[str, Any]) -> str:
    """Normalize viz edge ``label`` so ``belongs_to`` aliases match archived ``BELONGS_TO``."""
    lab = str(edge_data.get("label", "") or "").strip()
    if lab.lower() == "belongs_to":
        return "BELONGS_TO"
    return lab


def g6_edge_propagates_domain_from_host_to_child(e: dict[str, Any]) -> bool:
    """
    Whether host→child edges carry **domain bubble** membership downward.

    Rule: only **whole–part containment** (**Aggregation**, **Composition**) — direct and,
    via the fixpoint in :func:`propagate_node_domains`, indirect. **Association**, **Flow**,
    and other ArchiMate relationship names do **not** extend the bubble, even when the child
    is structurally ``near`` the host (roles, entity lifecycle hubs, peers, …).

    When ``relationshipName`` is missing, known interchange slots in
    :data:`SLOT_ONLY_CONTAINMENT_CHILDREN` are treated as containment (coordinator / skinny
    payloads). If ``relationshipName`` is explicitly ``Association``, that overrides slot
    inference so lifecycle / field slots modeled as peers stay out of the bubble.
    """
    ed = e.get("data") or {}
    if not isinstance(ed, dict):
        ed = {}
    rel = str(ed.get("relationshipName", "") or "").strip()
    if rel.casefold() in ("composition", "aggregation"):
        return True
    slot = canonical_g6_edge_slot(ed)
    if slot in SLOT_ONLY_CONTAINMENT_CHILDREN:
        return rel == "" or not rel.strip()
    return False


# Hull colors for domain bubbles (one per domain graph-node row); distinct from typical node fills.
_BUBBLE_SETS_PALETTE: tuple[str, ...] = (
    "#1783FF",
    "#00C9C9",
    "#F08F56",
    "#D580FF",
    "#5B8FF9",
    "#5AD8A6",
    "#F6BD16",
    "#6F5EF9",
    "#E8684A",
    "#269A99",
    "#B371E3",
    "#5D7092",
)


def domain_sort_key_for_id(g6_nodes: list[dict[str, Any]], nid: str) -> tuple[str, str]:
    node = next(x for x in g6_nodes if str(x["id"]) == nid)
    d = node.get("data") or {}
    return (str(d.get("label", "")), str(d.get("graph_key", nid)))


def propagate_node_domains(  # pylint: disable=too-many-branches
    g6_nodes: list[dict[str, Any]],
    g6_edges: list[dict[str, Any]],
) -> tuple[dict[str, str], list[str], defaultdict[str, set[str]]]:
    """
    Domain bubble membership mirrors coordinator ``domain`` seeding plus **containment** only:

    1. Seed from any interchange slot toward a ``Domain`` row
       (``domain`` edge from typed graph model or legacy ``belongs_to`` / ``BELONGS_TO``).
    2. Propagate along host→child edges whose ``relationshipName`` is ``Composition`` or
       ``Aggregation`` (case-insensitive), or interchange slots in
       :data:`SLOT_ONLY_CONTAINMENT_CHILDREN` when ``relationshipName`` is absent (explicit
       ``Association`` blocks slot-based inference). Transitive closure pulls in nested parts
       at arbitrary depth along those edges only.
    3. Merge domains along checker/compensator bridges
       ``CHECKS_ASPECT`` / ``COMPENSATES_ASPECT``.
    """
    id_to_type: dict[str, str] = {}
    for n in g6_nodes:
        nid = str(n["id"])
        id_to_type[nid] = str((n.get("data") or {}).get("node_type", "unknown"))

    domain_ids = [nid for nid, t in id_to_type.items() if t == DomainGraphNode.NODE_TYPE]

    node_domains: defaultdict[str, set[str]] = defaultdict(set)

    for e in g6_edges:
        ed_raw = e.get("data") or {}
        ed = ed_raw if isinstance(ed_raw, dict) else {}
        slot = canonical_g6_edge_slot(ed)
        if slot not in _DOMAIN_EDGE_SLOTS:
            continue
        src, tgt = str(e["source"]), str(e["target"])
        if id_to_type.get(tgt) != DomainGraphNode.NODE_TYPE:
            continue
        if id_to_type.get(src) == ApplicationGraphNode.NODE_TYPE:
            continue
        node_domains[src].add(tgt)

    changed = True
    while changed:
        changed = False
        for e in g6_edges:
            ed_raw = e.get("data") or {}
            ed = ed_raw if isinstance(ed_raw, dict) else {}
            label = str(ed.get("label", "") or "")
            src, tgt = str(e["source"]), str(e["target"])
            if label in _INTERNAL_INTERCHANGE_EDGES:
                merged = node_domains[src] | node_domains[tgt]
                if not merged:
                    continue
                if merged != node_domains[src] or merged != node_domains[tgt]:
                    node_domains[src] = merged
                    node_domains[tgt] = merged
                    changed = True
            elif g6_edge_propagates_domain_from_host_to_child(e):
                if not node_domains[src]:
                    continue
                before = len(node_domains[tgt])
                node_domains[tgt] |= node_domains[src]
                if len(node_domains[tgt]) > before:
                    changed = True

    return id_to_type, domain_ids, node_domains


def bubble_sets_plugins_for_domains(
    g6_nodes: list[dict[str, Any]],
    g6_edges: list[dict[str, Any]],
    *,
    propagation: tuple[dict[str, str], list[str], defaultdict[str, set[str]]] | None = None,
) -> list[dict[str, Any]]:
    """
    Build G6 ``bubble-sets`` plugins: one hull per ``domain`` graph-node row.

    Members: the domain node, interchange rows seeded with ``domain`` / ``belongs_to``
    toward that domain (``Action``, ``Resource``, ``Entity``, …), and every row reached by
    repeated host→child steps along **Composition** / **Aggregation** only (see
    :func:`g6_edge_propagates_domain_from_host_to_child`), plus checker/compensator bridge
    merges from :func:`propagate_node_domains`.

    The ``application`` graph-node row is never added to a domain bubble.
    """
    if propagation is None:
        propagation = propagate_node_domains(g6_nodes, g6_edges)
    id_to_type, domain_ids, node_domains = propagation

    members_by_domain: dict[str, set[str]] = {}
    for d in domain_ids:
        mem = {d}
        for nid, doms in node_domains.items():
            if d in doms and id_to_type.get(nid) != ApplicationGraphNode.NODE_TYPE:
                mem.add(nid)
        members_by_domain[d] = mem

    palette = _BUBBLE_SETS_PALETTE

    plugins: list[dict[str, Any]] = []
    if domain_ids:
        for i, dom_id in enumerate(sorted(domain_ids, key=lambda did: domain_sort_key_for_id(g6_nodes, did))):
            raw_members = members_by_domain.get(dom_id, {dom_id})
            members = sorted(
                [m for m in raw_members if id_to_type.get(m) != ApplicationGraphNode.NODE_TYPE],
            )
            dom_node = next(n for n in g6_nodes if str(n["id"]) == dom_id)
            ddata = dom_node.get("data") or {}
            label_text = str(ddata.get("label") or ddata.get("graph_key") or dom_id)
            base = palette[i % len(palette)]
            plugins.append(
                {
                    "key": f"bubble-domain-{i}",
                    "type": "bubble-sets",
                    "members": members,
                    "labelText": label_text,
                    "fill": base,
                    "stroke": base,
                    "labelFill": "#fff",
                    "labelPadding": 2,
                    "labelBackgroundFill": base,
                    "labelBackgroundRadius": 5,
                },
            )

    return plugins


def dag_cycle_violation_keys_from_coordinator(
    coordinator: NodeGraphCoordinator,
) -> set[tuple[str, str, str]]:
    """Match keys used by :func:`interchange_g6_payload_from_nx` for forbidden-cycle styling."""
    viol = getattr(coordinator, "dag_cycle_violations", ()) or ()
    return {(str(v.source_node_id), str(v.target_node_id), str(v.edge_name)) for v in viol}


G6_CDN_URL = "https://unpkg.com/@antv/g6@5/dist/g6.min.js"

# Okabe–Ito ``#E41A1C`` is reserved for debug DAG-cycle violations (edges + incident nodes only).
DAG_CYCLE_VIOLATION_COLOR = "#E41A1C"

# Fixed fill per interchange graph-node ``node_type`` (stable across graphs — not alphabetical).
# Palette: Okabe–Ito / Tol-inspired, maximally distinct hues; ``Application`` is black (root).
# ``Action`` is indigo so saturated red stays exclusive to DAG violation styling.
# Keys use interchange ``node_type`` ids (``NODE_TYPE`` on graph-node classes where applicable).
NODE_TYPE_FILL_COLORS: dict[str, str] = {
    ApplicationGraphNode.NODE_TYPE: "#000000",
    ActionGraphNode.NODE_TYPE: "#4F46E5",
    DomainGraphNode.NODE_TYPE: "#377EB8",
    ResourceGraphNode.NODE_TYPE: "#7570B3",
    RequiredContextGraphNode.NODE_TYPE: "#4DAF4A",
    RegularAspectGraphNode.NODE_TYPE: "#FF7F00",
    SummaryAspectGraphNode.NODE_TYPE: "#FF7F00",
    CheckerGraphNode.NODE_TYPE: "#A65628",
    CompensatorGraphNode.NODE_TYPE: "#F781BF",
    ErrorHandlerGraphNode.NODE_TYPE: "#FCD34D",
    EntityGraphNode.NODE_TYPE: "#1B9E77",
    LifeCycleGraphNode.NODE_TYPE: "#00798C",
    StateGraphNode.NODE_TYPE_STATE_INITIAL: "#9575CD",
    StateGraphNode.NODE_TYPE_STATE_INTERMEDIATE: "#6A51A3",
    StateGraphNode.NODE_TYPE_STATE_FINAL: "#452E7A",
    RoleGraphNode.NODE_TYPE: "#66A61E",
    SensitiveGraphNode.NODE_TYPE: "#A855F7",
    ParamsGraphNode.NODE_TYPE: "#CAB2D6",
    ResultGraphNode.NODE_TYPE: "#B2DF8A",
    # Field and PropertyField share one hue; glyphs in `icons` distinguish them.
    FieldGraphNode.NODE_TYPE: "#6B5B95",
    PropertyFieldGraphNode.NODE_TYPE: "#6B5B95",
}

DEFAULT_COLOR = "#95a5a6"

GRAPH_NODE_VISUAL_PX = 24

_SUBTITLE_GRAPH_NODE_TYPES: frozenset[str] = frozenset({
    RegularAspectGraphNode.NODE_TYPE,
    SummaryAspectGraphNode.NODE_TYPE,
    CheckerGraphNode.NODE_TYPE,
    CompensatorGraphNode.NODE_TYPE,
    ErrorHandlerGraphNode.NODE_TYPE,
    RequiredContextGraphNode.NODE_TYPE,
})

def _graph_node_key(node: dict[str, Any]) -> str:
    nm = str(node.get("id") or node.get("name", "") or "").strip()
    if nm:
        return nm
    nt = str(node.get("node_type", "") or "").strip()
    return nt or "unknown"


def _graph_node_subtitle(node: dict[str, Any]) -> str:
    nt = str(node.get("node_type", "unknown"))
    if nt in _SUBTITLE_GRAPH_NODE_TYPES:
        lab = str(node.get("label", "") or "").strip()
        if lab:
            return lab
    short = _element_short_name(node)
    return f"{nt}\n{short}"


def _element_short_name(node: dict[str, Any]) -> str:
    nt = str(node.get("node_type", "") or "").strip()
    if nt in _SUBTITLE_GRAPH_NODE_TYPES:
        lab = str(node.get("label", "") or "").strip()
        if lab:
            return lab
    raw = str(
        node.get("id") or node.get("name", "") or node.get("label", "") or ""
    ).strip()
    if not raw:
        return "?"
    if "." in raw:
        return raw.rsplit(".", 1)[-1]
    return raw


def _node_title_for_visual(node: dict[str, Any]) -> str:
    title = str(node.get("label", "") or node.get("display_name", "") or "").strip()
    if title:
        return title
    return _element_short_name(node)


def _element_qualified_name(node: dict[str, Any]) -> str:
    return str(node.get("id") or node.get("name", "") or node.get("label", "") or "?")


def _fill_color_for_graph_node_type(node_type: str) -> str:
    """
    Stable fill for one ``node_type`` string.

    Known types use :data:`NODE_TYPE_FILL_COLORS`. Any other label uses
    :data:`DEFAULT_COLOR` so such nodes share one neutral disk behind the
    generic fork icon.
    """
    t = str(node_type).strip()
    if not t or t == "unknown":
        return DEFAULT_COLOR
    if t in NODE_TYPE_FILL_COLORS:
        return NODE_TYPE_FILL_COLORS[t]
    return DEFAULT_COLOR


def _color_map_for_graph_node_types(node_types: Iterable[str]) -> dict[str, str]:
    """Map each distinct ``node_type`` present in the graph to its fill color."""
    unique = sorted({str(t) for t in node_types if str(t)})
    return {t: _fill_color_for_graph_node_type(t) for t in unique}


def _d3_seed_xy_for_nodes(  # pylint: disable=too-many-branches
    g6_nodes: list[dict[str, Any]],
    id_to_type: dict[str, str],
    domain_ids: list[str],
    node_domains: defaultdict[str, set[str]],
) -> dict[str, tuple[float, float]]:
    """
    Place each node in a **primary** domain wedge (``min`` of domain ids) on a
    circle; ``application`` and nodes without propagated domain sit in a small
    cluster at the origin. Reduces edge crossings versus a single force blob.
    """
    sorted_domain_ids = sorted(domain_ids, key=lambda did: domain_sort_key_for_id(g6_nodes, did))
    d_count = len(sorted_domain_ids)
    n_total = len(g6_nodes)
    ring_r = 240.0 + min(520.0, 18.0 * math.sqrt(max(n_total, 1)))

    out: dict[str, tuple[float, float]] = {}

    center_ids: list[str] = []
    for n in g6_nodes:
        nid = str(n["id"])
        if id_to_type.get(nid) == ApplicationGraphNode.NODE_TYPE:
            center_ids.append(nid)
            continue
        if id_to_type.get(nid) == DomainGraphNode.NODE_TYPE:
            continue
        if not node_domains.get(nid):
            center_ids.append(nid)

    for j, nid in enumerate(sorted(center_ids)):
        ang = 2 * math.pi * j / max(len(center_ids), 1)
        r = 38.0 + (j % 6) * 6.0
        out[nid] = (r * math.cos(ang), r * math.sin(ang))

    for i, dom_id in enumerate(sorted_domain_ids):
        theta = 2 * math.pi * i / max(d_count, 1)
        cx = ring_r * math.cos(theta)
        cy = ring_r * math.sin(theta)

        members: list[str] = []
        for n in g6_nodes:
            nid = str(n["id"])
            if id_to_type.get(nid) == ApplicationGraphNode.NODE_TYPE:
                continue
            if nid == dom_id:
                members.append(nid)
                continue
            doms = node_domains.get(nid, set())
            if doms and min(doms) == dom_id:
                members.append(nid)

        def _member_sort_key(nid: str, anchor: str = dom_id) -> tuple[int, str]:
            return (0 if nid == anchor else 1, nid)

        members = sorted(frozenset(members), key=_member_sort_key)

        for j, nid in enumerate(members):
            sub_ang = 2 * math.pi * j / max(len(members), 1)
            r_loc = 28.0 + (j % 8) * 5.0
            out[nid] = (cx + r_loc * math.cos(sub_ang), cy + r_loc * math.sin(sub_ang))

    for n in g6_nodes:
        nid = str(n["id"])
        if nid not in out:
            out[nid] = (0.0, 0.0)

    return out


def _node_obj_display(node_obj: object) -> str:
    if isinstance(node_obj, type):
        return f"{node_obj.__module__}.{node_obj.__qualname__}"
    return str(node_obj)


def interchange_node_to_visual_dict(node: BaseGraphNode[Any]) -> dict[str, Any]:
    """Shallow interchange node mapping (optional callers / tests)."""
    return {
        "id": node.node_id,
        "node_type": node.node_type,
        "label": node.label,
        "properties": dict(node.properties),
        "node_obj": _node_obj_display(node.node_obj),
    }


def interchange_model_dict_for_g6(node: BaseGraphNode[Any]) -> dict[str, Any]:
    """
    Graph-node payload ``dict`` for the G6 helpers in this module: ``id``, ``node_type``,
    ``label``, ``properties``, ``node_obj`` (string), aligned with interchange graph-node fields.
    """
    merged = interchange_node_to_visual_dict(node)
    text = str(merged.get("label", "") or "").strip()
    if not text:
        vid = str(merged["id"])
        merged["label"] = vid.rsplit(".", maxsplit=1)[-1] if "." in vid else vid
    return merged


def interchange_edge_to_visual_dict(edge: BaseGraphEdge) -> dict[str, Any]:
    """
    Edge payload for interchange G6 export.

    Includes ArchiMate-style ``source_attachment`` / ``target_attachment`` / ``line_style``
    (``StrEnum`` string values) plus ``relationship_name`` for tooltips or debugging.

    For ``COMPOSITION`` links to a ``RegularAspect`` / ``SummaryAspect`` / ``Compensator`` / ``error_handler``
    graph node, attachment graphics are swapped so the diamond sits on the **target** end (UML aggregate/composite whole); graph topology
    stays ``Action → callable node``.
    """
    er = edge.edge_relationship
    src_att = er.source_attachment.value
    tgt_att = er.target_attachment.value
    if isinstance(er, Composition) and edge.target_node_type in (
        RegularAspectGraphNode.NODE_TYPE,
        SummaryAspectGraphNode.NODE_TYPE,
        CompensatorGraphNode.NODE_TYPE,
        ErrorHandlerGraphNode.NODE_TYPE,
    ):
        src_att, tgt_att = tgt_att, src_att
    return {
        "edge_type": edge.edge_name,
        "is_dag": edge.is_dag,
        "relationship_name": er.archimate_name,
        "source_attachment": src_att,
        "target_attachment": tgt_att,
        "line_style": er.line_style.value,
    }


def _edge_visual_dict_from_relationship(er: EdgeRelationship, edge_type: str, is_dag: bool) -> dict[str, Any]:
    """Shallow visual dict from a standalone :class:`~aoa.graph.edge_relationship.EdgeRelationship` (nx path)."""
    return {
        "edge_type": edge_type,
        "is_dag": is_dag,
        "relationship_name": er.archimate_name,
        "source_attachment": er.source_attachment.value,
        "target_attachment": er.target_attachment.value,
        "line_style": er.line_style.value,
    }


def _edge_visual_for_topology_edge(edge_name: str, is_dag: bool) -> dict[str, Any]:
    """
    Edge visual dict when only ``edge_name`` / ``is_dag`` are known (e.g. :class:`networkx.DiGraph`).

    Interchange slots listed in :data:`SLOT_ONLY_CONTAINMENT_CHILDREN` are **Composition** /
    **Aggregation** in the typed graph; marking them as ``Composition`` here keeps
    :func:`propagate_node_domains` transitive closure aligned with the coordinator path
    (otherwise every nx edge defaulted to ``Association`` and domain hulls missed deep parts).
    """
    raw = str(edge_name or "").strip()
    elabel = "BELONGS_TO" if raw.lower() == "belongs_to" else raw
    slot = canonical_g6_edge_slot({"label": elabel})
    if slot in SLOT_ONLY_CONTAINMENT_CHILDREN:
        return _edge_visual_dict_from_relationship(Composition(), raw or "rel", is_dag)
    e = AssociationGraphEdge(
        edge_name=edge_name or "rel",
        is_dag=is_dag,
        target_node_id="_",
    )
    return interchange_edge_to_visual_dict(e)


def interchange_pygraph_for_g6(coordinator: NodeGraphCoordinator) -> Any:
    """
    Clone the coordinator graph with dict graph-node payloads on nodes and ``BaseGraphEdge`` data on edges.

    Uses :meth:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator.get_all_nodes` and each node's
    ``edges`` (same topology as after :meth:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator.build`).
    ``rustworkx`` is imported only inside this function; the return value is a ``PyDiGraph`` for
    callers that still want graph nodes stored as dict payloads (e.g. tests).
    """
    import rustworkx as rx  # pylint: disable=import-outside-toplevel

    out = rx.PyDiGraph()
    nodes = coordinator.get_all_nodes()
    id_to_idx: dict[str, int] = {}
    for n in nodes:
        id_to_idx[n.node_id] = out.add_node(interchange_node_to_visual_dict(n))
    for n in nodes:
        s = id_to_idx[n.node_id]
        for edge in n.get_all_edges():
            t = id_to_idx[edge.target_node_id]
            out.add_edge(s, t, interchange_edge_to_visual_dict(edge))
    return out

def build_interchange_g6_visual_payload(
    g6_nodes: list[dict[str, Any]],
    g6_edges: list[dict[str, Any]],
    legend_items: list[dict[str, Any]],
    node_type_map: dict[str, str],
    *,
    title: str,
) -> dict[str, Any]:
    """Layout seeds, bubble plugins, and graph constants for the Maxitor React G6 viewer."""
    propagation = propagate_node_domains(g6_nodes, g6_edges)
    seed_xy = _d3_seed_xy_for_nodes(g6_nodes, *propagation)
    for n in g6_nodes:
        sx, sy = seed_xy[str(n["id"])]
        n["style"] = {"x": sx, "y": sy}

    bubble_plugins = bubble_sets_plugins_for_domains(g6_nodes, g6_edges, propagation=propagation)
    return {
        "title": title,
        "nodes": g6_nodes,
        "edges": g6_edges,
        "legend_items": legend_items,
        "node_type_map": node_type_map,
        "bubble_plugins": bubble_plugins,
        "constants": {
            "node_visual_px": GRAPH_NODE_VISUAL_PX,
            "dag_cycle_violation_color": DAG_CYCLE_VIOLATION_COLOR,
            "default_color": DEFAULT_COLOR,
            "g6_cdn_url": G6_CDN_URL,
        },
    }


def interchange_g6_payload_from_coordinator(  # pylint: disable=too-many-statements
    coordinator: NodeGraphCoordinator,
    *,
    title: str = "ActionMachine Graph",
    node_colors: dict[str, str] | None = None,
) -> dict[str, Any]:
    nodes_tuple = coordinator.get_all_nodes()
    n_nodes = len(nodes_tuple)

    # Build nodes from ``BaseGraphNode`` payloads (interchange-native, ``get_all_nodes`` order).
    idx_to_node: dict[int, dict[str, Any]] = {}
    for idx, raw in enumerate(nodes_tuple):
        if not isinstance(raw, BaseGraphNode):
            msg = (
                f"interchange_g6_payload_from_coordinator expects BaseGraphNode payloads on nodes; "
                f"got {type(raw).__name__!r} at coordinator node index {idx}"
            )
            raise TypeError(msg)
        idx_to_node[idx] = interchange_model_dict_for_g6(raw)

    colors = _color_map_for_graph_node_types(
        str(idx_to_node[idx].get("node_type", "unknown"))
        for idx in range(n_nodes)
    )
    if node_colors:
        colors = {**colors, **node_colors}

    violations = getattr(coordinator, "dag_cycle_violations", ())
    cycle_violation_keys = {
        (str(v.source_node_id), str(v.target_node_id), str(v.edge_name)) for v in violations
    }
    dag_cycle_violation_incident_ids: set[str] = set()
    for v in violations:
        dag_cycle_violation_incident_ids.add(str(v.source_node_id))
        dag_cycle_violation_incident_ids.add(str(v.target_node_id))

    g6_nodes: list[dict[str, Any]] = []
    g6_edges: list[dict[str, Any]] = []

    def _edge_label_and_dag(edge_data: Any) -> tuple[str, bool]:
        if isinstance(edge_data, BaseGraphEdge):
            label = edge_data.edge_name
            if label == "belongs_to":
                label = "BELONGS_TO"
            return str(label), bool(edge_data.is_dag)
        if isinstance(edge_data, dict):
            return str(edge_data.get("edge_type", "")), bool(edge_data.get("is_dag"))
        return str(edge_data), False

    for idx in range(n_nodes):
        node = idx_to_node[idx]
        node_type = str(node.get("node_type", "unknown"))
        short = _element_short_name(node)
        ntitle = _node_title_for_visual(node)
        graph_node_subtitle = _graph_node_subtitle(node)
        graph_key = _graph_node_key(node)
        qualified = _element_qualified_name(node)
        base_fill = colors.get(node_type, DEFAULT_COLOR)
        interchange_nid = str(node.get("id", ""))
        is_dag_violation_incident = interchange_nid in dag_cycle_violation_incident_ids
        fill = DAG_CYCLE_VIOLATION_COLOR if is_dag_violation_incident else base_fill
        g6_nodes.append({
            "id": str(idx),
            "data": {
                "label": short,
                "title": ntitle,
                "graph_node_subtitle": graph_node_subtitle,
                "graph_key": graph_key,
                "qualified": qualified,
                "node_type": node_type,
                "typeFill": base_fill,
                "fill": fill,
                "isDagCycleViolationIncident": is_dag_violation_incident,
            },
        })

    id_to_idx = {n.node_id: i for i, n in enumerate(nodes_tuple)}
    ei = 0
    for src_idx, interchange_node in enumerate(nodes_tuple):
        for edge in interchange_node.get_all_edges():
            tgt = id_to_idx[edge.target_node_id]
            if src_idx == tgt:
                continue
            elabel, is_dag = _edge_label_and_dag(edge)
            vis = interchange_edge_to_visual_dict(edge)
            is_forbidden_dag_cycle = (interchange_node.node_id, edge.target_node_id, edge.edge_name) in cycle_violation_keys
            g6_edges.append({
                "id": f"e-{src_idx}-{tgt}-{ei}",
                "source": str(src_idx),
                "target": str(tgt),
                "data": {
                    "label": elabel,
                    "isDag": is_dag,
                    "isForbiddenDagCycle": is_forbidden_dag_cycle,
                    "relationshipName": vis["relationship_name"],
                    "sourceAttachment": vis["source_attachment"],
                    "targetAttachment": vis["target_attachment"],
                    "lineStyle": vis["line_style"],
                },
            })
            ei += 1

    used_types = sorted({str(n["data"]["node_type"]) for n in g6_nodes})
    legend_items = [
        {
            "type": nt,
            "color": colors.get(nt, DEFAULT_COLOR),
        }
        for nt in used_types
        if nt != "unknown"
    ]
    if not legend_items:
        legend_items = [
            {
                "type": "unknown",
                "color": DEFAULT_COLOR,
            },
        ]

    node_type_map = {
        str(idx): idx_to_node[idx].get("node_type", "unknown")
        for idx in range(n_nodes)
    }

    return build_interchange_g6_visual_payload(
        g6_nodes,
        g6_edges,
        legend_items,
        node_type_map,
        title=title,
    )


def interchange_g6_payload_from_nx(  # pylint: disable=too-many-statements
    nx_graph: nx.DiGraph[Any],
    *,
    title: str = "ActionMachine Graph",
    node_colors: dict[str, str] | None = None,
    cycle_violation_keys: set[tuple[str, str, str]] | None = None,
) -> dict[str, Any]:
    """Build the same G6 graph payload from a :class:`networkx.DiGraph` (e.g. :class:`LoadGraphAction` result)."""
    viol = cycle_violation_keys or set()
    dag_cycle_violation_incident_ids: set[str] = set()
    for src, tgt, _ename in viol:
        dag_cycle_violation_incident_ids.add(str(src))
        dag_cycle_violation_incident_ids.add(str(tgt))

    node_ids = sorted(nx_graph.nodes(), key=str)
    idx_to_node: dict[str, dict[str, Any]] = {}
    for nid in node_ids:
        attrs = nx_graph.nodes[nid]
        row: dict[str, Any] = dict(attrs) if isinstance(attrs, dict) else {}
        node_type = str(row.get("node_type", "unknown"))
        label = str(row.get("label", "") or "").strip() or str(nid)
        idx_to_node[str(nid)] = {
            "id": str(nid),
            "node_type": node_type,
            "label": label,
            "properties": {k: v for k, v in row.items() if k not in ("node_type", "label")},
            "node_obj": "",
        }

    colors = _color_map_for_graph_node_types(
        str(node.get("node_type", "unknown")) for node in idx_to_node.values()
    )
    if node_colors:
        colors = {**colors, **node_colors}

    g6_nodes: list[dict[str, Any]] = []
    g6_edges: list[dict[str, Any]] = []

    for nid in node_ids:
        key = str(nid)
        node = idx_to_node[key]
        node_type = str(node.get("node_type", "unknown"))
        short = _element_short_name(node)
        ntitle = _node_title_for_visual(node)
        graph_node_subtitle = _graph_node_subtitle(node)
        graph_key = _graph_node_key(node)
        qualified = _element_qualified_name(node)
        base_fill = colors.get(node_type, DEFAULT_COLOR)
        interchange_nid = str(node.get("id", ""))
        is_dag_violation_incident = interchange_nid in dag_cycle_violation_incident_ids
        fill = DAG_CYCLE_VIOLATION_COLOR if is_dag_violation_incident else base_fill
        g6_nodes.append({
            "id": key,
            "data": {
                "label": short,
                "title": ntitle,
                "graph_node_subtitle": graph_node_subtitle,
                "graph_key": graph_key,
                "qualified": qualified,
                "node_type": node_type,
                "typeFill": base_fill,
                "fill": fill,
                "isDagCycleViolationIncident": is_dag_violation_incident,
            },
        })

    ei = 0
    for u, v, edata in nx_graph.edges(data=True):
        u_s, v_s = str(u), str(v)
        if u_s not in idx_to_node or v_s not in idx_to_node:
            continue
        raw_en = str(edata.get("edge_name", "") or "")
        elabel = raw_en
        if elabel == "belongs_to":
            elabel = "BELONGS_TO"
        is_dag = bool(edata.get("is_dag", False))
        vis = _edge_visual_for_topology_edge(raw_en, is_dag)
        is_forbidden = (u_s, v_s, raw_en) in viol
        g6_edges.append({
            "id": f"e-{u_s}-{v_s}-{ei}",
            "source": u_s,
            "target": v_s,
            "data": {
                "label": elabel,
                "isDag": is_dag,
                "isForbiddenDagCycle": is_forbidden,
                "relationshipName": vis["relationship_name"],
                "sourceAttachment": vis["source_attachment"],
                "targetAttachment": vis["target_attachment"],
                "lineStyle": vis["line_style"],
            },
        })
        ei += 1

    used_types = sorted({str(n["data"]["node_type"]) for n in g6_nodes})
    legend_items = [
        {
            "type": nt,
            "color": colors.get(nt, DEFAULT_COLOR),
        }
        for nt in used_types
        if nt != "unknown"
    ]
    if not legend_items:
        legend_items = [
            {
                "type": "unknown",
                "color": DEFAULT_COLOR,
            },
        ]

    node_type_map = {k: node.get("node_type", "unknown") for k, node in idx_to_node.items()}

    return build_interchange_g6_visual_payload(
        g6_nodes,
        g6_edges,
        legend_items,
        node_type_map,
        title=title,
    )
