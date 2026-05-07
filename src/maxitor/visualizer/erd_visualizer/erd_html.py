# src/maxitor/visualizer/erd_visualizer/erd_html.py
"""
Standalone ERD HTML export — AntV **X6** ER-style nodes plus **ELK** layered auto-layout,
orthogonal edge routing, and G6-style UX (zoom, properties panel, LOD).
"""

from __future__ import annotations

import copy
import json
from functools import cache
from html import escape as html_escape
from pathlib import Path
from typing import Any

# ESM entry (browser ``import()``); pinned for reproducible offline-friendly builds.
X6_MODULE_URL = "https://esm.sh/@antv/x6@2.19.2"
ELK_MODULE_URL = "https://esm.sh/elkjs@0.11.1"

_PACKAGE_DIR = Path(__file__).resolve().parent
_TEMPLATE_HTML = _PACKAGE_DIR / "template.html"


def _default_archive_logs_dir() -> Path:
    """Repository ``archive/logs`` output directory for generated artifacts."""
    return Path(__file__).resolve().parents[4] / "archive" / "logs"


DEFAULT_ERD_HTML_PATH = _default_archive_logs_dir() / "erd.html"


@cache
def _template_raw() -> str:
    return _TEMPLATE_HTML.read_text(encoding="utf-8")


