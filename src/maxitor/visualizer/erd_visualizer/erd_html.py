# src/maxitor/visualizer/erd_visualizer/erd_html.py
"""
Standalone ERD HTML builder — G6 canvas shell shared with :mod:`graph_visualizer` UX patterns.

Injects ``nodes`` / ``edges`` JSON (from :mod:`erd_graph_data`) into :file:`template.html`
and writes ``erd.html`` under the repository ``archive/logs`` directory by default unless
``output_path`` is given (same artifact sink as interchange graph exports).
"""

from __future__ import annotations

import copy
import json
import math
from functools import cache
from html import escape as html_escape
from pathlib import Path
from typing import Any

G6_CDN_URL = "https://unpkg.com/@antv/g6@5/dist/g6.min.js"

_PACKAGE_DIR = Path(__file__).resolve().parent
_TEMPLATE_HTML = _PACKAGE_DIR / "template.html"


def _default_archive_logs_dir() -> Path:
    """Repository ``archive/logs`` output directory for generated artifacts."""
    return Path(__file__).resolve().parents[4] / "archive" / "logs"


# Default write target — parallel to interchange graph HTML under ``archive/logs``.
DEFAULT_ERD_HTML_PATH = _default_archive_logs_dir() / "erd.html"


@cache
def _template_raw() -> str:
    return _TEMPLATE_HTML.read_text(encoding="utf-8")


def _seed_layout(nodes: list[dict[str, Any]], *, radius: float = 220.0) -> None:
    """Mutate ``nodes`` with ``style.x`` / ``style.y`` on a ring (deterministic)."""
    n = len(nodes)
    for i, node in enumerate(nodes):
        ang = 2 * math.pi * i / max(n, 1)
        node.setdefault("style", {})
        node["style"]["x"] = radius * math.cos(ang)
        node["style"]["y"] = radius * math.sin(ang)


