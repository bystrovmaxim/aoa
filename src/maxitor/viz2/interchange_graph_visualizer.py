# src/maxitor/viz2/interchange_graph_visualizer.py
"""
HTML export for :class:`~graph.node_graph_coordinator.NodeGraphCoordinator` graphs.

Vertices carry :class:`~graph.base_graph_node.BaseGraphNode` and edges carry
:class:`~graph.base_graph_edge.BaseGraphEdge`. :func:`export_interchange_axes_graph_html`
writes a standalone AntV G6 HTML file for an **already built** coordinator to
:data:`INTERCHANGE_AXES_GRAPH_HTML_PATH`
(the repo's ``archive/logs/graph_node_2.html``, next to ``app_graph.html`` from
:mod:`maxitor.viz1.visualizer`; UTF-8, parent directories created as needed).
It does **not** call :meth:`~graph.node_graph_coordinator.NodeGraphCoordinator.build` or change inspectors.

:func:`generate_interchange_g6_html` takes the same built coordinator and serializes **only**
:meth:`~graph.node_graph_coordinator.NodeGraphCoordinator.get_all_nodes` plus each node's ``edges``
(no extra vertices, no ``rustworkx`` in this module's public API).

Layout, legend, domain bubbles, and the inspector panel follow the same G6 behaviour as
the legacy HTML export, without importing the old coordinator or dict-normalization
pipeline.

Edges use G6 ``line`` with default style; ``stroke`` / arrow colour follow ``isDag`` only
(**red** vs **slate**) and never change on hover. On node hover, incident edges get state
``active``. Edge ``data`` still carries relationship fields for tests.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Iterable
from html import escape as html_escape
from pathlib import Path
from typing import Any

from action_machine.auth.graph_model.role_graph_node import RoleGraphNode
from action_machine.domain.graph_model.domain_graph_node import DomainGraphNode
from action_machine.domain.graph_model.entity_graph_node import EntityGraphNode
from action_machine.legacy.interchange_vertex_labels import (
    APPLICATION_VERTEX_TYPE,
    CHECKER_VERTEX_TYPE,
    COMPENSATOR_VERTEX_TYPE,
    SERVICE_VERTEX_TYPE,
    SUMMARY_ASPECT_VERTEX_TYPE,
)
from action_machine.model.graph_model.action_graph_node import ActionGraphNode
from action_machine.model.graph_model.params_graph_node import ParamsGraphNode
from action_machine.model.graph_model.regular_aspect_graph_node import (
    RegularAspectGraphNode,
)
from action_machine.model.graph_model.result_graph_node import ResultGraphNode
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector
from graph.constants import INTERNAL_EDGE_TYPES, OWNERSHIP_EDGE_TYPES
from graph.edge_relationship import Composition
from graph.node_graph_coordinator import NodeGraphCoordinator
from maxitor.viz2.visualizer_icons import svg_data_uri_for_vertex_icon

G6_CDN_URL = "https://unpkg.com/@antv/g6@5/dist/g6.min.js"

def _default_archive_logs_dir() -> Path:
    """Repository ``archive/logs`` (same rule as :func:`maxitor.viz1.visualizer._default_archive_logs_dir`)."""
    return Path(__file__).resolve().parents[3] / "archive" / "logs"


# Default write target for :func:`export_interchange_axes_graph_html`.
INTERCHANGE_AXES_GRAPH_HTML_PATH: Path = _default_archive_logs_dir() / "graph_node_2.html"

# Fixed fill per interchange vertex type (stable across graphs — not alphabetical).
# Palette: Okabe–Ito / Tol-inspired, maximally distinct hues; ``Application`` is black (root).
# Keys for Action / Domain / Entity / Params / Result / Role use ``NODE_TYPE`` from the corresponding ``*GraphNode`` classes.
VERTEX_TYPE_FILL_COLORS: dict[str, str] = {
    APPLICATION_VERTEX_TYPE: "#000000",
    ActionGraphNode.NODE_TYPE: "#E41A1C",
    DomainGraphNode.NODE_TYPE: "#377EB8",
    "dependency": "#4DAF4A",
    "connection": "#984EA3",
    RegularAspectGraphNode.NODE_TYPE: "#FF7F00",
    SUMMARY_ASPECT_VERTEX_TYPE: "#FF7F00",
    CHECKER_VERTEX_TYPE: "#A65628",
    COMPENSATOR_VERTEX_TYPE: "#F781BF",
    "error_handler": "#6A3D9A",
    EntityGraphNode.NODE_TYPE: "#1B9E77",
    "lifecycle": "#00798C",
    "lifecycle_state_initial": "#9575CD",
    "lifecycle_state_intermediate": "#6A51A3",
    "lifecycle_state_final": "#452E7A",
    "resource_manager": "#7570B3",
    "role_class": "#66A61E",
    RoleGraphNode.NODE_TYPE: "#66A61E",
    "role": "#E6AB02",
    "role_mode": "#B15928",
    "sensitive_field": "#FB9A99",
    "described_fields": "#A6CEE3",
    ParamsGraphNode.NODE_TYPE: "#CAB2D6",
    ResultGraphNode.NODE_TYPE: "#B2DF8A",
    "plugin": "#33A02C",
    "subscription": "#FDBF6F",
    "service": "#1F78B4",
    SERVICE_VERTEX_TYPE: "#4DAF4A",
}

DEFAULT_COLOR = "#95a5a6"

# Interchange vertex types with fixed fill + icon in this module; anything else
# uses one neutral fill and the dependency-style icon.
_KNOWN_VISUAL_VERTEX_TYPES: frozenset[str] = frozenset(VERTEX_TYPE_FILL_COLORS.keys())

GRAPH_NODE_VISUAL_PX = 24
GRAPH_NODE_LAYOUT_MARGIN_FRAC = 0.10

def _graph_vertex_key(node: dict[str, Any]) -> str:
    nm = str(node.get("id") or node.get("name", "") or "").strip()
    if nm:
        return nm
    nt = str(node.get("node_type", "") or "").strip()
    return nt or "unknown"


def _vertex_facet_label(node: dict[str, Any]) -> str:
    nt = str(node.get("node_type", "unknown"))
    if nt in (
        RegularAspectGraphNode.NODE_TYPE,
        SUMMARY_ASPECT_VERTEX_TYPE,
        CHECKER_VERTEX_TYPE,
        COMPENSATOR_VERTEX_TYPE,
    ):
        lab = str(node.get("label", "") or "").strip()
        if lab:
            return lab
    short = _element_short_name(node)
    return f"{nt}\n{short}"


def _element_short_name(node: dict[str, Any]) -> str:
    nt = str(node.get("node_type", "") or "").strip()
    if nt in (
        RegularAspectGraphNode.NODE_TYPE,
        SUMMARY_ASPECT_VERTEX_TYPE,
        CHECKER_VERTEX_TYPE,
        COMPENSATOR_VERTEX_TYPE,
    ):
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


def _fill_color_for_vertex_type(node_type: str) -> str:
    """
    Stable fill for one ``node_type`` string.

    Known types use :data:`VERTEX_TYPE_FILL_COLORS`. Any other label uses
    :data:`DEFAULT_COLOR` so such nodes share one neutral disk behind the
    dependency-style icon.
    """
    t = str(node_type).strip()
    if not t or t == "unknown":
        return DEFAULT_COLOR
    if t in VERTEX_TYPE_FILL_COLORS:
        return VERTEX_TYPE_FILL_COLORS[t]
    return DEFAULT_COLOR


def _color_map_for_vertex_types(node_types: Iterable[str]) -> dict[str, str]:
    """Map each distinct type string present in a graph to its fill color."""
    unique = sorted({str(t) for t in node_types if str(t)})
    return {t: _fill_color_for_vertex_type(t) for t in unique}


def _serialize_graph_value(value: Any) -> str:
    if isinstance(value, type):
        return f"{value.__module__}.{value.__qualname__}"
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, ensure_ascii=False, default=str)[:8000]
        except (TypeError, ValueError):
            return str(value)[:8000]
    s = str(value)
    return s[:8000] if len(s) > 8000 else s


# Role facets and ``Service`` stubs (see :data:`VERTEX_TYPE_FILL_COLORS`).
_ROLE_VERTEX_TYPES_FOR_APP_BUNDLE: frozenset[str] = frozenset(
    {"role", "role_class", RoleGraphNode.NODE_TYPE, "role_mode", SERVICE_VERTEX_TYPE},
)

# Hull colors for domain bubbles (one per domain vertex); distinct from typical node fills.
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


def _domain_sort_key_for_id(g6_nodes: list[dict[str, Any]], nid: str) -> tuple[str, str]:
    node = next(x for x in g6_nodes if str(x["id"]) == nid)
    d = node.get("data") or {}
    return (str(d.get("label", "")), str(d.get("graph_key", nid)))


def _propagate_node_domains(  # pylint: disable=too-many-branches
    g6_nodes: list[dict[str, Any]],
    g6_edges: list[dict[str, Any]],
) -> tuple[dict[str, str], list[str], defaultdict[str, set[str]]]:
    """
    Same domain membership as domain bubble-sets: ``BELONGS_TO`` + propagation
    along every interchange :data:`~graph.constants.OWNERSHIP_EDGE_TYPES` edge
    (host → child) and merge along :data:`~graph.constants.INTERNAL_EDGE_TYPES`
    (``CHECKS_ASPECT``, ``COMPENSATES_ASPECT``).
    """
    id_to_type: dict[str, str] = {}
    for n in g6_nodes:
        nid = str(n["id"])
        id_to_type[nid] = str((n.get("data") or {}).get("node_type", "unknown"))

    domain_ids = [nid for nid, t in id_to_type.items() if t == DomainGraphNode.NODE_TYPE]

    node_domains: defaultdict[str, set[str]] = defaultdict(set)

    for e in g6_edges:
        ed = e.get("data") or {}
        if str(ed.get("label", "") or "") != "BELONGS_TO":
            continue
        src, tgt = str(e["source"]), str(e["target"])
        if id_to_type.get(tgt) != DomainGraphNode.NODE_TYPE:
            continue
        if id_to_type.get(src) == APPLICATION_VERTEX_TYPE:
            continue
        node_domains[src].add(tgt)

    changed = True
    while changed:
        changed = False
        for e in g6_edges:
            ed = e.get("data") or {}
            label = str(ed.get("label", "") or "")
            src, tgt = str(e["source"]), str(e["target"])
            if label in OWNERSHIP_EDGE_TYPES:
                if not node_domains[src]:
                    continue
                before = len(node_domains[tgt])
                node_domains[tgt] |= node_domains[src]
                if len(node_domains[tgt]) > before:
                    changed = True
            elif label in INTERNAL_EDGE_TYPES:
                merged = node_domains[src] | node_domains[tgt]
                if not merged:
                    continue
                if merged != node_domains[src] or merged != node_domains[tgt]:
                    node_domains[src] = merged
                    node_domains[tgt] = merged
                    changed = True

    return id_to_type, domain_ids, node_domains


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
    sorted_domain_ids = sorted(domain_ids, key=lambda did: _domain_sort_key_for_id(g6_nodes, did))
    d_count = len(sorted_domain_ids)
    n_total = len(g6_nodes)
    ring_r = 240.0 + min(520.0, 18.0 * math.sqrt(max(n_total, 1)))

    out: dict[str, tuple[float, float]] = {}

    center_ids: list[str] = []
    for n in g6_nodes:
        nid = str(n["id"])
        if id_to_type.get(nid) == APPLICATION_VERTEX_TYPE:
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
            if id_to_type.get(nid) == APPLICATION_VERTEX_TYPE:
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


def _bubble_sets_plugins_for_domains(
    g6_nodes: list[dict[str, Any]],
    g6_edges: list[dict[str, Any]],
    *,
    propagation: tuple[dict[str, str], list[str], defaultdict[str, set[str]]] | None = None,
) -> list[dict[str, Any]]:
    """
    Build G6 ``bubble-sets`` plugins: one hull per ``domain`` vertex.

    Members: the domain vertex, every node with ``BELONGS_TO`` into that domain, and
    nodes reachable by propagating domain along interchange ownership edges
    (see :data:`~graph.constants.OWNERSHIP_EDGE_TYPES`) and internal
    checker/compensator–aspect links (see :data:`~graph.constants.INTERNAL_EDGE_TYPES`).

    The ``application`` vertex is never added to a domain bubble.
    """
    if propagation is None:
        propagation = _propagate_node_domains(g6_nodes, g6_edges)
    id_to_type, domain_ids, node_domains = propagation

    members_by_domain: dict[str, set[str]] = {}
    for d in domain_ids:
        mem = {d}
        for nid, doms in node_domains.items():
            if d in doms and id_to_type.get(nid) != APPLICATION_VERTEX_TYPE:
                mem.add(nid)
        members_by_domain[d] = mem

    palette = _BUBBLE_SETS_PALETTE

    plugins: list[dict[str, Any]] = []
    if domain_ids:
        for i, dom_id in enumerate(sorted(domain_ids, key=lambda did: _domain_sort_key_for_id(g6_nodes, did))):
            raw_members = members_by_domain.get(dom_id, {dom_id})
            members = sorted(
                [m for m in raw_members if id_to_type.get(m) != APPLICATION_VERTEX_TYPE],
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


def _node_obj_display(node_obj: object) -> str:
    if isinstance(node_obj, type):
        return f"{node_obj.__module__}.{node_obj.__qualname__}"
    return str(node_obj)


def interchange_model_dict_for_g6(node: BaseGraphNode[Any]) -> dict[str, Any]:
    """
    Vertex-weight ``dict`` for the G6 helpers in this module: ``id``, ``node_type``,
    ``label``, ``properties``, ``node_obj`` (string), matching the interchange facet shape.
    """
    merged: dict[str, Any] = {
        "id": node.node_id,
        "node_type": node.node_type,
        "label": node.label,
        "properties": dict(node.properties),
        "node_obj": _node_obj_display(node.node_obj),
    }
    text = str(merged.get("label", "") or "").strip()
    if not text:
        vid = str(merged["id"])
        merged["label"] = vid.rsplit(".", maxsplit=1)[-1] if "." in vid else vid
    return merged


def interchange_node_to_visual_dict(node: BaseGraphNode[Any]) -> dict[str, Any]:
    """Shallow interchange node mapping (optional callers / tests)."""
    return {
        "id": node.node_id,
        "node_type": node.node_type,
        "label": node.label,
        "properties": dict(node.properties),
        "node_obj": _node_obj_display(node.node_obj),
    }


def interchange_edge_to_visual_dict(edge: BaseGraphEdge) -> dict[str, Any]:
    """
    Edge payload for :func:`interchange_pygraph_for_g6` and G6 export.

    Includes ArchiMate-style ``source_attachment`` / ``target_attachment`` / ``line_style``
    (``StrEnum`` string values) plus ``relationship_name`` for tooltips or debugging.

    For ``COMPOSITION`` links to a ``RegularAspect`` vertex, attachment graphics are swapped so
    the diamond sits on the **aspect** end (UML aggregate/composite whole); graph topology
    stays ``Action → RegularAspect``.
    """
    er = edge.edge_relationship
    src_att = er.source_attachment.value
    tgt_att = er.target_attachment.value
    if isinstance(er, Composition) and edge.target_node_type == RegularAspectGraphNode.NODE_TYPE:
        src_att, tgt_att = tgt_att, src_att
    return {
        "edge_type": edge.edge_name,
        "is_dag": edge.is_dag,
        "relationship_name": er.archimate_name,
        "source_attachment": src_att,
        "target_attachment": tgt_att,
        "line_style": er.line_style.value,
    }


def interchange_pygraph_for_g6(coordinator: NodeGraphCoordinator) -> Any:
    """
    Clone the coordinator graph with dict vertex weights and ``BaseGraphEdge`` payloads on edges.

    Uses :meth:`~graph.node_graph_coordinator.NodeGraphCoordinator.get_all_nodes` and each node's
    ``edges`` (same topology as after :meth:`~graph.node_graph_coordinator.NodeGraphCoordinator.build`).
    ``rustworkx`` is imported only inside this function; the return value is a ``PyDiGraph`` for
    callers that still want dict-weighted graphs (e.g. tests).
    """
    import rustworkx as rx  # pylint: disable=import-outside-toplevel

    out = rx.PyDiGraph()
    nodes = coordinator.get_all_nodes()
    id_to_idx: dict[str, int] = {}
    for n in nodes:
        id_to_idx[n.node_id] = out.add_node(interchange_node_to_visual_dict(n))
    for n in nodes:
        s = id_to_idx[n.node_id]
        for edge in n.edges:
            t = id_to_idx[edge.target_node_id]
            out.add_edge(s, t, interchange_edge_to_visual_dict(edge))
    return out


def all_axis_graph_node_inspectors() -> list[BaseGraphNodeInspector[Any]]:
    """
    Built-in axis inspectors for **sample** / demo HTML.

    Includes ``Domain`` and ``Action`` so :class:`~action_machine.model.graph_model.action_graph_node.ActionGraphNode`
    ``domain`` / ``params`` / ``result`` edges resolve to existing vertices. This module does not
    inject missing nodes; :meth:`~graph.node_graph_coordinator.NodeGraphCoordinator.build` still
    validates every ``target_node_id``.
    """
    # pylint: disable=import-outside-toplevel
    from action_machine.auth.graph_model.role_graph_node_inspector import (
        RoleGraphNodeInspector,
    )
    from action_machine.domain.graph_model.domain_graph_node_inspector import (
        DomainGraphNodeInspector,
    )
    from action_machine.model.graph_model.action_graph_node_inspector import (
        ActionGraphNodeInspector,
    )
    from action_machine.model.graph_model.params_graph_node_inspector import (
        ParamsGraphNodeInspector,
    )
    from action_machine.model.graph_model.result_graph_node_inspector import (
        ResultGraphNodeInspector,
    )

    return [
        ParamsGraphNodeInspector(),
        ResultGraphNodeInspector(),
        RoleGraphNodeInspector(),
        DomainGraphNodeInspector(),
        ActionGraphNodeInspector(),
    ]


def generate_interchange_g6_html(  # pylint: disable=too-many-statements
    coordinator: NodeGraphCoordinator,
    output_path: str | Path,
    *,
    title: str = "ActionMachine Graph",
    width: str = "100%",
    height: str = "100vh",
    node_colors: dict[str, str] | None = None,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    nodes_tuple = coordinator.get_all_nodes()
    n_nodes = len(nodes_tuple)

    # Build nodes from ``BaseGraphNode`` payloads (interchange-native, ``get_all_nodes`` order).
    idx_to_node: dict[int, dict[str, Any]] = {}
    for idx, raw in enumerate(nodes_tuple):
        if not isinstance(raw, BaseGraphNode):
            msg = (
                f"generate_interchange_g6_html expects BaseGraphNode vertex weights; "
                f"got {type(raw).__name__!r} at coordinator node index {idx}"
            )
            raise TypeError(msg)
        idx_to_node[idx] = interchange_model_dict_for_g6(raw)

    colors = _color_map_for_vertex_types(
        str(idx_to_node[idx].get("node_type", "unknown"))
        for idx in range(n_nodes)
    )
    if node_colors:
        colors = {**colors, **node_colors}

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
        facet_label = _vertex_facet_label(node)
        graph_key = _graph_vertex_key(node)
        qualified = _element_qualified_name(node)
        # Serialized interchange node fields only; derived labels for the canvas live on ``data``.
        payload_panel: dict[str, str] = {}
        for k, v in node.items():
            payload_panel[str(k)] = _serialize_graph_value(v)
        fill = colors.get(node_type, DEFAULT_COLOR)
        g6_nodes.append({
            "id": str(idx),
            "data": {
                "label": short,
                "title": ntitle,
                "facet_label": facet_label,
                "graph_key": graph_key,
                "qualified": qualified,
                "node_type": node_type,
                "fill": fill,
                "iconSrc": svg_data_uri_for_vertex_icon(fill, node_type),
                "payload_panel": payload_panel,
            },
        })

    id_to_idx = {n.node_id: i for i, n in enumerate(nodes_tuple)}
    ei = 0
    for src_idx, interchange_node in enumerate(nodes_tuple):
        for edge in interchange_node.edges:
            tgt = id_to_idx[edge.target_node_id]
            if src_idx == tgt:
                continue
            elabel, is_dag = _edge_label_and_dag(edge)
            vis = interchange_edge_to_visual_dict(edge)
            g6_edges.append({
                "id": f"e-{src_idx}-{tgt}-{ei}",
                "source": str(src_idx),
                "target": str(tgt),
                "data": {
                    "label": elabel,
                    "isDag": is_dag,
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
            "iconSrc": svg_data_uri_for_vertex_icon(colors.get(nt, DEFAULT_COLOR), nt),
        }
        for nt in used_types
        if nt != "unknown"
    ]
    if not legend_items:
        legend_items = [
            {
                "type": "unknown",
                "color": DEFAULT_COLOR,
                "iconSrc": svg_data_uri_for_vertex_icon(DEFAULT_COLOR, "unknown"),
            },
        ]

    node_type_map = {
        str(idx): idx_to_node[idx].get("node_type", "unknown")
        for idx in range(n_nodes)
    }

    propagation = _propagate_node_domains(g6_nodes, g6_edges)
    seed_xy = _d3_seed_xy_for_nodes(g6_nodes, *propagation)
    for n in g6_nodes:
        sx, sy = seed_xy[str(n["id"])]
        n["style"] = {"x": sx, "y": sy}

    bubble_plugins = _bubble_sets_plugins_for_domains(g6_nodes, g6_edges, propagation=propagation)
    bubble_plugins_json = json.dumps(bubble_plugins, ensure_ascii=False)

    graph_data_json = json.dumps({"nodes": g6_nodes, "edges": g6_edges}, ensure_ascii=False)
    legend_json = json.dumps(legend_items, ensure_ascii=False)
    node_type_map_json = json.dumps(node_type_map, ensure_ascii=False)
    safe_title = html_escape(title)

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
    <meta http-equiv="Pragma" content="no-cache" />
    <meta http-equiv="Expires" content="0" />
    <title>{safe_title}</title>
    <script src="{G6_CDN_URL}"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ width: 100%; height: 100%; overflow: hidden; font-family: system-ui, sans-serif; }}
        #container {{
            position: relative;
            width: {width};
            height: {height};
            background-color: #f4f5f7;
            background-image: radial-gradient(rgba(160,168,180,0.42) 1px, transparent 1px);
            background-size: 20px 20px;
        }}
        #graph-hover-labels {{
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 20;
            overflow: visible;
        }}
        .graph-hover-label {{
            position: absolute;
            /* Same stack as G6 ``labelFontFamily`` on edges */
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #0f172a;
            font-size: 10px;
            font-weight: 500;
            max-width: 160px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            line-height: 1.2;
            transform: translate(-50%, 0);
        }}
        .color-legend {{
            position: fixed; top: 12px; left: 12px; z-index: 100000;
            background: rgba(255,255,255,0.88); backdrop-filter: blur(8px);
            border: 1px solid rgba(0,0,0,0.08); border-radius: 8px;
            padding: 8px 10px; min-width: 132px; max-width: 240px;
            max-height: 80vh; overflow-y: auto; font-size: 11px;
            color: #2c3e50; box-shadow: 0 2px 10px rgba(0,0,0,0.07);
            display: flex; flex-direction: column; gap: 5px;
        }}
        .color-legend .legend-title {{
            font-weight: 600; font-size: 10px; text-transform: uppercase;
            letter-spacing: 0.04em; color: #5c6370; margin-bottom: 2px;
        }}
        .color-legend .row {{ display: flex; align-items: center; gap: 8px; }}
        .color-legend .legend-icon {{
            width: 20px; height: 20px; border-radius: 50%; flex-shrink: 0;
            border: 1px solid rgba(0,0,0,0.12); object-fit: cover;
            display: block;
        }}
        .color-legend .swatch {{
            width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0;
            border: 1px solid rgba(0,0,0,0.12);
        }}
        .node-detail-shell {{
            position: fixed; top: 0; right: 0; height: 100vh; z-index: 100001;
            width: min(306px, calc(92vw * 0.85)); max-width: 306px;
            transform: translateX(100%);
            transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: none;
            box-shadow: -4px 0 28px rgba(0,0,0,0.07);
        }}
        .node-detail-shell.is-open {{
            transform: translateX(0);
            pointer-events: auto;
        }}
        .node-detail-panel {{
            height: 100%;
            background: #fff;
            border-left: 1px solid #eee;
            padding: 22px 22px 28px;
            overflow-y: auto;
            overflow-x: hidden;
            position: relative;
            font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        }}
        .node-detail-close {{
            position: absolute; top: 10px; right: 10px;
            width: 34px; height: 34px; border: none; border-radius: 8px;
            background: transparent; color: #757575;
            font-size: 22px; line-height: 1; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
        }}
        .node-detail-close:hover {{ background: #f5f5f5; color: #333; }}
        .properties-entity-name {{
            font-size: 16px; font-weight: 700; letter-spacing: 0.04em;
            text-transform: uppercase; color: #111; margin: 0 0 18px;
            padding-right: 40px; line-height: 1.2;
        }}
        .properties-entity-name.is-vertex-kind {{
            font-size: 14px; font-weight: 600; letter-spacing: 0.02em;
            text-transform: none; color: #222;
        }}
        .prop-block {{ margin-bottom: 18px; }}
        .prop-block-type {{ margin-bottom: 14px; }}
        .prop-label {{
            font-size: 11px; font-weight: 500; color: #757575; margin-bottom: 4px;
        }}
        .prop-label-type {{
            font-size: 10px; font-weight: 600; letter-spacing: 0.04em;
            text-transform: uppercase; color: #9e9e9e; margin-bottom: 3px;
        }}
        .prop-value {{
            font-size: 13px; color: #111; line-height: 1.5; word-break: break-word;
        }}
        .prop-type-value {{
            font-size: 11px; font-weight: 400; color: #333; line-height: 1.35;
        }}
        .prop-short-label-value {{
            font-size: 11px; color: #424242;
        }}
        .prop-value-mono {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 12px; word-break: break-all;
        }}
        .prop-value-row {{
            display: flex; align-items: flex-start; gap: 8px;
        }}
        .prop-value-row .prop-mono {{
            flex: 1; min-width: 0;
        }}
        .properties-section-title {{
            font-size: 10px; font-weight: 600; letter-spacing: 0.06em;
            text-transform: uppercase; color: #9e9e9e; margin: 4px 0 12px;
        }}
        .prop-value-multiline {{
            font-size: 11px; line-height: 1.45; white-space: pre-wrap;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            word-break: break-word;
        }}
        .copy-btn {{
            flex-shrink: 0; width: 30px; height: 30px; border: none;
            border-radius: 6px; background: #f0f0f0; color: #757575;
            cursor: pointer; font-size: 14px; line-height: 1;
        }}
        .copy-btn:hover {{ background: #e8e8e8; color: #424242; }}
        .type-row {{ display: flex; align-items: center; gap: 7px; }}
        .type-icon {{
            width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
            border: 1px solid rgba(0,0,0,0.12); object-fit: cover; display: block;
        }}
        .type-dot {{
            width: 7px; height: 7px; border-radius: 50%;
            border: 1px solid rgba(0,0,0,0.1); flex-shrink: 0;
        }}
        .zoom-toolbar {{
            position: fixed; bottom: 10px; left: 10px; z-index: 100000;
            display: flex; flex-direction: row; flex-wrap: wrap; align-items: center;
            gap: 3px;
            background: rgba(255,255,255,0.9); backdrop-filter: blur(6px);
            border: 1px solid rgba(0,0,0,0.08); border-radius: 6px;
            padding: 3px 5px; box-shadow: 0 1px 6px rgba(0,0,0,0.06);
        }}
        .zoom-toolbar button {{
            min-width: 0; width: 26px; height: 26px; padding: 0; font-size: 13px; line-height: 1;
            cursor: pointer; border: 1px solid #c5cad3; border-radius: 4px;
            background: #fff; color: #2c3e50; box-shadow: none;
            display: flex; align-items: center; justify-content: center;
        }}
        .zoom-toolbar button:hover {{ background: #eef0f3; }}
        .zoom-toolbar .zoom-label {{
            font-size: 10px; font-variant-numeric: tabular-nums;
            text-align: center; color: #5c6370; user-select: none;
            padding: 0 4px; min-width: 2.5em;
        }}
    </style>
</head>
<body>
    <div id="container"></div>
    <div id="color-legend" class="color-legend"></div>
    <aside id="node-detail-shell" class="node-detail-shell" aria-hidden="true">
      <div class="node-detail-panel">
        <button type="button" class="node-detail-close" id="node-detail-close" aria-label="Close properties">×</button>
        <div id="node-detail-body"></div>
      </div>
    </aside>
    <div class="zoom-toolbar" aria-label="Zoom">
        <button type="button" id="zoom-in" title="Zoom in">+</button>
        <button type="button" id="zoom-out" title="Zoom out">−</button>
        <button type="button" id="zoom-fit" title="Fit to window">⊡</button>
        <span class="zoom-label" id="zoom-pct">100%</span>
    </div>
    <script>
__G6_SCRIPT__
    </script>
</body>
</html>
"""

    g6_script = f"""
        const graphData = {graph_data_json};
        // Copy Python seed coordinates into node x/y so d3-force starts from domain wedges.
        for (const n of graphData.nodes) {{
          const s = n.style;
          if (s && typeof s.x === 'number' && typeof s.y === 'number') {{
            n.x = s.x;
            n.y = s.y;
          }}
        }}
        const legendItems = {legend_json};
        const nodeTypeMap = {node_type_map_json};
        const bubblePlugins = {bubble_plugins_json};
        const NODE_VISUAL_PX = {GRAPH_NODE_VISUAL_PX};

        const esc = (s) =>
          String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

        const escAttr = (s) =>
          String(s)
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');

        const COPY_SVG =
          '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';

        // Legend
        const legendEl = document.getElementById('color-legend');
        if (legendEl && legendItems.length) {{
          legendEl.innerHTML =
            '<div class="legend-title">Node types</div>' +
            legendItems.map((it) => {{
              const src = it.iconSrc != null ? String(it.iconSrc) : '';
              const lead = src
                ? '<img class="legend-icon" src="' + escAttr(src) + '" width="20" height="20" alt="" />'
                : '<span class="swatch" style="background:' + esc(it.color) + '"></span>';
              return '<div class="row">' + lead + '<span>' + esc(it.type) + '</span></div>';
            }}).join('');
        }}

        // Adjacency for hover highlight (no data mutation — use setElementState only).
        const adjIndex = {{}};
        const initAdj = (nid) => {{
          if (!adjIndex[nid]) adjIndex[nid] = {{ edges: new Set(), neighbors: new Set() }};
        }};
        for (const edge of graphData.edges) {{
          initAdj(edge.source);
          initAdj(edge.target);
          adjIndex[edge.source].edges.add(edge.id);
          adjIndex[edge.source].neighbors.add(edge.target);
          adjIndex[edge.target].edges.add(edge.id);
          adjIndex[edge.target].neighbors.add(edge.source);
        }}
        for (const node of graphData.nodes) initAdj(node.id);

        function edgeBaseStroke(d) {{
          return d.data?.isDag ? '#b91c1c' : '#95a5a6';
        }}
        const container = document.getElementById('container');
        const graph = new G6.Graph({{
          container: 'container',
          width: container.clientWidth,
          height: container.clientHeight,
          autoFit: 'view',
          animation: false,
          data: graphData,

          node: {{
            type: 'image',
            style: {{
              label: false,
              size: NODE_VISUAL_PX,
              src: (d) => d.data?.iconSrc || '',
              opacity: 1,
              filter: 'none',
              cursor: 'grab',
            }},
            state: {{
              dim: {{
                opacity: 0.22,
              }},
              hub: {{
                opacity: 1,
                stroke: '#DC2626',
                lineWidth: 3,
              }},
              nb: {{
                opacity: 1,
                stroke: '#F87171',
                lineWidth: 2,
              }},
            }},
          }},

          edge: {{
            type: 'line',
            style: {{
              stroke: (d) => edgeBaseStroke(d),
              lineWidth: 1.2,
              opacity: 1,
              endArrow: true,
              endArrowStroke: (d) => edgeBaseStroke(d),
              endArrowFill: (d) => edgeBaseStroke(d),
              label: false,
            }},
            state: {{
              active: {{}},
            }},
          }},

          layout: {{
            type: 'd3-force',
            iterations: 320,
            link: {{
              distance: (edge) => {{
                const st = nodeTypeMap[edge.source] || '';
                const tt = nodeTypeMap[edge.target] || '';
                return st === tt ? 72 : 200;
              }},
              strength: (edge) => {{
                const st = nodeTypeMap[edge.source] || '';
                const tt = nodeTypeMap[edge.target] || '';
                return st === tt ? 0.82 : 0.11;
              }},
            }},
            manyBody: {{ strength: -360, distanceMax: 1200 }},
            collide: {{ radius: NODE_VISUAL_PX * 0.5 + 7, strength: 0.95, iterations: 4 }},
            center: {{ strength: 0.012 }},
            alphaDecay: 0.008,
            alphaMin: 0.0008,
            velocityDecay: 0.36,
          }},

          behaviors: [
            {{ type: 'zoom-canvas', key: 'zoom-canvas', enable: true }},
            {{
              type: 'drag-element',
              key: 'drag-element',
              dropEffect: 'move',
            }},
            'drag-canvas',
          ],

          plugins: bubblePlugins,
        }});

        graph.render();

        const hoverOverlay = document.createElement('div');
        hoverOverlay.id = 'graph-hover-labels';
        hoverOverlay.setAttribute('aria-hidden', 'true');
        container.appendChild(hoverOverlay);

        function _xyFromPoint(p) {{
          if (p == null) return null;
          if (Array.isArray(p)) return [p[0], p[1]];
          if (typeof p.x === 'number' && typeof p.y === 'number') return [p.x, p.y];
          return null;
        }}

        function _canvasPointForLabel(id) {{
          try {{
            if (typeof graph.getElementPosition === 'function') {{
              const pos = graph.getElementPosition(id);
              const xy = _xyFromPoint(pos);
              if (xy) {{
                // Node center in canvas drawing space; move below the icon disk.
                return [xy[0], xy[1] + NODE_VISUAL_PX / 2 + 6];
              }}
            }}
          }} catch (_) {{}}
          try {{
            if (typeof graph.getElementRenderBounds === 'function') {{
              const b = graph.getElementRenderBounds(id);
              if (b && b.min != null && b.max != null) {{
                const min = b.min;
                const max = b.max;
                const m0 = Array.isArray(min) ? min[0] : min.x;
                const m1 = Array.isArray(min) ? min[1] : min.y;
                const M0 = Array.isArray(max) ? max[0] : max.x;
                const M1 = Array.isArray(max) ? max[1] : max.y;
                const cx = (m0 + M0) / 2;
                const cy = M1 + 4;
                return [cx, cy];
              }}
            }}
          }} catch (_) {{}}
          return null;
        }}

        let hoverLabelNodeId = null;
        let glowClearTimer = null;

        function applyNeighborGlow(nodeIdStr) {{
          const adj = adjIndex[nodeIdStr];
          if (!adj || typeof graph.setElementState !== 'function') return;
          const st = {{}};
          const hub = String(nodeIdStr);
          graphData.nodes.forEach((n) => {{
            const nid = String(n.id);
            if (nid === hub) st[nid] = ['hub'];
            else if (adj.neighbors.has(nid)) st[nid] = ['nb'];
            else st[nid] = ['dim'];
          }});
          graphData.edges.forEach((e) => {{
            st[e.id] = adj.edges.has(e.id) ? ['active'] : [];
          }});
          void graph.setElementState(st);
        }}

        function clearNeighborGlow() {{
          if (typeof graph.setElementState !== 'function') return;
          const st = {{}};
          graphData.nodes.forEach((n) => {{ st[n.id] = []; }});
          graphData.edges.forEach((e) => {{ st[e.id] = []; }});
          void graph.setElementState(st);
        }}

        function syncHoverLabels() {{
          hoverOverlay.innerHTML = '';
          if (hoverLabelNodeId == null) return;
          const adj = adjIndex[hoverLabelNodeId];
          const labelIds = new Set();
          labelIds.add(String(hoverLabelNodeId));
          if (adj) {{
            adj.neighbors.forEach((nid) => labelIds.add(String(nid)));
          }}
          const cr = container.getBoundingClientRect();
          graphData.nodes.forEach((n) => {{
            const id = String(n.id);
            if (!labelIds.has(id)) return;
            const d = n.data || {{}};
            const hoverText =
              d.label != null && String(d.label).trim() !== ''
                ? String(d.label)
                : d.title != null && String(d.title).trim() !== ''
                  ? String(d.title)
                  : d.graph_key != null && String(d.graph_key).trim() !== ''
                    ? String(d.graph_key)
                    : id;
            const canvasPt = _canvasPointForLabel(id);
            if (canvasPt == null) return;
            let left;
            let top;
            try {{
              if (typeof graph.getClientByCanvas === 'function') {{
                const client = graph.getClientByCanvas(canvasPt);
                const cxy = _xyFromPoint(client);
                if (cxy) {{
                  left = cxy[0] - cr.left;
                  top = cxy[1] - cr.top;
                }}
              }}
            }} catch (_) {{}}
            if (left == null || top == null) {{
              try {{
                if (typeof graph.getViewportByCanvas === 'function') {{
                  const vp = graph.getViewportByCanvas(canvasPt);
                  const vxy = _xyFromPoint(vp);
                  if (vxy) {{
                    left = vxy[0];
                    top = vxy[1];
                  }}
                }}
              }} catch (_) {{}}
            }}
            if (left == null || top == null) return;
            const div = document.createElement('div');
            div.className = 'graph-hover-label';
            div.textContent = hoverText;
            div.style.left = `${{left}}px`;
            div.style.top = `${{top}}px`;
            hoverOverlay.appendChild(div);
          }});
        }}

        const detailShell = document.getElementById('node-detail-shell');
        const detailBody = document.getElementById('node-detail-body');

        function closeNodeDetailPanel() {{
          if (detailShell) {{
            detailShell.classList.remove('is-open');
            detailShell.setAttribute('aria-hidden', 'true');
          }}
          if (detailBody) detailBody.innerHTML = '';
        }}

        function typeDisplayName(nt) {{
          if (!nt || String(nt).trim() === '') return '';
          const s = String(nt);
          return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ');
        }}

        function showNodeDetailPanel(nodeIdStr) {{
          if (!detailShell || !detailBody) return;
          const n = graphData.nodes.find((x) => String(x.id) === String(nodeIdStr));
          if (!n) {{
            closeNodeDetailPanel();
            return;
          }}
          const d = n.data || {{}};
          const shortName = d.label != null && String(d.label).trim() !== ''
            ? String(d.label)
            : String(nodeIdStr);
          const nt = d.node_type != null ? String(d.node_type) : '';
          const ntNorm = nt.trim().toLowerCase();
          const useKindHeading =
            ntNorm !== '' && ntNorm !== 'unknown';
          const title = d.title != null ? String(d.title) : '';
          const titleTrim = title.trim();
          const useTitleHeading = titleTrim !== '';
          const useHumanHeadingStyle = useTitleHeading || useKindHeading;
          const entityHeading = useTitleHeading
            ? titleTrim
            : useKindHeading
              ? typeDisplayName(nt)
              : shortName.toUpperCase();
          const payloadPanel = d.payload_panel && typeof d.payload_panel === 'object' && !Array.isArray(d.payload_panel) ? d.payload_panel : {{}};
          const payloadPanelKeys = Object.keys(payloadPanel).sort((a, b) => a.localeCompare(b));

          const copyKey = new Set(['graph_key', 'qualified', 'id', 'name']);

          let html = '';
          html +=
            '<h2 class="properties-entity-name' +
            (useHumanHeadingStyle ? ' is-vertex-kind' : '') +
            '">' +
            esc(entityHeading) +
            '</h2>';

          const fill = d.fill != null ? String(d.fill) : '';
          const iconSrc =
            d.iconSrc != null && String(d.iconSrc).trim() !== ''
              ? String(d.iconSrc)
              : '';
          const typePretty = nt ? typeDisplayName(nt) : '';
          const headingDuplicatesType =
            typePretty !== '' && entityHeading === typePretty;
          if (nt && !headingDuplicatesType) {{
            html += '<div class="prop-block prop-block-type">';
            html += '<div class="type-row">';
            if (iconSrc) {{
              html +=
                '<img class="type-icon" src="' +
                escAttr(iconSrc) +
                '" width="22" height="22" alt="" />';
            }} else {{
              html +=
                '<span class="type-dot" style="background:' +
                esc(fill || '#95a5a6') +
                '"></span>';
            }}
            html += '<span class="prop-type-value">' + esc(typePretty) + '</span>';
            html += '</div></div>';
          }}

          const propsRaw = payloadPanel['properties'];
          let propsObj = null;
          if (propsRaw != null && String(propsRaw).trim() !== '') {{
            try {{
              const parsed = JSON.parse(String(propsRaw));
              if (
                parsed !== null &&
                typeof parsed === 'object' &&
                !Array.isArray(parsed)
              ) {{
                propsObj = parsed;
              }}
            }} catch (_) {{}}
          }}

          const payloadSkipTop = new Set([
            'properties',
            'label',
            'node_obj',
            'node_type',
          ]);
          const payloadKeysNoProps = payloadPanelKeys.filter(
            (k) => !payloadSkipTop.has(k),
          );

          function appendPropBlock(k, rawVal) {{
            const v =
              rawVal == null
                ? ''
                : typeof rawVal === 'object'
                  ? JSON.stringify(rawVal, null, 0)
                  : String(rawVal);
            const multiline =
              v.length > 160 ||
              v.indexOf('\\n') >= 0 ||
              v.startsWith('{{') ||
              v.startsWith('[');
            html += '<div class="prop-block"><div class="prop-label">' + esc(k) + '</div>';
            if (copyKey.has(k) && v !== '') {{
              html += '<div class="prop-value prop-value-row">';
              html +=
                '<span class="prop-value-mono prop-mono' +
                (multiline ? ' prop-value-multiline' : '') +
                '">' +
                esc(v).replace(/\\n/g, '<br/>') +
                '</span>';
              html +=
                '<button type="button" class="copy-btn" data-copy="' +
                encodeURIComponent(v) +
                '" title="Copy">' +
                COPY_SVG +
                '</button>';
              html += '</div>';
            }} else {{
              html +=
                '<div class="' +
                (multiline ? 'prop-value prop-value-multiline' : 'prop-value') +
                '">' +
                esc(v).replace(/\\n/g, '<br/>') +
                '</div>';
            }}
            html += '</div>';
          }}

          for (const k of payloadKeysNoProps) {{
            appendPropBlock(k, payloadPanel[k]);
          }}

          if (propsObj != null && Object.keys(propsObj).length > 0) {{
            for (const pk of Object.keys(propsObj).sort((a, b) =>
              a.localeCompare(b),
            )) {{
              appendPropBlock(pk, propsObj[pk]);
            }}
          }} else if (
            propsObj === null &&
            payloadPanelKeys.includes('properties')
          ) {{
            appendPropBlock('properties', payloadPanel['properties']);
          }}

          detailBody.innerHTML = html;
          detailShell.classList.add('is-open');
          detailShell.setAttribute('aria-hidden', 'false');
        }}

        if (detailShell) {{
          detailShell.addEventListener('click', (e) => {{
            const btn = e.target.closest('.copy-btn');
            if (!btn || !detailShell.contains(btn)) return;
            const enc = btn.getAttribute('data-copy');
            if (enc == null) return;
            try {{
              const text = decodeURIComponent(enc);
              if (navigator.clipboard && navigator.clipboard.writeText)
                navigator.clipboard.writeText(text);
            }} catch (_) {{}}
          }});
        }}
        const detailCloseBtn = document.getElementById('node-detail-close');
        if (detailCloseBtn) {{
          detailCloseBtn.addEventListener('click', (e) => {{
            e.stopPropagation();
            closeNodeDetailPanel();
          }});
        }}
        closeNodeDetailPanel();

        graph.on('node:click', (evt) => {{
          let id = evt.target?.id;
          if (id == null && evt.itemId != null) id = evt.itemId;
          if (id == null && Array.isArray(evt.items) && evt.items[0]?.id != null) id = evt.items[0].id;
          if (id != null) showNodeDetailPanel(String(id));
        }});

        graph.on('node:pointerover', (evt) => {{
          if (glowClearTimer) {{
            clearTimeout(glowClearTimer);
            glowClearTimer = null;
          }}
          let id = evt.target?.id;
          if (id == null && evt.itemId != null) id = evt.itemId;
          if (id == null && Array.isArray(evt.items) && evt.items[0]?.id != null) id = evt.items[0].id;
          if (id == null) return;
          const sid = String(id);
          applyNeighborGlow(sid);
          hoverLabelNodeId = sid;
          requestAnimationFrame(() => syncHoverLabels());
        }});

        graph.on('node:pointerout', () => {{
          glowClearTimer = setTimeout(() => {{
            clearNeighborGlow();
            hoverLabelNodeId = null;
            syncHoverLabels();
            glowClearTimer = null;
          }}, 50);
        }});

        graph.on('canvas:click', () => {{
          if (glowClearTimer) {{
            clearTimeout(glowClearTimer);
            glowClearTimer = null;
          }}
          clearNeighborGlow();
          hoverLabelNodeId = null;
          syncHoverLabels();
          closeNodeDetailPanel();
        }});

        graph.on('canvas:mouseleave', () => {{
          if (glowClearTimer) {{
            clearTimeout(glowClearTimer);
            glowClearTimer = null;
          }}
          clearNeighborGlow();
          hoverLabelNodeId = null;
          syncHoverLabels();
        }});

        // Zoom toolbar
        const zoomPct = document.getElementById('zoom-pct');
        const syncZoom = () => {{
          if (!zoomPct) return;
          const z = graph.getZoom();
          zoomPct.textContent = Math.round(z * 100) + '%';
        }};
        graph.on('viewportchange', () => {{
          syncZoom();
          syncHoverLabels();
        }});

        const doZoom = async (factor) => {{
          const cur = graph.getZoom();
          const next = Math.min(4, Math.max(0.15, cur * factor));
          await graph.zoomTo(next, false);
          syncZoom();
        }};

        document.getElementById('zoom-in').addEventListener('click', () => doZoom(1.25));
        document.getElementById('zoom-out').addEventListener('click', () => doZoom(0.8));
        document.getElementById('zoom-fit').addEventListener('click', async () => {{
          await graph.fitView();
          syncZoom();
        }});

        graph.on('element:dragend', () => {{
          syncHoverLabels();
        }});

        window.addEventListener('resize', () => {{
          graph.resize(container.clientWidth, container.clientHeight);
          syncZoom();
          syncHoverLabels();
        }});
    """

    html = html_template.replace("__G6_SCRIPT__", g6_script.strip())
    path.write_text(html, encoding="utf-8")
    return path




def export_interchange_axes_graph_html(
    coordinator: NodeGraphCoordinator,
    *,
    title: str = "ActionMachine · interchange axes",
) -> Path:
    """Write G6 HTML for ``coordinator`` exactly as :func:`generate_interchange_g6_html` would.

    ``coordinator`` must already have a successful :meth:`~graph.node_graph_coordinator.NodeGraphCoordinator.build`.
    Output path is always :data:`INTERCHANGE_AXES_GRAPH_HTML_PATH`
    (``<repo>/archive/logs/graph_node_2.html``).
    """
    return generate_interchange_g6_html(coordinator, INTERCHANGE_AXES_GRAPH_HTML_PATH, title=title)

if __name__ == "__main__":
    import importlib

    from maxitor.samples.build import _MODULES

    for _mod in _MODULES:
        importlib.import_module(_mod)
    _coord = NodeGraphCoordinator()
    _coord.build(all_axis_graph_node_inspectors())
    written = export_interchange_axes_graph_html(_coord)
    print(f"Interchange axes graph HTML written to {written.resolve()}")