_ERD_BOOTSTRAP_JS = """
(async function () {
  const x6Mod = await import(__X6_MODULE_IMPORT__);
  const { Graph, Shape } = x6Mod;
  let ELK = null;
  try {
    const elkMod = await import(__ELK_MODULE_IMPORT__);
    ELK = elkMod.default ?? elkMod.ELK ?? elkMod;
  } catch (err) {
    console.warn('erd: failed to import elkjs; falling back to simple layout', err);
  }

  const LINE_HEIGHT = 24;
  const NODE_WIDTH = 150;

  Graph.registerPortLayout(
    'erPortPosition',
    (portsPositionArgs) =>
      portsPositionArgs.map((_, index) => ({
        position: { x: 0, y: (index + 1) * LINE_HEIGHT },
        angle: 0,
      })),
    true,
  );

  Graph.registerNode(
    'er-rect',
    {
      inherit: 'rect',
      markup: [
        { tagName: 'rect', selector: 'body' },
        { tagName: 'text', selector: 'label' },
      ],
      attrs: {
        body: {
          strokeWidth: 1,
          stroke: '#5F95FF',
          fill: '#5F95FF',
        },
        label: {
          refX: NODE_WIDTH / 2,
          refY: LINE_HEIGHT / 2,
          textAnchor: 'middle',
          textVerticalAnchor: 'middle',
          fontWeight: 'bold',
          fill: '#ffffff',
          fontSize: 12,
        },
      },
      ports: {
        groups: {
          list: {
            markup: [
              { tagName: 'rect', selector: 'portBody' },
              { tagName: 'text', selector: 'portNameLabel' },
              { tagName: 'text', selector: 'portTypeLabel' },
            ],
            attrs: {
              portBody: {
                width: NODE_WIDTH,
                height: LINE_HEIGHT,
                strokeWidth: 1,
                stroke: '#5F95FF',
                fill: '#EFF4FF',
                magnet: true,
              },
              portNameLabel: {
                ref: 'portBody',
                refX: 6,
                refY: 6,
                fontSize: 10,
              },
              portTypeLabel: {
                ref: 'portBody',
                refX: 95,
                refY: 6,
                fontSize: 10,
              },
            },
            position: 'erPortPosition',
          },
        },
      },
    },
    true,
  );

  async function layoutElk(g) {
    if (typeof ELK !== 'function') {
      console.warn('erd: elkjs bundle did not export a constructor');
      return false;
    }
    const elk = new ELK();
    const nodes = g.getNodes().filter((n) => n.shape === 'er-rect');
    const edges = g.getEdges();
    const idSet = new Set(nodes.map((n) => n.id));
    const elkGraph = {
      id: 'root',
      layoutOptions: {
        'elk.algorithm': 'layered',
        'elk.direction': 'RIGHT',
        'elk.edgeRouting': 'ORTHOGONAL',
        'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
        'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
        'elk.spacing.nodeNode': '72',
        'elk.spacing.edgeEdge': '24',
        'elk.spacing.edgeNode': '36',
        'elk.layered.spacing.nodeNodeBetweenLayers': '140',
        'elk.layered.spacing.edgeNodeBetweenLayers': '48',
        'elk.layered.spacing.edgeEdgeBetweenLayers': '24',
        'elk.padding': '[top=60,left=60,bottom=60,right=60]',
      },
      children: [],
      edges: [],
    };
    nodes.forEach((n) => {
      const sz = n.size();
      elkGraph.children.push({ id: n.id, width: sz.width, height: sz.height });
    });
    edges.forEach((e) => {
      const sCell = typeof e.getSourceCell === 'function' ? e.getSourceCell() : null;
      const tCell = typeof e.getTargetCell === 'function' ? e.getTargetCell() : null;
      const sid = sCell && sCell.id;
      const tid = tCell && tCell.id;
      if (!sid || !tid || !idSet.has(sid) || !idSet.has(tid)) return;
      elkGraph.edges.push({ id: String(e.id), sources: [sid], targets: [tid] });
    });
    let layout;
    try {
      layout = await elk.layout(elkGraph);
    } catch (err) {
      console.warn('erd elk layout failed', err);
      return false;
    }
    const byId = new Map(nodes.map((n) => [n.id, n]));
    (layout.children ?? []).forEach((child) => {
      if (child.x == null || child.y == null) return;
      const n = byId.get(child.id);
      if (!n) return;
      n.position(child.x, child.y);
    });
    const edgeById = new Map(edges.map((e) => [String(e.id), e]));
    (layout.edges ?? []).forEach((le) => {
      const edge = edgeById.get(String(le.id));
      if (!edge) return;
      const firstSection = Array.isArray(le.sections) ? le.sections[0] : null;
      if (!firstSection) return;
      const bends = Array.isArray(firstSection.bendPoints) ? firstSection.bendPoints : [];
      if (typeof edge.setVertices === 'function') {
        edge.setVertices(bends.map((p) => ({ x: p.x, y: p.y })));
      }
    });
    return true;
  }

  function layoutFallback(g) {
    const nodes = g.getNodes().filter((n) => n.shape === 'er-rect');
    const centerId =
      nodes.find((n) => /OrderEntity$/.test(String(n.id)))?.id ??
      nodes[Math.floor(nodes.length / 2)]?.id;
    const ordered = nodes
      .slice()
      .sort((a, b) => {
        if (a.id === centerId) return -1;
        if (b.id === centerId) return 1;
        return String(a.id).localeCompare(String(b.id));
      });
    ordered.forEach((n, i) => {
      if (i === 0) {
        n.position(360, 160);
        return;
      }
      const col = i % 2 === 1 ? -1 : 1;
      const row = Math.floor((i - 1) / 2);
      n.position(360 + col * 280, 80 + row * 220);
    });
  }

  const esc = (s) =>
    String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  const COPY_SVG =
    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';

  const MIN_SCALE = 0.2;
  const MAX_SCALE = 2.5;
  const WHEEL_ZOOM_SENSITIVITY = 0.0045;

  const container = document.getElementById('container');
  const graph = new Graph({
    container,
    width: container.clientWidth,
    height: container.clientHeight,
    connecting: {
      router: { name: 'normal' },
      connector: { name: 'rounded', args: { radius: 8 } },
      createEdge() {
        return new Shape.Edge({
          attrs: {
            line: {
              stroke: '#A2B1C3',
              strokeWidth: 2,
            },
          },
        });
      },
    },
    mousewheel: {
      enabled: false,
      minScale: MIN_SCALE,
      maxScale: MAX_SCALE,
    },
    panning: true,
    background: {
      color: '#f4f5f7',
    },
    grid: {
      visible: true,
      size: 20,
    },
  });

  graph.fromJSON(__CELL_DOCUMENT_JSON__);
  const didLayout = await layoutElk(graph);
  if (!didLayout) layoutFallback(graph);
  graph.zoomToFit({ padding: 48, maxScale: 1.08 });

  const detailShell = document.getElementById('node-detail-shell');
  const detailBody = document.getElementById('node-detail-body');

  function closeDetail() {
    if (detailShell) {
      detailShell.classList.remove('is-open');
      detailShell.setAttribute('aria-hidden', 'true');
    }
    if (detailBody) detailBody.innerHTML = '';
  }

  function showDetail(cell) {
    if (!detailShell || !detailBody || !cell) return;
    const raw = typeof cell.getData === 'function' ? cell.getData() : {};
    const panel =
      raw && typeof raw.payload_panel === 'object' && !Array.isArray(raw.payload_panel)
        ? raw.payload_panel
        : {};
    const keys = Object.keys(panel).sort((a, b) => a.localeCompare(b));
    let title = '';
    if (cell.isNode && cell.isNode() && cell.shape === 'er-rect') {
      const tlab = cell.attr('label/text');
      title = tlab != null ? String(tlab).trim() : '';
    }
    if (!title) title = String(panel.label || panel.id || cell.id || '');
    let html =
      '<h2 class="properties-entity-name is-kind">' +
      esc(title) +
      '</h2>';
    keys.forEach((k) => {
      let v =
        panel[k] == null
          ? ''
          : typeof panel[k] === 'object'
            ? JSON.stringify(panel[k], null, 0)
            : String(panel[k]);
      const multiline = v.length > 140 || /[\\r\\n]/.test(v);
      html += '<div class="prop-block"><div class="prop-label">' + esc(k) + '</div>';
      if (multiline) html += '<div class="prop-value prop-value-multiline">' + esc(v) + '</div>';
      else {
        html += '<div class="prop-value prop-value-row">';
        html += '<span class="prop-value" style="flex:1">' + esc(v) + '</span>';
        if (v !== '')
          html +=
            '<button type="button" class="copy-btn" data-copy="' +
            encodeURIComponent(v) +
            '" title="Copy">' +
            COPY_SVG +
            '</button>';
        html += '</div>';
      }
      html += '</div>';
    });
    detailBody.innerHTML = html;
    detailShell.classList.add('is-open');
    detailShell.setAttribute('aria-hidden', 'false');
  }

  detailShell?.addEventListener('click', (e) => {
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

  graph.on('blank:click', () => closeDetail());

  graph.on('cell:click', ({ cell }) => {
    if (!cell || !cell.id) return;
    const d =
      typeof cell.getData === 'function' ? cell.getData() : {};
    if (
      !d ||
      typeof d.payload_panel !== 'object' ||
      d.payload_panel == null ||
      Array.isArray(d.payload_panel)
    )
      return;
    showDetail(cell);
  });

  let lodLevel = 'detailed';

  function applyLodLevel(level) {
    if (lodLevel === level) return;
    lodLevel = level;
    graph.batchUpdate(() => {
      graph.getNodes().forEach((node) => {
        if (node.shape !== 'er-rect') return;
        const dd = typeof node.getData === 'function' ? node.getData() : {};
        const types =
          dd && Array.isArray(dd.lod_port_types)
            ? dd.lod_port_types
            : [];
        const listPorts =
          typeof node.getPorts === 'function'
            ? node.getPorts().filter((p) => p.group === 'list')
            : [];
        listPorts.forEach((slot, i) => {
          const pid = slot?.id == null ? null : String(slot.id);
          if (!pid) return;
          node.setPortProp(
            pid,
            'attrs/portTypeLabel/text',
            level === 'overview' ? '' : String(types[i] ?? ''),
          );
          node.setPortProp(pid, 'attrs/portNameLabel/fontSize', level === 'overview' ? 9 : 10);
        });
        node.attr('label/fontSize', level === 'overview' ? 11 : 12);
      });
    });
  }

  const zoomPct = document.getElementById('zoom-pct');
  function currentScale() {
    return graph.transform?.getScale?.()?.sx ?? 1;
  }
  function clampScale(scale) {
    return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
  }
  function setAbsoluteZoom(scale) {
    const next = clampScale(scale);
    if (typeof graph.zoomTo === 'function') {
      graph.zoomTo(next);
      return;
    }
    const curr = currentScale();
    const ratio = next / (curr <= 0 ? 1 : curr);
    graph.zoom(ratio);
  }
  function syncZoom() {
    if (!zoomPct) return;
    const sx = currentScale();
    zoomPct.textContent = Math.round(Number(sx) * 100) + '%';
  }

  graph.on('scale', () => {
    syncZoom();
    const sx = currentScale();
    applyLodLevel(sx <= 0.65 ? 'overview' : 'detailed');
  });

  graph.on('translate', () => syncZoom());

  let wheelAccum = 0;
  let wheelRaf = null;
  const flushWheelZoom = () => {
    wheelRaf = null;
    // Clamp one frame impulse to avoid large jump spikes from trackpads.
    const dy = Math.max(-120, Math.min(120, wheelAccum));
    wheelAccum = 0;
    const factor = Math.exp(-dy * WHEEL_ZOOM_SENSITIVITY);
    setAbsoluteZoom(currentScale() * factor);
    syncZoom();
  };
  container.addEventListener(
    'wheel',
    (evt) => {
      evt.preventDefault();
      wheelAccum += evt.deltaY;
      if (wheelRaf == null) wheelRaf = requestAnimationFrame(flushWheelZoom);
    },
    { passive: false },
  );

  const doZoom = (factor) => {
    const cur = currentScale();
    setAbsoluteZoom(cur * factor);
    syncZoom();
  };

  document.getElementById('zoom-in')?.addEventListener('click', () => {
    doZoom(1.25);
  });
  document.getElementById('zoom-out')?.addEventListener('click', () => {
    doZoom(0.8);
  });
  document.getElementById('zoom-fit')?.addEventListener('click', () => {
    graph.zoomToFit({ padding: 48, maxScale: 1.08 });
    syncZoom();
    applyLodLevel(currentScale() <= 0.65 ? 'overview' : 'detailed');
  });

  syncZoom();

  window.addEventListener('resize', () => {
    graph.resize(container.clientWidth, container.clientHeight);
    syncZoom();
  });

  const sx0 = currentScale();
  applyLodLevel(sx0 <= 0.65 ? 'overview' : 'detailed');
})();
"""


