# src/maxitor/visualizer.py
"""
HTML visualization for coordinator PyDiGraph graphs.

Generates a standalone HTML file using AntV G6 v5.
Layout: d3-force with custom distance/strength per node type.
Node fill colors: **fixed** per interchange ``vertex_type`` / ``node_type`` string
(see :data:`VERTEX_TYPE_FILL_COLORS`); ``application`` is always black. Each node is
drawn as an SVG **data URL** (white Lucide icons on the colored disk; see
:mod:`maxitor.visualizer_icons`). Unknown
types use a stable hash into a high-contrast fallback palette so new types never
shift existing colors. Optional ``node_colors`` in :func:`generate_g6_html`
still override per-type fills.

Domain hulls (``bubble-sets``) are derived only from graph topology: every
``domain`` vertex, ``BELONGS_TO`` edges, and facet ownership propagation — no
hardcoded domain list.

Interaction: drag-canvas (pan empty canvas) + drag-element (move nodes).
``drag-element-force`` is intentionally avoided: it re-runs d3-force on every drag
frame, so the *entire* graph appears to move with the pointer.
"""

from __future__ import annotations

import json
import zlib
from collections import defaultdict
from datetime import UTC, datetime
from html import escape as html_escape
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import rustworkx as rx

from maxitor.graph_export import (
    coordinator_pygraph_for_visual_export,
    normalize_coordinator_node_payload_for_visualization,
)
from maxitor.visualizer_icons import svg_data_uri_for_vertex_icon

_HIGHLIGHT_DISK_FILL = "#e74c3c"

G6_CDN_URL = "https://unpkg.com/@antv/g6@5/dist/g6.min.js"
DEFAULT_APP_GRAPH_HTML = "app_graph.html"

# Fixed fill per interchange vertex type (stable across graphs — not alphabetical).
# Palette: Okabe–Ito / Tol-inspired, maximally distinct hues; ``application`` is black (root).
VERTEX_TYPE_FILL_COLORS: dict[str, str] = {
    "application": "#000000",
    "action": "#E41A1C",
    "domain": "#377EB8",
    "dependency": "#4DAF4A",
    "connection": "#984EA3",
    "aspect": "#FF7F00",
    "checker": "#A65628",
    "compensator": "#F781BF",
    "error_handler": "#6A3D9A",
    "entity": "#1B9E77",
    "resource_manager": "#7570B3",
    "role_class": "#66A61E",
    "role": "#E6AB02",
    "role_mode": "#B15928",
    "sensitive_field": "#FB9A99",
    "described_fields": "#A6CEE3",
    "params_schema": "#CAB2D6",
    "result_schema": "#B2DF8A",
    "plugin": "#33A02C",
    "subscription": "#FDBF6F",
    "service": "#1F78B4",
}

# Types not listed above: deterministic pick from distinct hues (never black).
_UNKNOWN_VERTEX_TYPE_COLORS: tuple[str, ...] = (
    "#DD8452",
    "#55A868",
    "#C44E52",
    "#8172B3",
    "#937860",
    "#DA8BC3",
    "#8C564B",
    "#E377C2",
    "#7F7F7F",
    "#BCBD22",
    "#17BECF",
    "#D62728",
    "#9467BD",
    "#2CA02C",
    "#FF9896",
    "#C5B0D5",
    "#C49C94",
    "#F7B6D2",
    "#DBDB8D",
    "#9EDAE5",
)

DEFAULT_COLOR = "#95a5a6"

GRAPH_NODE_VISUAL_PX = 24
GRAPH_NODE_LAYOUT_MARGIN_FRAC = 0.10

_SKIP_META_KEYS = frozenset(
    {
        "node_type", "name", "label", "graph_key", "facet_label",
        "vertex_type", "id", "display_name", "stereotype", "properties",
    },
)


def _graph_vertex_key(node: dict[str, Any]) -> str:
    nm = str(node.get("name", "") or "").strip()
    if nm:
        return nm
    nt = str(node.get("node_type", "") or "").strip()
    return nt or "unknown"


def _vertex_facet_label(node: dict[str, Any]) -> str:
    nt = str(node.get("node_type", "unknown"))
    short = _element_short_name(node)
    return f"{nt}\n{short}"


def _element_short_name(node: dict[str, Any]) -> str:
    cr = node.get("class_ref")
    if isinstance(cr, type):
        return cr.__name__
    raw = str(node.get("name", "") or node.get("label", "") or "").strip()
    if not raw:
        return "?"
    if "." in raw:
        return raw.rsplit(".", 1)[-1]
    return raw


