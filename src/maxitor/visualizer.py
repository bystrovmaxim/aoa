# src/maxitor/visualizer.py
"""
HTML visualization for coordinator ``PyDiGraph`` graphs — purpose.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Render a rustworkx graph as a **standalone HTML** page using **AntV G6 5** (single UMD
from a CDN). The export is a strict 1:1 mapping from ``PyDiGraph`` indices to G6 nodes
and ``weighted_edge_list`` entries to edges. ``export_test_domain_graph_html`` uses
the same graph source as GraphML export: ``get_logical_graph()`` when the coordinator
implements ``get_graph_for_visualization``, ``get_logical_graph``, or ``get_graph`` in
that order. Node payloads may use **logical interchange** keys; they are normalized
via ``maxitor.graph_export`` helpers before styling.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    build_test_coordinator()
            │
            ▼
    coordinator_pygraph_for_visual_export(coordinator)
            │
            ▼
    generate_g6_html(graph, path)
            │
            ├── normalize_coordinator_node_payload_for_visualization (per node)
            └── JSON payload → inline G6 script → HTML file under archive/logs

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- No npm build step: the HTML embeds CDN script and serialized graph JSON only.
- Default output path lives under ``archive/logs`` relative to the repository root.
- Normalization never mutates the input ``PyDiGraph`` node payloads.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

- **Happy path:** ``export_test_domain_graph_html()`` writes
  ``archive/logs/test_domain_graph.html`` with G6 zoom controls.
- **Edge case:** ``use_timestamp=True`` appends a UTC suffix so each run creates a
  new HTML file instead of overwriting the default name.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Unknown ``node_type`` values fall back to a neutral color in ``NODE_COLORS``.
- Large dynamic meta values on nodes are truncated when serialized for tooltips.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape as html_escape
from pathlib import Path
from typing import Any

import rustworkx as rx

from maxitor.graph_export import (
    coordinator_pygraph_for_visual_export,
    normalize_coordinator_node_payload_for_visualization,
)

# AntV G6 5 — см. https://g6.antv.antgroup.com/en/manual/getting-started/installation
G6_CDN_URL = "https://unpkg.com/@antv/g6@5/dist/g6.min.js"

# Имя HTML по умолчанию — всегда одно и то же (перезапись при экспорте).
DEFAULT_TEST_DOMAIN_GRAPH_HTML = "test_domain_graph.html"

# Уникальный цвет на каждый известный node_type.
NODE_COLORS: dict[str, str] = {
    "action": "#3498db",
    "action_schemas": "#27ae60",
    "aspect": "#e67e22",
    "checker": "#f1c40f",
    "compensator": "#c0392b",
    "connection": "#9b59b6",
    "dependency": "#f39c12",
    "described_fields": "#a569bd",
    "domain": "#2ecc71",
    "entity": "#1abc9c",
    "error_handler": "#e84393",
    "meta": "#7f8c8d",
    "role": "#e74c3c",
    "role_class": "#8e44ad",
    "role_mode": "#2980b9",
    "sensitive": "#d35400",
    "subscription": "#16a085",
}

DEFAULT_COLOR = "#95a5a6"

_SKIP_META_KEYS = frozenset(
    {
        "node_type",
        "name",
        "label",
        "graph_key",
        "facet_label",
        "vertex_type",
        "id",
        "display_name",
        "stereotype",
        "properties",
    },
)


def _graph_vertex_key(node: dict[str, Any]) -> str:
    """Ключ вершины как у ``GateCoordinator._make_key`` (``node_type:name``)."""
    nt = str(node.get("node_type", "") or "")
    nm = str(node.get("name", "") or "")
    return f"{nt}:{nm}"


def _vertex_facet_label(node: dict[str, Any]) -> str:
    """Подпись на узле: фасет + класс — чтобы не сливались разные вершины одного типа."""
    nt = str(node.get("node_type", "unknown"))
    short = _element_short_name(node)
    return f"{nt}\n{short}"


def _element_short_name(node: dict[str, Any]) -> str:
    """Короткое имя класса/сущности для подписи на графе (без пакетов)."""
    cr = node.get("class_ref")
    if isinstance(cr, type):
        return cr.__name__
    raw = str(node.get("name", "") or node.get("label", "") or "").strip()
    if not raw:
        return "?"
    if "." in raw:
        return raw.rsplit(".", 1)[-1]
    return raw


def _element_qualified_name(node: dict[str, Any]) -> str:
    """Полное имя для tooltip."""
    cr = node.get("class_ref")
    if isinstance(cr, type):
        return f"{cr.__module__}.{cr.__qualname__}"
    return str(node.get("name", "") or node.get("label", "") or "?")


def _serialize_graph_value(value: Any) -> str:
    if isinstance(value, type):
        return f"{value.__module__}.{value.__qualname__}"
    if value is None:
        return ""
    return str(value)[:800]


def _default_archive_logs_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "archive" / "logs"


def generate_g6_html(
    graph: rx.PyDiGraph,
    output_path: str | Path,
    *,
    title: str = "ActionMachine Graph",
    width: str = "100%",
    height: str = "800px",
    node_colors: dict[str, str] | None = None,
) -> Path:
    """Write a standalone HTML page with G6 5 for the given ``PyDiGraph`` topology."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    colors = node_colors if node_colors is not None else NODE_COLORS

    g6_nodes: list[dict[str, Any]] = []
    for idx in graph.node_indices():
        raw = graph[idx]
        node = dict(raw) if isinstance(raw, dict) else {}
        node = normalize_coordinator_node_payload_for_visualization(node)
        node_type = str(node.get("node_type", "unknown"))
        short = _element_short_name(node)
        facet_label = _vertex_facet_label(node)
        graph_key = _graph_vertex_key(node)
        qualified = _element_qualified_name(node)
        meta = {
            k: _serialize_graph_value(v)
            for k, v in node.items()
            if k not in _SKIP_META_KEYS and k != "class_ref"
        }
        fill = colors.get(node_type, DEFAULT_COLOR)
        g6_nodes.append(
            {
                "id": str(idx),
                "type": "rect",
                "data": {
                    "label": short,
                    "facet_label": facet_label,
                    "graph_key": graph_key,
                    "qualified": qualified,
                    "node_type": node_type,
                    "meta": meta,
                },
                "style": {
                    "fill": fill,
                    "stroke": "#2c3e50",
                    "lineWidth": 2,
                    "radius": 6,
                    "size": [220, 56],
                    # Две строки: node_type и класс — соответствие реальным разным вершинам.
                    "labelText": facet_label,
                    "labelFill": "#ffffff",
                    "labelFontSize": 9,
                    "labelFontWeight": 600,
                    "labelPlacement": "center",
                    "labelWordWrap": True,
                    "labelMaxWidth": 208,
                },
            },
        )

    g6_edges: list[dict[str, Any]] = []
    for ei, (src, tgt, edge_data) in enumerate(graph.weighted_edge_list()):
        if isinstance(edge_data, dict):
            elabel = str(edge_data.get("edge_type", ""))
        else:
            elabel = str(edge_data)
        g6_edges.append(
            {
                "id": f"e-{src}-{tgt}-{ei}",
                "source": str(src),
                "target": str(tgt),
                "type": "line",
                "data": {"label": elabel},
                "style": {"stroke": "#7f8c8d", "lineWidth": 1.5},
            },
        )

    graph_payload = {"nodes": g6_nodes, "edges": g6_edges}
    data_json = json.dumps(graph_payload, ensure_ascii=False)
    safe_title = html_escape(title)

    # Плейсхолдер, чтобы не экранировать весь JS через f-string.
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title}</title>
    <script src="{G6_CDN_URL}"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: system-ui, sans-serif; }}
        #graph-root {{
            position: relative;
            width: {width};
            height: {height};
            box-sizing: border-box;
        }}
        #container {{
            position: absolute;
            inset: 0;
            box-sizing: border-box;
            /* Фон «как в Miro»: светлая плоскость + регулярная сетка точек */
            background-color: #f4f5f7;
            background-image: radial-gradient(rgba(160, 168, 180, 0.42) 1px, transparent 1px);
            background-size: 20px 20px;
            background-position: 0 0;
        }}
        .zoom-toolbar {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 10;
            display: flex;
            flex-direction: column;
            gap: 4px;
            align-items: stretch;
        }}
        .zoom-toolbar button {{
            min-width: 36px;
            padding: 6px 8px;
            font-size: 14px;
            line-height: 1;
            cursor: pointer;
            border: 1px solid #c5cad3;
            border-radius: 6px;
            background: #fff;
            color: #2c3e50;
            box-shadow: 0 1px 2px rgba(0,0,0,0.06);
        }}
        .zoom-toolbar button:hover {{ background: #eef0f3; }}
        .zoom-toolbar .zoom-label {{
            font-size: 11px;
            text-align: center;
            color: #5c6370;
            user-select: none;
            padding: 2px 0;
        }}
    </style>
</head>
<body>
    <div id="graph-root">
        <div id="container"></div>
        <div class="zoom-toolbar" id="zoom-toolbar" aria-label="Canvas zoom">
            <button type="button" id="zoom-in" title="Увеличить">+</button>
            <span class="zoom-label" id="zoom-pct">100%</span>
            <button type="button" id="zoom-out" title="Уменьшить">−</button>
            <button type="button" id="zoom-fit" title="По размеру окна">⊡</button>
        </div>
    </div>
    <script>
__G6_SCRIPT__
    </script>
</body>
</html>
"""

    _g6_body = r"""
        const graphData = __DATA_JSON__;
        const { Graph } = G6;

        const esc = (s) =>
          String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        const graph = new Graph({
          container: 'container',
          width: document.getElementById('container').clientWidth,
          height: document.getElementById('container').clientHeight,
          autoFit: 'view',
          animation: false,
          data: graphData,
          node: {
            type: 'rect',
            style: {
              size: (d) => (Array.isArray(d.style?.size) ? d.style.size : [200, 48]),
              fill: (d) => d.style?.fill || '#95a5a6',
              stroke: (d) => d.style?.stroke || '#2c3e50',
              lineWidth: (d) => d.style?.lineWidth ?? 2,
              radius: (d) => d.style?.radius ?? 6,
              labelText: (d) =>
                d.style?.labelText != null && d.style.labelText !== ''
                  ? d.style.labelText
                  : (d.data?.label != null ? String(d.data.label) : String(d.id ?? '')),
              labelFill: (d) => d.style?.labelFill || '#ffffff',
              labelFontSize: (d) => d.style?.labelFontSize ?? 10,
              labelFontWeight: (d) => d.style?.labelFontWeight ?? 600,
              labelPlacement: (d) => d.style?.labelPlacement || 'center',
              labelWordWrap: true,
              labelMaxWidth: (d) => d.style?.labelMaxWidth ?? 188,
            },
          },
          edge: {
            type: 'line',
            style: {
              stroke: (d) => d.style?.stroke || '#7f8c8d',
              lineWidth: (d) => d.style?.lineWidth ?? 1.5,
              endArrow: true,
              labelText: (d) => (d.data?.label != null ? d.data.label : ''),
              labelFontSize: 8,
            },
          },
          layout: {
            type: 'dagre',
            rankdir: 'TB',
            nodesep: 36,
            ranksep: 52,
          },
          behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
          plugins: [
            {
              type: 'tooltip',
              enable: (e) => e.targetType === 'node',
              getContent: (e, items) => {
                const n = items[0];
                const data = n.data || {};
                const gk = data.graph_key || '';
                const lines = [
                  '<b>' + esc(gk || (data.node_type + ':' + (data.label || ''))) + '</b>',
                  'Индекс PyDiGraph: ' + esc(String(n.id ?? '')),
                ];
                if (data.qualified) {
                  lines.push(
                    '<span style="opacity:0.88;font-size:11px;">' + esc(data.qualified) + '</span>',
                  );
                }
                const meta = data.meta || {};
                for (const [k, v] of Object.entries(meta)) {
                  lines.push(esc(k) + ': ' + esc(v));
                }
                return '<div style="font-size:12px;line-height:1.45;">' + lines.join('<br>') + '</div>';
              },
            },
          ],
        });

        graph.render();

        const zoomPct = document.getElementById('zoom-pct');
        const syncZoomLabel = () => {
          if (!zoomPct) return;
          const z = typeof graph.getZoom === 'function' ? graph.getZoom() : 1;
          zoomPct.textContent = Math.round(z * 100) + '%';
        };
        syncZoomLabel();
        if (typeof graph.on === 'function') {
          graph.on('viewportchange', syncZoomLabel);
        }

        const zoomOrigin = () =>
          typeof graph.getCanvasCenter === 'function'
            ? graph.getCanvasCenter()
            : (() => {
                const c = document.getElementById('container');
                return [c.clientWidth / 2, c.clientHeight / 2];
              })();

        document.getElementById('zoom-in')?.addEventListener('click', () => {
          graph.zoomBy(1.2, false, zoomOrigin()).then(syncZoomLabel).catch(syncZoomLabel);
        });
        document.getElementById('zoom-out')?.addEventListener('click', () => {
          graph.zoomBy(0.8, false, zoomOrigin()).then(syncZoomLabel).catch(syncZoomLabel);
        });
        document.getElementById('zoom-fit')?.addEventListener('click', () => {
          graph
            .fitView({ when: 'always', direction: 'both' }, false)
            .then(syncZoomLabel)
            .catch(syncZoomLabel);
        });

        window.addEventListener('resize', () => {
          const c = document.getElementById('container');
          if (c && typeof graph.resize === 'function') {
            graph.resize(c.clientWidth, c.clientHeight);
          }
          syncZoomLabel();
        });
"""
    g6_script = _g6_body.replace("__DATA_JSON__", data_json)

    out = html_template.replace("__G6_SCRIPT__", g6_script.strip("\n"))
    path.write_text(out, encoding="utf-8")
    return path


def export_test_domain_graph_html(
    output_path: str | Path | None = None,
    *,
    title: str = "ActionMachine test_domain graph",
    use_timestamp: bool = False,
) -> Path:
    """Build the test_domain coordinator and write a G6 HTML graph under ``archive/logs``."""
    from maxitor.test_domain.build import build_test_coordinator  # pylint: disable=import-outside-toplevel

    coordinator = build_test_coordinator()
    graph = coordinator_pygraph_for_visual_export(coordinator)

    if output_path is not None:
        target = Path(output_path)
    else:
        log_dir = _default_archive_logs_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        name = f"test_domain_graph_{ts}.html" if use_timestamp else DEFAULT_TEST_DOMAIN_GRAPH_HTML
        target = log_dir / name

    written = generate_g6_html(graph, target, title=title)
    print(f"Graph HTML written to {written}")
    return written


if __name__ == "__main__":
    export_test_domain_graph_html()