def write_erd_html(
    document: dict[str, Any],
    *,
    output_path: str | Path | None = None,
    title: str = "Entity diagram",
    width: str = "100%",
    height: str = "100vh",
) -> Path:
    """
    Write a standalone HTML file with AntV X6 ER rendering.

    ``document`` must be an X6 graph JSON object (typically ``{\"cells\": [...]}`` from
    :func:`~maxitor.visualizer.erd_visualizer.erd_graph_data.erd_payload_to_x6_document`).
    Default output is :data:`DEFAULT_ERD_HTML_PATH` (``<repo>/archive/logs/erd.html``).
    """
    payload = copy.deepcopy(document)
    if "cells" not in payload:
        msg = "write_erd_html expects document with top-level \"cells\" (X6 fromJSON)"
        raise TypeError(msg)

    cells_json = json.dumps(payload, ensure_ascii=False)
    js_import = json.dumps(X6_MODULE_URL)
    elk_imp = json.dumps(ELK_MODULE_URL)
    bootstrap = (
        _ERD_BOOTSTRAP_JS.replace("__X6_MODULE_IMPORT__", js_import)
        .replace("__ELK_MODULE_IMPORT__", elk_imp)
        .replace("__CELL_DOCUMENT_JSON__", cells_json)
    )
    safe_title = html_escape(title)
    out = DEFAULT_ERD_HTML_PATH if output_path is None else Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    html = (
        _template_raw()
        .replace("@@HTML_ESCAPED_TITLE@@", safe_title)
        .replace("@@CONTAINER_WIDTH@@", width)
        .replace("@@CONTAINER_HEIGHT@@", height)
        .replace("@@INLINE_ERD_SCRIPT@@", bootstrap.strip())
    )
    out.write_text(html, encoding="utf-8")
    return out