def _node_title_for_visual(node: dict[str, Any]) -> str:
    dn = str(node.get("display_name", "") or "").strip()
    if dn:
        return dn
    return _element_short_name(node)


def _element_qualified_name(node: dict[str, Any]) -> str:
    cr = node.get("class_ref")
    if isinstance(cr, type):
        return f"{cr.__module__}.{cr.__qualname__}"
    return str(node.get("name", "") or node.get("label", "") or "?")


def _fill_color_for_vertex_type(vertex_type: str) -> str:
    """
    Stable fill for one ``vertex_type`` / ``node_type`` string.

    Known types use :data:`VERTEX_TYPE_FILL_COLORS`. Others use
    :data:`_UNKNOWN_VERTEX_TYPE_COLORS` indexed by ``zlib.adler32`` of the name
    (stable across processes, unlike ``hash()``).
    """
    t = str(vertex_type).strip()
    if not t or t == "unknown":
        return DEFAULT_COLOR
    if t in VERTEX_TYPE_FILL_COLORS:
        return VERTEX_TYPE_FILL_COLORS[t]
    idx = zlib.adler32(t.encode("utf-8")) % len(_UNKNOWN_VERTEX_TYPE_COLORS)
    return _UNKNOWN_VERTEX_TYPE_COLORS[idx]


def _color_map_for_vertex_types(node_types: Iterable[str]) -> dict[str, str]:
    """Map each distinct type string present in a graph to its fill color."""
    unique = sorted({str(t) for t in node_types if str(t)})
    return {t: _fill_color_for_vertex_type(t) for t in unique}


def _serialize_graph_value(value: Any) -> str:
    if isinstance(value, type):
        return f"{value.__module__}.{value.__qualname__}"
    if value is None:
        return ""
    return str(value)[:800]


def _default_archive_logs_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "archive" / "logs"


# Interchange edge labels: host (e.g. action) → facet child; domain flows to child.
_OWNERSHIP_HOST_TO_CHILD: frozenset[str] = frozenset(
    {
        "HAS_ASPECT",
        "HAS_SENSITIVE_FIELD",
        "HAS_ERROR_HANDLER",
        "HAS_COMPENSATOR",
        "HAS_PARAMS",
        "HAS_RESULT",
    },
)