_ERD_BOOTSTRAP_JS = """
(function () {
  const graphData = __GRAPH_DATA_JSON__;

  for (const n of graphData.nodes) {
    const s = n.style;
    if (s && typeof s.x === 'number' && typeof s.y === 'number') {
      n.x = s.x;
      n.y = s.y;
    }
  }

  const esc = (s) =>
    String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const escAttr = (s) =>
    String(s)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const adjIndex = {};
  const initAdj = (nid) => {
    if (!adjIndex[nid]) adjIndex[nid] = { edges: new Set(), neighbors: new Set() };
  };
  for (const edge of graphData.edges) {
    initAdj(edge.source);
    initAdj(edge.target);
    adjIndex[edge.source].edges.add(edge.id);
    adjIndex[edge.source].neighbors.add(edge.target);
    adjIndex[edge.target].edges.add(edge.id);
    adjIndex[edge.target].neighbors.add(edge.source);
  }
  for (const node of graphData.nodes) initAdj(node.id);

  const container = document.getElementById('container');
  const graph = new G6.Graph({
    container: 'container',
    width: container.clientWidth,
    height: container.clientHeight,
    autoFit: 'view',
    animation: false,
    data: graphData,
    node: {
      type: 'rect',
      style: {
        size: (d) => [
          Number(d.data?.width) || 128,
          Number(d.data?.height) || 56,
        ],
        radius: 6,
        fill: (d) => d.data?.fill || '#dbeafe',
        stroke: (d) => d.data?.stroke || '#1e293b',
        lineWidth: 1.5,
        labelText: (d) => String(d.data?.label || d.id || ''),
        labelFill: '#0f172a',
        labelFontSize: 12,
        labelFontWeight: 600,
        labelPlacement: 'center',
      },
      state: {
        dim: { opacity: 0.22 },
        hub: { lineWidth: 3, stroke: '#4338ca' },
        nb: { lineWidth: 2, stroke: '#818cf8' },
      },
    },
    edge: {
      type: 'line',
      style: {
        stroke: '#64748b',
        lineWidth: 1.25,
        endArrow: true,
        labelText: (d) => String(d.data?.label || ''),
        labelFontSize: 10,
        labelFill: '#334155',
        labelPadding: [2, 2, 4, 2],
      },
      state: {
        active: { stroke: '#4338ca', lineWidth: 2 },
      },
    },
    layout: {
      type: 'd3-force',
      iterations: 280,
      link: {
        distance: () => 240,
        strength: 0.12,
      },
      manyBody: { strength: -420, distanceMax: 900 },
      collide: {
        radius: 72,
        strength: 0.95,
        iterations: 5,
      },
      center: { strength: 0.02 },
      alphaDecay: 0.015,
      alphaMin: 0.001,
      velocityDecay: 0.34,
    },
    behaviors: [
      { type: 'zoom-canvas', key: 'zoom-canvas', enable: true },
      { type: 'drag-element', key: 'drag-element', dropEffect: 'move' },
      'drag-canvas',
    ],
    plugins: [],
  });

  graph.render();

  const hoverOverlay = document.getElementById('graph-hover-labels');
  let hoverLabelId = null;
  let glowTimer = null;

  function applyNeighborGlow(idStr) {
    const adj = adjIndex[idStr];
    if (!adj || typeof graph.setElementState !== 'function') return;
    const st = {};
    const hub = String(idStr);
    graphData.nodes.forEach((n) => {
      const nid = String(n.id);
      if (nid === hub) st[nid] = ['hub'];
      else if (adj.neighbors.has(nid)) st[nid] = ['nb'];
      else st[nid] = ['dim'];
    });
    graphData.edges.forEach((e) => {
      st[e.id] = adj.edges.has(e.id) ? ['active'] : [];
    });
    void graph.setElementState(st);
  }

  function clearGlow() {
    if (typeof graph.setElementState !== 'function') return;
    const st = {};
    graphData.nodes.forEach((n) => {
      st[n.id] = [];
    });
    graphData.edges.forEach((e) => {
      st[e.id] = [];
    });
    void graph.setElementState(st);
  }

  function clearHoverLabels() {
    if (hoverOverlay) hoverOverlay.innerHTML = '';
    hoverLabelId = null;
  }

  function _xyFromPoint(p) {
    if (p == null) return null;
    if (Array.isArray(p)) return [p[0], p[1]];
    if (typeof p.x === 'number' && typeof p.y === 'number') return [p.x, p.y];
    return null;
  }

  function _canvasPointBelowNode(id, dy) {
    try {
      if (typeof graph.getElementRenderBounds === 'function') {
        const b = graph.getElementRenderBounds(id);
        if (b && b.min != null && b.max != null) {
          const min = b.min;
          const max = b.max;
          const m0 = Array.isArray(min) ? min[0] : min.x;
          const m1 = Array.isArray(min) ? min[1] : min.y;
          const M0 = Array.isArray(max) ? max[0] : max.x;
          const M1 = Array.isArray(max) ? max[1] : max.y;
          return [(m0 + M0) / 2, M1 + dy];
        }
      }
    } catch (_) {}
    try {
      if (typeof graph.getElementPosition === 'function') {
        const xy = _xyFromPoint(graph.getElementPosition(id));
        if (xy) return [xy[0], xy[1] + dy];
      }
    } catch (_) {}
    return null;
  }

  function syncHoverLabels() {
    if (!hoverOverlay) return;
    hoverOverlay.innerHTML = '';
    if (hoverLabelId == null) return;
    const cr = container.getBoundingClientRect();
    const hoverText =
      hoverLabelId != null &&
      hoverLabelId !== '' &&
      graphData.edges.some((e) => String(e.id) === hoverLabelId)
        ? graphData.edges.find((e) => String(e.id) === hoverLabelId)?.data?.label ||
          hoverLabelId
        : graphData.nodes.find((n) => String(n.id) === hoverLabelId)?.data?.label ||
          hoverLabelId;
    const canvasPt = _canvasPointBelowNode(hoverLabelId, 8);
    let left = null;
    let top = null;
    if (canvasPt) {
      try {
        const client =
          typeof graph.getClientByCanvas === 'function'
            ? graph.getClientByCanvas(canvasPt)
            : null;
        const cxy = _xyFromPoint(client);
        if (cxy) {
          left = cxy[0] - cr.left;
          top = cxy[1] - cr.top;
        }
      } catch (_) {}
      if (left == null && typeof graph.getViewportByCanvas === 'function') {
        const vp = graph.getViewportByCanvas(canvasPt);
        const vxy = _xyFromPoint(vp);
        if (vxy) {
          left = vxy[0];
          top = vxy[1];
        }
      }
    }
    if (left == null || top == null) return;
    const div = document.createElement('div');
    div.className = 'graph-hover-label';
    div.textContent = String(hoverText || '');
    div.style.left = `${left}px`;
    div.style.top = `${top}px`;
    hoverOverlay.appendChild(div);
  }

  const detailShell = document.getElementById('node-detail-shell');
  const detailBody = document.getElementById('node-detail-body');
  const COPY_SVG =
    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';

  function closeDetail() {
    if (detailShell) {
      detailShell.classList.remove('is-open');
      detailShell.setAttribute('aria-hidden', 'true');
    }
    if (detailBody) detailBody.innerHTML = '';
  }

  function showDetail(kind, elemIdStr) {
    if (!detailShell || !detailBody) return;
    const isEdge = kind === 'edge';
    const found = isEdge
      ? graphData.edges.find((e) => String(e.id) === String(elemIdStr))
      : graphData.nodes.find((n) => String(n.id) === String(elemIdStr));
    if (!found) {
      closeDetail();
      return;
    }
    const d = found.data || {};
    const title = String(d.label || elemIdStr);
    const panel = d.payload_panel && typeof d.payload_panel === 'object' ? d.payload_panel : {};
    const keys = Object.keys(panel).sort((a, b) => a.localeCompare(b));

    let html = '';
    html +=
      '<h2 class="properties-entity-name is-kind">' +
      esc(title) +
      '</h2>';
    html +=
      '<div class="prop-block"><div class="prop-label">' +
      esc('Kind') +
      '</div>';
    html += '<div class="prop-value">' + esc(isEdge ? 'relationship' : 'entity') + '</div></div>';

    keys.forEach((k) => {
      const raw = panel[k];
      const val = raw == null ? '' : typeof raw === 'object' ? JSON.stringify(raw, null, 0) : String(raw);
      const multiline =
        val.length > 140 || /[\\r\\n]/.test(val);
      html +=
        '<div class="prop-block"><div class="prop-label">' +
        esc(k) +
        '</div>';
      if (multiline)
        html += '<div class="prop-value prop-value-multiline">' + esc(val) + '</div>';
      else {
        html += '<div class="prop-value prop-value-row">';
        html += '<span class="prop-value" style="flex:1">' + esc(val) + '</span>';
        if (val !== '') {
          html +=
            '<button type="button" class="copy-btn" data-copy="' +
            encodeURIComponent(val) +
            '" title="Copy">' +
            COPY_SVG +
            '</button>';
        }
        html += '</div>';
      }
      html += '</div>';
    });

    detailBody.innerHTML = html;
    detailShell.classList.add('is-open');
    detailShell.setAttribute('aria-hidden', 'false');
  }

  detailShell &&
    detailShell.addEventListener('click', (e) => {
      const btn = e.target.closest('.copy-btn');
      if (!btn || !detailShell.contains(btn)) return;
      const enc = btn.getAttribute('data-copy');
      if (enc == null) return;
      try {
        const text = decodeURIComponent(enc);
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text);
      } catch (_) {}
    });

  document.getElementById('node-detail-close')?.addEventListener('click', (e) => {
    e.stopPropagation();
    closeDetail();
  });

  graph.on('node:click', (evt) => {
    let id =
      evt.target?.id ??
      evt.itemId ??
      (Array.isArray(evt.items) ? evt.items[0]?.id : null);
    if (id != null) showDetail('node', String(id));
  });

  graph.on('edge:click', (evt) => {
    let id =
      evt.target?.id ??
      evt.itemId ??
      (Array.isArray(evt.items) ? evt.items[0]?.id : null);
    if (id != null) showDetail('edge', String(id));
  });

  graph.on('node:pointerover', (evt) => {
    if (glowTimer) clearTimeout(glowTimer);
    let id =
      evt.target?.id ??
      evt.itemId ??
      (Array.isArray(evt.items) ? evt.items[0]?.id : null);
    if (id == null) return;
    const sid = String(id);
    applyNeighborGlow(sid);
    hoverLabelId = sid;
    requestAnimationFrame(() => syncHoverLabels());
  });

  graph.on('node:pointerout', () => {
    glowTimer = setTimeout(() => {
      clearGlow();
      clearHoverLabels();
      glowTimer = null;
    }, 40);
  });

  graph.on('canvas:click', () => {
    closeDetail();
    if (glowTimer) clearTimeout(glowTimer);
    clearGlow();
    clearHoverLabels();
  });

  graph.on('canvas:mouseleave', () => {
    if (glowTimer) clearTimeout(glowTimer);
    clearGlow();
    clearHoverLabels();
  });

  const zoomPct = document.getElementById('zoom-pct');
  const syncZoom = () => {
    if (zoomPct) zoomPct.textContent = Math.round(graph.getZoom() * 100) + '%';
  };
  graph.on('viewportchange', () => syncZoom());

  async function zoomBy(factor) {
    const cur = graph.getZoom();
    await graph.zoomTo(Math.min(4, Math.max(0.15, cur * factor)), false);
    syncZoom();
  }

  document.getElementById('zoom-in')?.addEventListener('click', () => zoomBy(1.25));
  document.getElementById('zoom-out')?.addEventListener('click', () => zoomBy(0.8));
  document.getElementById('zoom-fit')?.addEventListener('click', async () => {
    await graph.fitView();
    syncZoom();
  });

  window.addEventListener('resize', () => {
    graph.resize(container.clientWidth, container.clientHeight);
    syncZoom();
    syncHoverLabels();
  });

  syncZoom();
})();
"""


