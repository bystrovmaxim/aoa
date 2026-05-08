# src/maxitor/visualizer/graph_visualizer/visualizer.py
"""
HTML export for :class:`~graph.node_graph_coordinator.NodeGraphCoordinator` graphs.

Graph nodes carry :class:`~graph.base_graph_node.BaseGraphNode` and edges carry
:class:`~graph.base_graph_edge.BaseGraphEdge`. :func:`export_interchange_axes_graph_html`
writes a standalone AntV G6 HTML file for an **already built** coordinator to
:data:`HTML_PATH`
(``archive/logs/graph_node_2.html``; UTF-8, parent directories created as needed).
Markup and layout shell live in ``template.html`` beside this module;
Python injects graph JSON, seeds, and runtime script.
It does **not** call :meth:`~graph.node_graph_coordinator.NodeGraphCoordinator.build` or change inspectors.

:func:`generate_interchange_g6_html` takes the same built coordinator and serializes **only**
:meth:`~graph.node_graph_coordinator.NodeGraphCoordinator.get_all_nodes` plus each node's ``edges``
(no extra nodes, no ``rustworkx`` in this module's public API).

Layout, legend, domain bubbles, and the inspector panel keep the existing G6
behaviour while staying on the interchange-node pipeline only.

Domain hull membership propagation is implemented in
:mod:`~maxitor.visualizer.graph_visualizer.domain_propagation` so this module stays maintainable.

Edges use G6 ``line`` with default style; all edges are slate by default. Debug-collected
forbidden DAG-cycle edges use the reserved violation red (**not** reused by any stable node-type
fill). Nodes incident on those edges use the same red disk so endpoints read as hotspots. Action
nodes use indigo (:data:`NODE_TYPE_FILL_COLORS`), not violation red. On node hover, floating labels
use a flat rectangular panel; the **left stripe** uses each node’s ``data.fill`` (same hue as the
on-canvas disk). Canvas rendering uses G6 **circle** nodes (``fill`` + glyph ``iconSrc`` only). Hover
``hub`` / ``nb`` add a **black** ``stroke`` ring (same ``lineWidth`` as the default grey outline). Legend
and the details panel use full-chroma disk ``iconSrc``.
Edge ``data`` still carries relationship fields for tests.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Iterable
from functools import cache
from html import escape as html_escape
from pathlib import Path
from typing import Any

from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.graph_model.nodes.application_graph_node import ApplicationGraphNode
from action_machine.graph_model.nodes.checker_graph_node import CheckerGraphNode
from action_machine.graph_model.nodes.compensator_graph_node import CompensatorGraphNode
from action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
from action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode
from action_machine.graph_model.nodes.error_handler_graph_node import ErrorHandlerGraphNode
from action_machine.graph_model.nodes.field_graph_node import FieldGraphNode
from action_machine.graph_model.nodes.lifecycle_graph_node import LifeCycleGraphNode
from action_machine.graph_model.nodes.params_graph_node import ParamsGraphNode
from action_machine.graph_model.nodes.property_field_graph_node import PropertyFieldGraphNode
from action_machine.graph_model.nodes.regular_aspect_graph_node import (
    RegularAspectGraphNode,
)
from action_machine.graph_model.nodes.required_context_graph_node import (
    RequiredContextGraphNode,
)
from action_machine.graph_model.nodes.resource_graph_node import ResourceGraphNode
from action_machine.graph_model.nodes.result_graph_node import ResultGraphNode
from action_machine.graph_model.nodes.role_graph_node import RoleGraphNode
from action_machine.graph_model.nodes.sensitive_graph_node import SensitiveGraphNode
from action_machine.graph_model.nodes.state_graph_node import StateGraphNode
from action_machine.graph_model.nodes.summary_aspect_graph_node import SummaryAspectGraphNode
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.edge_relationship import Composition
from graph.node_graph_coordinator import NodeGraphCoordinator
from maxitor.visualizer.graph_visualizer.domain_propagation import (
    bubble_sets_plugins_for_domains as _bubble_sets_plugins_for_domains,
)
from maxitor.visualizer.graph_visualizer.domain_propagation import (
    domain_sort_key_for_id as _domain_sort_key_for_id,
)
from maxitor.visualizer.graph_visualizer.domain_propagation import (
    propagate_node_domains as _propagate_node_domains,
)
from maxitor.visualizer.graph_visualizer.visualizer_icons import (
    svg_data_uri_for_graph_node_glyph_only,
    svg_data_uri_for_graph_node_icon,
)
from maxitor.visualizer.shared.chrome import read_detail_panel_js, read_interchange_chrome_css

G6_CDN_URL = "https://unpkg.com/@antv/g6@5/dist/g6.min.js"

_INTERCHANGE_G6_SHELL_HTML = Path(__file__).resolve().parent / "template.html"


@cache
def _interchange_g6_shell_html_raw() -> str:
    return _INTERCHANGE_G6_SHELL_HTML.read_text(encoding="utf-8")

def _default_archive_logs_dir() -> Path:
    """Repository ``archive/logs`` output directory for generated graph artifacts."""
    return Path(__file__).resolve().parents[4] / "archive" / "logs"


# Default write target for :func:`export_interchange_axes_graph_html`.
HTML_PATH: Path = _default_archive_logs_dir() / "graph_node.html"

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
    # Field and PropertyField share one hue; glyphs in `visualizer_icons` distinguish them.
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
    Edge payload for :func:`interchange_pygraph_for_g6` and G6 export.

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


def interchange_pygraph_for_g6(coordinator: NodeGraphCoordinator) -> Any:
    """
    Clone the coordinator graph with dict graph-node payloads on nodes and ``BaseGraphEdge`` data on edges.

    Uses :meth:`~graph.node_graph_coordinator.NodeGraphCoordinator.get_all_nodes` and each node's
    ``edges`` (same topology as after :meth:`~graph.node_graph_coordinator.NodeGraphCoordinator.build`).
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
                f"generate_interchange_g6_html expects BaseGraphNode payloads on nodes; "
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
        # Serialized interchange node fields only; derived labels for the canvas live on ``data``.
        payload_panel: dict[str, str] = {}
        for k, v in node.items():
            payload_panel[str(k)] = _serialize_graph_value(v)
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
                "iconSrc": svg_data_uri_for_graph_node_icon(fill, node_type),
                "glyphIconSrc": svg_data_uri_for_graph_node_glyph_only(node_type),
                "payload_panel": payload_panel,
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
            "iconSrc": svg_data_uri_for_graph_node_icon(colors.get(nt, DEFAULT_COLOR), nt),
        }
        for nt in used_types
        if nt != "unknown"
    ]
    if not legend_items:
        legend_items = [
            {
                "type": "unknown",
                "color": DEFAULT_COLOR,
                "iconSrc": svg_data_uri_for_graph_node_icon(DEFAULT_COLOR, "unknown"),
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
        const DAG_CYCLE_VIOLATION_COLOR = "{DAG_CYCLE_VIOLATION_COLOR}";
        const NODE_BASE_RING_LINE_WIDTH = 0.75;

        const esc = (s) =>
          String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

        const escAttr = (s) =>
          String(s)
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');

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

        // Adjacency for hover: G6 states on hub / neighbors / edges; label stripe from node fill.
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
        const nodeById = new Map();
        for (const node of graphData.nodes) {{
          nodeById.set(String(node.id), node);
        }}

        function edgeBaseStroke(d) {{
          return d.data?.isForbiddenDagCycle ? DAG_CYCLE_VIOLATION_COLOR : '#95a5a6';
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
            type: 'circle',
            style: {{
              label: false,
              size: NODE_VISUAL_PX,
              fill: (d) => {{
                const v = d.data?.fill;
                if (v != null && String(v).trim() !== '') return String(v).trim();
                return '{DEFAULT_COLOR}';
              }},
              iconSrc: (d) =>
                d.data?.glyphIconSrc != null && String(d.data.glyphIconSrc).trim() !== ''
                  ? String(d.data.glyphIconSrc)
                  : d.data?.iconSrc || '',
              stroke: 'rgba(15, 23, 42, 0.14)',
              lineWidth: NODE_BASE_RING_LINE_WIDTH,
              opacity: 1,
              cursor: 'grab',
              halo: false,
              shadowBlur: 0,
            }},
            state: {{
              hub: {{
                opacity: 1,
                halo: false,
                stroke: '#000000',
                lineWidth: NODE_BASE_RING_LINE_WIDTH,
                shadowBlur: 0,
              }},
              nb: {{
                opacity: 1,
                halo: false,
                stroke: '#000000',
                lineWidth: NODE_BASE_RING_LINE_WIDTH,
                shadowBlur: 0,
              }},
            }},
          }},

          edge: {{
            type: 'line',
            style: {{
              stroke: (d) => edgeBaseStroke(d),
              lineWidth: (d) => (d.data?.isForbiddenDagCycle ? 2.4 : 1.2),
              opacity: 1,
              endArrow: true,
              endArrowStroke: (d) => edgeBaseStroke(d),
              endArrowFill: (d) => edgeBaseStroke(d),
              label: false,
            }},
            state: {{
              active: {{
                lineWidth: 2.35,
              }},
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

        function _containerOffsetFromCanvasPoint(canvasPt) {{
          const cr = container.getBoundingClientRect();
          try {{
            if (typeof graph.getClientByCanvas === 'function') {{
              const client = graph.getClientByCanvas(canvasPt);
              const cxy = _xyFromPoint(client);
              if (cxy) return [cxy[0] - cr.left, cxy[1] - cr.top];
            }}
          }} catch (_) {{}}
          try {{
            if (typeof graph.getViewportByCanvas === 'function') {{
              const vp = graph.getViewportByCanvas(canvasPt);
              const vxy = _xyFromPoint(vp);
              if (vxy) return [vxy[0], vxy[1]];
            }}
          }} catch (_) {{}}
          return null;
        }}

        let hoverLabelNodeId = null;
        let glowClearTimer = null;
        let hoverPointerOutPending = false;
        let viewportQuietTimer = null;
        const HOVER_CLEAR_DELAY_MS = 420;

        function clearViewportQuietTimer() {{
          if (viewportQuietTimer != null) {{
            clearTimeout(viewportQuietTimer);
            viewportQuietTimer = null;
          }}
        }}

        function armHoverClearDeferred() {{
          if (glowClearTimer != null) {{
            clearTimeout(glowClearTimer);
            glowClearTimer = null;
          }}
          glowClearTimer = setTimeout(() => {{
            clearNeighborGlow();
            hoverLabelNodeId = null;
            hoverPointerOutPending = false;
            scheduleHoverOverlaySync();
            glowClearTimer = null;
            clearViewportQuietTimer();
          }}, HOVER_CLEAR_DELAY_MS);
        }}
        let hoverGlowSnap = null;

        function applyNeighborGlow(nodeIdStr) {{
          const adj = adjIndex[nodeIdStr];
          if (!adj || typeof graph.setElementState !== 'function') return;
          const hub = String(nodeIdStr);
          const nbNorm = new Set();
          adj.neighbors.forEach((x) => nbNorm.add(String(x)));
          const eActive = adj.edges;
          const st = {{}};
          const prev = hoverGlowSnap;

          if (prev == null) {{
            st[hub] = ['hub'];
            nbNorm.forEach((s) => {{
              if (s !== hub) st[s] = ['nb'];
            }});
            eActive.forEach((eid) => {{
              st[eid] = ['active'];
            }});
          }} else {{
            const candNodes = new Set([prev.hubId, hub]);
            prev.neighborIds.forEach((s) => candNodes.add(String(s)));
            nbNorm.forEach((s) => candNodes.add(s));
            for (const nid of candNodes) {{
              const s = String(nid);
              if (s === hub) st[s] = ['hub'];
              else if (nbNorm.has(s)) st[s] = ['nb'];
              else st[s] = [];
            }}
            const candEdges = new Set();
            prev.edgeIds.forEach((eid) => candEdges.add(eid));
            eActive.forEach((eid) => candEdges.add(eid));
            for (const eid of candEdges) {{
              st[eid] = eActive.has(eid) ? ['active'] : [];
            }}
          }}

          void graph.setElementState(st);
          hoverGlowSnap = {{
            hubId: hub,
            neighborIds: new Set(nbNorm),
            edgeIds: new Set(eActive),
          }};
        }}

        function clearNeighborGlow() {{
          if (typeof graph.setElementState !== 'function') return;
          const prev = hoverGlowSnap;
          if (prev == null) return;
          const st = {{}};
          st[prev.hubId] = [];
          prev.neighborIds.forEach((nid) => {{
            st[String(nid)] = [];
          }});
          prev.edgeIds.forEach((eid) => {{
            st[eid] = [];
          }});
          void graph.setElementState(st);
          hoverGlowSnap = null;
        }}

        function syncHoverLabels() {{
          hoverOverlay.innerHTML = '';
          if (hoverLabelNodeId == null) return;
          const adj = adjIndex[hoverLabelNodeId];
          const labelIds = new Set([String(hoverLabelNodeId)]);
          if (adj) {{
            adj.neighbors.forEach((nid) => labelIds.add(String(nid)));
          }}
          for (const id of labelIds) {{
            const n = nodeById.get(id);
            if (!n) continue;
            const d = n.data || {{}};
            const hoverText =
              d.label != null && String(d.label).trim() !== ''
                ? String(d.label)
                : d.title != null && String(d.title).trim() !== ''
                  ? String(d.title)
                  : d.graph_key != null && String(d.graph_key).trim() !== ''
                    ? String(d.graph_key)
                    : id;
            const fill =
              d.fill != null && String(d.fill).trim() !== '' ? String(d.fill).trim() : '';
            const stripe = fill !== '' ? fill : '{DEFAULT_COLOR}';
            const canvasPt = _canvasPointForLabel(id);
            if (canvasPt == null) continue;
            const off = _containerOffsetFromCanvasPoint(canvasPt);
            if (off == null) continue;
            const div = document.createElement('div');
            div.className = 'graph-hover-label';
            div.textContent = hoverText;
            div.style.borderLeftColor = stripe;
            div.style.left = `${{off[0]}}px`;
            div.style.top = `${{off[1]}}px`;
            hoverOverlay.appendChild(div);
          }}
        }}

        let hoverOverlaySyncRaf = null;
        function scheduleHoverOverlaySync() {{
          if (hoverOverlaySyncRaf != null) return;
          hoverOverlaySyncRaf = requestAnimationFrame(() => {{
            hoverOverlaySyncRaf = null;
            syncHoverLabels();
          }});
        }}

        const detailPanel = window.InterchangeDetailPanel;
        detailPanel.replaceData('graph-node', graphData.nodes, {{ template: 'graph-node' }});

        graph.on('node:click', (evt) => {{
          let id = evt.target?.id;
          if (id == null && evt.itemId != null) id = evt.itemId;
          if (id == null && Array.isArray(evt.items) && evt.items[0]?.id != null) id = evt.items[0].id;
          if (id != null) detailPanel.open(String(id));
        }});

        graph.on('node:pointerover', (evt) => {{
          hoverPointerOutPending = false;
          clearViewportQuietTimer();
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
          scheduleHoverOverlaySync();
        }});

        graph.on('node:pointerout', () => {{
          hoverPointerOutPending = true;
          armHoverClearDeferred();
        }});

        graph.on('canvas:click', () => {{
          hoverPointerOutPending = false;
          clearViewportQuietTimer();
          if (glowClearTimer) {{
            clearTimeout(glowClearTimer);
            glowClearTimer = null;
          }}
          clearNeighborGlow();
          hoverLabelNodeId = null;
          scheduleHoverOverlaySync();
          detailPanel.close();
        }});

        graph.on('canvas:mouseleave', () => {{
          hoverPointerOutPending = false;
          clearViewportQuietTimer();
          if (glowClearTimer) {{
            clearTimeout(glowClearTimer);
            glowClearTimer = null;
          }}
          clearNeighborGlow();
          hoverLabelNodeId = null;
          scheduleHoverOverlaySync();
        }});

        // Zoom toolbar
        const zoomPct = document.getElementById('zoom-pct');
        const syncZoom = () => {{
          if (!zoomPct) return;
          const z = graph.getZoom();
          zoomPct.textContent = Math.round(z * 100) + '%';
        }};
        let zoomSyncRaf = null;
        const scheduleZoomSync = () => {{
          if (zoomSyncRaf != null) return;
          zoomSyncRaf = requestAnimationFrame(() => {{
            zoomSyncRaf = null;
            syncZoom();
          }});
        }};
        graph.on('viewportchange', () => {{
          scheduleZoomSync();
          scheduleHoverOverlaySync();
          if (hoverPointerOutPending && glowClearTimer != null) {{
            clearTimeout(glowClearTimer);
            glowClearTimer = null;
          }}
          clearViewportQuietTimer();
          viewportQuietTimer = setTimeout(() => {{
            viewportQuietTimer = null;
            if (hoverPointerOutPending && hoverGlowSnap !== null)
              armHoverClearDeferred();
          }}, 170);
        }});

        container.addEventListener(
          'wheel',
          () => {{
            scheduleZoomSync();
            scheduleHoverOverlaySync();
            if (hoverPointerOutPending && glowClearTimer != null) {{
              clearTimeout(glowClearTimer);
              glowClearTimer = null;
            }}
            clearViewportQuietTimer();
            viewportQuietTimer = setTimeout(() => {{
              viewportQuietTimer = null;
              if (hoverPointerOutPending && hoverGlowSnap !== null)
                armHoverClearDeferred();
            }}, 170);
          }},
          {{ passive: true }},
        );

        const doZoom = async (factor) => {{
          const cur = graph.getZoom();
          const next = Math.min(4, Math.max(0.15, cur * factor));
          await graph.zoomTo(next, false);
          scheduleZoomSync();
        }};

        document.getElementById('btn-zoom-in').addEventListener('click', () => doZoom(1.25));
        document.getElementById('btn-zoom-out').addEventListener('click', () => doZoom(0.8));
        document.getElementById('btn-zoom-fit').addEventListener('click', async () => {{
          await graph.fitView();
          scheduleZoomSync();
        }});

        graph.on('element:dragend', () => {{
          scheduleHoverOverlaySync();
        }});

        window.addEventListener('resize', () => {{
          graph.resize(container.clientWidth, container.clientHeight);
          scheduleZoomSync();
          scheduleHoverOverlaySync();
        }});
        syncZoom();
    """

    html_document = (
        _interchange_g6_shell_html_raw()
        .replace("@@INTERCHANGE_CHROME_CSS@@", read_interchange_chrome_css())
        .replace("@@DETAIL_PANEL_SCRIPT@@", read_detail_panel_js())
        .replace("@@HTML_ESCAPED_TITLE@@", safe_title)
        .replace("@@G6_CDN_URL@@", G6_CDN_URL)
        .replace("@@CONTAINER_WIDTH@@", width)
        .replace("@@CONTAINER_HEIGHT@@", height)
        .replace("@@INLINE_G6_SCRIPT@@", g6_script.strip())
    )
    path.write_text(html_document, encoding="utf-8")
    return path




def export_interchange_axes_graph_html(
    coordinator: NodeGraphCoordinator,
    *,
    title: str = "ActionMachine · interchange axes",
) -> Path:
    """Write G6 HTML for ``coordinator`` exactly as :func:`generate_interchange_g6_html` would.

    ``coordinator`` must already have a successful :meth:`~graph.node_graph_coordinator.NodeGraphCoordinator.build`.
    Output path is always :data:`HTML_PATH`
    (``<repo>/archive/logs/graph_node_2.html``).
    """
    return generate_interchange_g6_html(coordinator, HTML_PATH, title=title)

def write_demo_interchange_axes_graph_html() -> Path:
    """Build sample graph coordinator and emit G6 HTML to :data:`HTML_PATH`."""
    from maxitor.samples.interchange_demo_coordinator import (  # pylint: disable=import-outside-toplevel
        build_registered_interchange_coordinator,
        import_sample_registration_modules,
    )

    import_sample_registration_modules()
    coord = build_registered_interchange_coordinator()
    return export_interchange_axes_graph_html(coord)


if __name__ == "__main__":
    written = write_demo_interchange_axes_graph_html()
    print(f"Interchange axes graph HTML written to {written.resolve()}")