# Single bubble-set: application root + all role facet vertices.
_ROLE_VERTEX_TYPES_FOR_APP_BUNDLE: frozenset[str] = frozenset(
    {"role", "role_class", "role_mode"},
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


def _application_roles_bubble_plugin(
    id_to_type: dict[str, str],
    *,
    color_index: int,
) -> dict[str, Any] | None:
    """One ``bubble-sets`` hull grouping ``application`` and role-related nodes."""
    app_ids = [nid for nid, t in id_to_type.items() if t == "application"]
    role_ids = [
        nid
        for nid, t in id_to_type.items()
        if t in _ROLE_VERTEX_TYPES_FOR_APP_BUNDLE
    ]
    members = sorted(frozenset(app_ids) | frozenset(role_ids))
    if not members:
        return None
    cyc = _BUBBLE_SETS_PALETTE
    base = cyc[color_index % len(cyc)]
    return {
        "key": "bubble-application-roles",
        "type": "bubble-sets",
        "members": members,
        "labelText": "Application & roles",
        "fill": base,
        "stroke": base,
        "labelFill": "#fff",
        "labelPadding": 2,
        "labelBackgroundFill": base,
        "labelBackgroundRadius": 5,
    }


def _bubble_sets_plugins_for_domains(
    g6_nodes: list[dict[str, Any]],
    g6_edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build G6 ``bubble-sets`` plugins: one hull per ``domain`` vertex.

    Members: the domain vertex, every node with ``BELONGS_TO`` into that domain, and
    nodes reachable by propagating domain along action-owned facets (aspects,
    sensitive fields, error handlers, compensators, param/result schemas) and
    ``CHECKS_ASPECT`` (checker ↔ aspect), so facets share the parent action's domain.

    The ``application`` vertex is never added to a domain bubble.

    Additionally, one hull bundles ``application`` with all ``role`` / ``role_class`` /
    ``role_mode`` vertices.
    """
    id_to_type: dict[str, str] = {}
    for n in g6_nodes:
        nid = str(n["id"])
        id_to_type[nid] = str((n.get("data") or {}).get("node_type", "unknown"))

    domain_ids = [nid for nid, t in id_to_type.items() if t == "domain"]

    # node_id -> domain vertex ids (interchange ids of domain nodes)
    node_domains: defaultdict[str, set[str]] = defaultdict(set)

    for e in g6_edges:
        ed = e.get("data") or {}
        if str(ed.get("label", "") or "") != "BELONGS_TO":
            continue
        src, tgt = str(e["source"]), str(e["target"])
        if id_to_type.get(tgt) != "domain":
            continue
        if id_to_type.get(src) == "application":
            continue
        node_domains[src].add(tgt)

    changed = True
    while changed:
        changed = False
        for e in g6_edges:
            ed = e.get("data") or {}
            label = str(ed.get("label", "") or "")
            src, tgt = str(e["source"]), str(e["target"])
            if label in _OWNERSHIP_HOST_TO_CHILD:
                if not node_domains[src]:
                    continue
                before = len(node_domains[tgt])
                node_domains[tgt] |= node_domains[src]
                if len(node_domains[tgt]) > before:
                    changed = True
            elif label == "CHECKS_ASPECT":
                merged = node_domains[src] | node_domains[tgt]
                if not merged:
                    continue
                if merged != node_domains[src] or merged != node_domains[tgt]:
                    node_domains[src] = merged
                    node_domains[tgt] = merged
                    changed = True

    members_by_domain: dict[str, set[str]] = {}
    for d in domain_ids:
        mem = {d}
        for nid, doms in node_domains.items():
            if d in doms and id_to_type.get(nid) != "application":
                mem.add(nid)
        members_by_domain[d] = mem

    palette = _BUBBLE_SETS_PALETTE

    def _domain_sort_key(nid: str) -> tuple[str, str]:
        node = next(x for x in g6_nodes if str(x["id"]) == nid)
        d = node.get("data") or {}
        return (str(d.get("label", "")), str(d.get("graph_key", nid)))

    plugins: list[dict[str, Any]] = []
    if domain_ids:
        for i, dom_id in enumerate(sorted(domain_ids, key=_domain_sort_key)):
            raw_members = members_by_domain.get(dom_id, {dom_id})
            members = sorted(
                [m for m in raw_members if id_to_type.get(m) != "application"],
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

    ar = _application_roles_bubble_plugin(id_to_type, color_index=len(plugins))
    if ar:
        plugins.append(ar)

    return plugins


def generate_g6_html(
    graph: rx.PyDiGraph,
    output_path: str | Path,
    *,
    title: str = "ActionMachine Graph",
    width: str = "100%",
    height: str = "100vh",
    node_colors: dict[str, str] | None = None,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Build nodes
    idx_to_node: dict[int, dict[str, Any]] = {}
    for idx in graph.node_indices():
        raw = graph[idx]
        raw_node = dict(raw) if isinstance(raw, dict) else {}
        idx_to_node[idx] = normalize_coordinator_node_payload_for_visualization(raw_node)

    colors = _color_map_for_vertex_types(
        str(idx_to_node[idx].get("node_type", "unknown"))
        for idx in graph.node_indices()
    )
    if node_colors:
        colors = {**colors, **node_colors}

    def _edge_label_and_dag(edge_data: Any) -> tuple[str, bool]:
        if isinstance(edge_data, dict):
            return str(edge_data.get("edge_type", "")), bool(edge_data.get("is_dag"))
        return str(edge_data), False

    g6_nodes = []
    for idx in graph.node_indices():
        node = idx_to_node[idx]
        node_type = str(node.get("node_type", "unknown"))
        short = _element_short_name(node)
        ntitle = _node_title_for_visual(node)
        facet_label = _vertex_facet_label(node)
        graph_key = _graph_vertex_key(node)
        qualified = _element_qualified_name(node)
        meta = {
            k: _serialize_graph_value(v)
            for k, v in node.items()
            if k not in _SKIP_META_KEYS and k != "class_ref"
        }
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
                "iconSrcHighlight": svg_data_uri_for_vertex_icon(_HIGHLIGHT_DISK_FILL, node_type),
                "meta": meta,
            },
        })

    g6_edges = []
    for ei, (src, tgt, edge_data) in enumerate(graph.weighted_edge_list()):
        if src == tgt:
            continue
        elabel, is_dag = _edge_label_and_dag(edge_data)
        g6_edges.append({
            "id": f"e-{src}-{tgt}-{ei}",
            "source": str(src),
            "target": str(tgt),
            "data": {"label": elabel, "isDag": is_dag},
        })

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
        for idx in graph.node_indices()
    }

    bubble_plugins = _bubble_sets_plugins_for_domains(g6_nodes, g6_edges)
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
            width: {width};
            height: {height};
            background-color: #f4f5f7;
            background-image: radial-gradient(rgba(160,168,180,0.42) 1px, transparent 1px);
            background-size: 20px 20px;
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
        .properties-head {{
            display: flex; align-items: flex-start; gap: 12px; margin-bottom: 2px;
        }}
        .properties-type-icon {{
            width: 44px; height: 44px; border-radius: 50%; flex-shrink: 0;
            border: 1px solid rgba(0,0,0,0.12); object-fit: cover; display: block;
        }}
        .properties-head-text {{
            flex: 1; min-width: 0;
        }}
        .properties-head .properties-entity-name {{ margin-top: 0; }}
        .type-icon, .fill-type-icon {{
            width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
            border: 1px solid rgba(0,0,0,0.12); object-fit: cover; display: block;
        }}
        .fill-type-icon {{ width: 20px; height: 20px; }}
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
        .properties-kicker {{
            font-size: 9px; font-weight: 700; letter-spacing: 0.14em;
            color: #9e9e9e; text-transform: uppercase; margin: 0 0 8px;
        }}
        .properties-rule {{
            border: 0; height: 1px; background: #eee; margin: 0 0 16px;
        }}
        .properties-entity-name {{
            font-size: 16px; font-weight: 700; letter-spacing: 0.04em;
            text-transform: uppercase; color: #111; margin: 0 0 4px;
            padding-right: 40px; line-height: 1.2;
        }}
        .properties-entity-name.is-vertex-kind {{
            font-size: 14px; font-weight: 600; letter-spacing: 0.02em;
            text-transform: none; color: #222;
        }}
        .properties-sub {{
            font-size: 10px; font-weight: 400; letter-spacing: 0.02em;
            color: #bdbdbd; margin: 0 0 20px; line-height: 1.3;
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
        .copy-btn {{
            flex-shrink: 0; width: 30px; height: 30px; border: none;
            border-radius: 6px; background: #f0f0f0; color: #757575;
            cursor: pointer; font-size: 14px; line-height: 1;
        }}
        .copy-btn:hover {{ background: #e8e8e8; color: #424242; }}
        .type-row {{ display: flex; align-items: center; gap: 7px; }}
        .type-dot {{
            width: 7px; height: 7px; border-radius: 50%;
            border: 1px solid rgba(0,0,0,0.1); flex-shrink: 0;
        }}
        .fill-row {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
        .fill-swatch {{
            width: 16px; height: 16px; border-radius: 50%;
            border: 1px solid rgba(0,0,0,0.12); flex-shrink: 0;
        }}
        .fill-hex-muted {{
            margin-left: auto; font-size: 11px; color: #9e9e9e;
            font-family: ui-monospace, monospace;
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

        // Adjacency index for highlighting
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
              size: NODE_VISUAL_PX,
              src: (d) =>
                d.data?.highlighted
                  ? (d.data?.iconSrcHighlight || d.data?.iconSrc)
                  : (d.data?.iconSrc || ''),
              opacity: (d) => d.data?.inactive ? 0.2 : 1,
              cursor: 'grab',
              labelText: '',
            }},
          }},

          edge: {{
            type: 'line',
            style: {{
              stroke: (d) => d.data?.highlighted ? '#e74c3c' : '#95a5a6',
              lineWidth: (d) => d.data?.highlighted ? 2.5 : (d.data?.isDag ? 2 : 1.2),
              opacity: (d) => d.data?.inactive ? 0.15 : 1,
              endArrow: true,
              labelText: '',
            }},
          }},

          layout: {{
            type: 'd3-force',
            link: {{
              distance: (edge) => {{
                const st = nodeTypeMap[edge.source] || '';
                const tt = nodeTypeMap[edge.target] || '';
                return st === tt ? 60 : 220;
              }},
              strength: (edge) => {{
                const st = nodeTypeMap[edge.source] || '';
                const tt = nodeTypeMap[edge.target] || '';
                return st === tt ? 0.8 : 0.08;
              }},
            }},
            manyBody: {{ strength: -260, distanceMax: 600 }},
            collide: {{ radius: NODE_VISUAL_PX * 0.5 + 6, strength: 0.9, iterations: 3 }},
            center: {{ strength: 0.03 }},
            alphaDecay: 0.01,
            alphaMin: 0.001,
            velocityDecay: 0.35,
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

        function metaValueString(v) {{
          if (v == null) return '';
          if (typeof v === 'object') {{
            try {{ return JSON.stringify(v); }} catch (_) {{ return String(v); }}
          }}
          return String(v);
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
          const graphKey = d.graph_key != null ? String(d.graph_key) : '';
          const qualified = d.qualified != null ? String(d.qualified) : '';
          const facetLabel = d.facet_label != null ? String(d.facet_label) : '';
          const fill = d.fill != null ? String(d.fill) : '';
          const iconSrc =
            d.iconSrc != null && String(d.iconSrc).trim() !== ''
              ? String(d.iconSrc)
              : '';
          const meta = d.meta && typeof d.meta === 'object' && !Array.isArray(d.meta) ? d.meta : {{}};
          const description =
            meta.description != null ? metaValueString(meta.description) : '';
          const metaKeys = Object.keys(meta).sort().filter((k) => k !== 'description');

          let html = '';
          html += '<p class="properties-kicker">PROPERTIES</p>';
          html += '<hr class="properties-rule" />';
          if (iconSrc) {{
            html += '<div class="properties-head">';
            html +=
              '<img class="properties-type-icon" src="' +
              escAttr(iconSrc) +
              '" width="44" height="44" alt="" />';
            html += '<div class="properties-head-text">';
          }}
          html +=
            '<h2 class="properties-entity-name' +
            (useHumanHeadingStyle ? ' is-vertex-kind' : '') +
            '">' +
            esc(entityHeading) +
            '</h2>';
          if (iconSrc) {{
            html += '<p class="properties-sub">Properties</p></div></div>';
          }} else {{
            html += '<p class="properties-sub">Properties</p>';
          }}

          const showShortLabelRow =
            useHumanHeadingStyle &&
            String(shortName).trim() !== '' &&
            String(shortName).trim() !== titleTrim;
          if (showShortLabelRow) {{
            html += '<div class="prop-block"><div class="prop-label">Label</div>';
            html +=
              '<div class="prop-value prop-value-mono prop-short-label-value">' +
              esc(shortName) +
              '</div></div>';
          }}

          const typePretty = nt ? typeDisplayName(nt) : '';
          const headingDuplicatesType =
            typePretty !== '' && entityHeading === typePretty;
          if (nt && !headingDuplicatesType) {{
            html += '<div class="prop-block prop-block-type"><div class="prop-label prop-label-type">Type</div>';
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

          if (title && !useTitleHeading) {{
            html += '<div class="prop-block"><div class="prop-label">Title</div>';
            html += '<div class="prop-value">' + esc(title) + '</div></div>';
          }}

          if (graphKey) {{
            html += '<div class="prop-block"><div class="prop-label">Graph Key</div>';
            html += '<div class="prop-value prop-value-row">';
            html += '<span class="prop-value-mono prop-mono">' + esc(graphKey) + '</span>';
            html +=
              '<button type="button" class="copy-btn" data-copy="' +
              encodeURIComponent(graphKey) +
              '" title="Copy">' +
              COPY_SVG +
              '</button>';
            html += '</div></div>';
          }}

          if (qualified) {{
            html += '<div class="prop-block"><div class="prop-label">Qualified Name</div>';
            html += '<div class="prop-value prop-value-row">';
            html += '<span class="prop-value-mono prop-mono">' + esc(qualified) + '</span>';
            html +=
              '<button type="button" class="copy-btn" data-copy="' +
              encodeURIComponent(qualified) +
              '" title="Copy">' +
              COPY_SVG +
              '</button>';
            html += '</div></div>';
          }}

          if (facetLabel) {{
            html += '<div class="prop-block"><div class="prop-label">Facet</div>';
            html += '<div class="prop-value">' + esc(facetLabel) + '</div></div>';
          }}

          if (fill) {{
            html += '<div class="prop-block"><div class="prop-label">Fill</div>';
            html += '<div class="prop-value fill-row">';
            if (iconSrc) {{
              html +=
                '<img class="fill-type-icon" src="' +
                escAttr(iconSrc) +
                '" width="20" height="20" alt="" />';
            }}
            html += '<span class="fill-swatch" style="background:' + esc(fill) + '"></span>';
            html += '<span class="prop-value-mono">' + esc(fill) + '</span>';
            html += '<span class="fill-hex-muted">' + esc(fill) + '</span>';
            html += '</div></div>';
          }}

          if (description) {{
            html += '<div class="prop-block"><div class="prop-label">Description</div>';
            html +=
              '<div class="prop-value">' +
              esc(description).replace(/\\n/g, '<br/>') +
              '</div></div>';
          }}

          for (const k of metaKeys) {{
            const v = metaValueString(meta[k]);
            html += '<div class="prop-block"><div class="prop-label">' + esc(k) + '</div>';
            html += '<div class="prop-value">' + esc(v) + '</div></div>';
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

        // Highlighting (data-driven, no states)
        let currentHighlight = null;
        let clearTimer = null;

        function resetAllFlags() {{
          graphData.nodes.forEach(n => {{ n.data.highlighted = false; n.data.inactive = false; }});
          graphData.edges.forEach(e => {{ e.data.highlighted = false; e.data.inactive = false; }});
        }}

        function applyHighlight(nodeId) {{
          const adj = adjIndex[nodeId];
          if (!adj) return;
          resetAllFlags();
          graphData.nodes.forEach(n => {{
            if (n.id === nodeId || adj.neighbors.has(n.id)) n.data.highlighted = true;
            else n.data.inactive = true;
          }});
          graphData.edges.forEach(e => {{
            if (adj.edges.has(e.id)) e.data.highlighted = true;
            else e.data.inactive = true;
          }});
          graph.updateData(graphData);
          graph.draw();
        }}

        function clearHighlight() {{
          resetAllFlags();
          graph.updateData(graphData);
          graph.draw();
        }}

        graph.on('node:pointerover', (evt) => {{
          if (clearTimer) clearTimeout(clearTimer);
          const id = evt.target.id;
          if (currentHighlight !== id) {{
            currentHighlight = id;
            applyHighlight(id);
          }}
        }});

        graph.on('node:pointerout', () => {{
          clearTimer = setTimeout(() => {{
            if (currentHighlight !== null) {{
              currentHighlight = null;
              clearHighlight();
            }}
            clearTimer = null;
          }}, 50);
        }});

        graph.on('canvas:click', () => {{
          if (clearTimer) clearTimeout(clearTimer);
          currentHighlight = null;
          clearHighlight();
          closeNodeDetailPanel();
        }});

        graph.on('canvas:mouseleave', () => {{
          if (clearTimer) clearTimeout(clearTimer);
          currentHighlight = null;
          clearHighlight();
        }});

        // Zoom toolbar
        const zoomPct = document.getElementById('zoom-pct');
        const syncZoom = () => {{
          if (!zoomPct) return;
          const z = graph.getZoom();
          zoomPct.textContent = Math.round(z * 100) + '%';
        }};
        graph.on('viewportchange', syncZoom);

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

        window.addEventListener('resize', () => {{
          graph.resize(container.clientWidth, container.clientHeight);
          syncZoom();
        }});
    """

    html = html_template.replace("__G6_SCRIPT__", g6_script.strip())
    path.write_text(html, encoding="utf-8")
    return path


def export_samples_graph_html(
    output_path: str | Path | None = None,
    *,
    title: str = "ActionMachine · samples graph",
    use_timestamp: bool = False,
    graph: rx.PyDiGraph | None = None,
) -> Path:
    """
    Write G6 HTML from the samples interchange graph.

    By default builds the graph dynamically via ``build_sample_coordinator()`` and
    :func:`maxitor.graph_export.coordinator_pygraph_for_visual_export`. Pass ``graph``
    to visualize an already-built ``PyDiGraph`` (e.g. tests or a custom coordinator).
    """
    if graph is None:
        from maxitor.samples.build import build_sample_coordinator  # noqa: PLC0415

        graph = coordinator_pygraph_for_visual_export(build_sample_coordinator())

    if output_path is not None:
        target = Path(output_path)
    else:
        log_dir = _default_archive_logs_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        for p in log_dir.glob("test_domain_graph*"):
            try:
                p.unlink()
            except OSError:
                pass
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        name = f"app_graph_{ts}.html" if use_timestamp else DEFAULT_APP_GRAPH_HTML
        target = log_dir / name

    written = generate_g6_html(graph, target, title=title)
    print(f"Graph HTML written to {written}")
    return written


if __name__ == "__main__":
    export_samples_graph_html()