def write_erd_html(
    graph_records: dict[str, Any],
    *,
    output_path: str | Path | None = None,
    title: str = "Entity diagram",
    width: str = "100%",
    height: str = "100vh",
) -> Path:
    """
    Write a standalone HTML file with AntV G6 rendering ``graph_records``.

    ``graph_records`` must carry ``nodes`` and ``edges`` arrays (same shape produced by
    :func:`~maxitor.visualizer.erd_visualizer.erd_graph_data.erd_payload_to_g6_records`). Default output is
    :data:`DEFAULT_ERD_HTML_PATH` (``<repo>/archive/logs/erd.html``).
    """
    payload = copy.deepcopy(graph_records)
    nodes = list(payload.get("nodes") or [])
    edges = list(payload.get("edges") or [])
    _seed_layout(nodes)
    graph_obj = {"nodes": nodes, "edges": edges}
    graph_json = json.dumps(graph_obj, ensure_ascii=False)
    bootstrap = _ERD_BOOTSTRAP_JS.replace("__GRAPH_DATA_JSON__", graph_json)
    safe_title = html_escape(title)
    out = DEFAULT_ERD_HTML_PATH if output_path is None else Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    html = (
        _template_raw()
        .replace("@@HTML_ESCAPED_TITLE@@", safe_title)
        .replace("@@G6_CDN_URL@@", G6_CDN_URL)
        .replace("@@CONTAINER_WIDTH@@", width)
        .replace("@@CONTAINER_HEIGHT@@", height)
        .replace("@@INLINE_G6_SCRIPT@@", bootstrap.strip())
    )
    out.write_text(html, encoding="utf-8")
    return out