def write_erd_html_from_coordinator(
    coordinator: Any,
    domain_cls: type[Any],
    *,
    output_path: str | Path | None = None,
    title: str = "Entity diagram",
    width: str = "100%",
    height: str = "100vh",
) -> Path:
    """
    Derive cells from interchange ``Entity`` rows for ``domain_cls`` and write standalone HTML.

    ``coordinator`` must be a :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`
    produced the same way as production (typically ``create_node_graph_coordinator()`` after
    application modules registering entities/actions are imported). ``domain_cls`` is e.g.
    :class:`~maxitor.samples.store.domain.StoreDomain``.

    AI-CORE-BEGIN
    PURPOSE: Convenience path from built interchange graph → X6 ER export without assembling payload manually.
    INPUT: Coordinator after ``build``; ``domain_cls`` ``BaseDomain`` subclass.
    OUTPUT: Same as :func:`write_erd_html`; document is ``erd_payload_to_x6_document(projection)``.
    AI-CORE-END
    """
    from action_machine.domain.base_domain import BaseDomain
    from graph.node_graph_coordinator import NodeGraphCoordinator
    from maxitor.visualizer.erd_visualizer.erd_graph_data import (
        erd_payload_from_coordinator_for_domain,
        erd_payload_to_x6_document,
    )

    if not isinstance(coordinator, NodeGraphCoordinator):
        msg = "coordinator must be a built NodeGraphCoordinator"
        raise TypeError(msg)
    if not isinstance(domain_cls, type) or not issubclass(domain_cls, BaseDomain):
        msg = "domain_cls must be a BaseDomain subclass"
        raise TypeError(msg)

    payload = erd_payload_from_coordinator_for_domain(coordinator, domain_cls)
    doc = erd_payload_to_x6_document(payload)
    return write_erd_html(doc, output_path=output_path, title=title, width=width, height=height)
