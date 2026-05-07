# src/maxitor/visualizer/erd_visualizer/erd_html.py
# pylint: disable=import-outside-toplevel,too-many-lines
"""
Standalone ERD HTML export — normalized table nodes with X6, Mermaid, Graphviz, and D2
renderer variants plus ERD/Graphviz layout pickers.
Tables render PK/FK compartments; relationship ends use crow-foot text markers instead of
arrowheads. Long table, field, and type labels are truncated with a fixed tooltip.
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
MERMAID_MODULE_URL = "https://esm.sh/mermaid@11.12.0"
GRAPHVIZ_MODULE_URL = "https://cdn.jsdelivr.net/npm/@hpcc-js/wasm-graphviz/dist/index.js"
D2_MODULE_URL = "https://esm.sh/@terrastruct/d2@0.1.33"

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
  let mermaidApi = null;
  let graphvizApi = null;
  let d2Api = null;

  const LINE_HEIGHT = 24;
  const NODE_WIDTH = 190;
  const ROLE_WIDTH = 46;
  const TYPE_X = 132;

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
          stroke: '#1f2937',
          fill: '#e5e7eb',
        },
        label: {
          refX: NODE_WIDTH / 2,
          refY: LINE_HEIGHT / 2,
          textAnchor: 'middle',
          textVerticalAnchor: 'middle',
          fontWeight: '500',
          fill: '#111827',
          fontSize: 12,
        },
      },
      ports: {
        groups: {
          list: {
            markup: [
              { tagName: 'rect', selector: 'portBody' },
              { tagName: 'line', selector: 'roleDivider' },
              { tagName: 'text', selector: 'portRoleLabel' },
              { tagName: 'text', selector: 'portNameLabel' },
              { tagName: 'text', selector: 'portTypeLabel' },
            ],
            attrs: {
              portBody: {
                width: NODE_WIDTH,
                height: LINE_HEIGHT,
                strokeWidth: 1,
                stroke: '#1f2937',
                fill: '#f9fafb',
                magnet: false,
              },
              roleDivider: {
                x1: ROLE_WIDTH,
                y1: 0,
                x2: ROLE_WIDTH,
                y2: LINE_HEIGHT,
                stroke: '#1f2937',
                strokeWidth: 1,
              },
              portRoleLabel: {
                ref: 'portBody',
                refX: 6,
                refY: 6,
                fontSize: 10,
                fontWeight: 'bold',
                fill: '#111827',
              },
              portNameLabel: {
                ref: 'portBody',
                refX: ROLE_WIDTH + 8,
                refY: 6,
                fontSize: 10,
                fill: '#111827',
              },
              portTypeLabel: {
                ref: 'portBody',
                refX: TYPE_X,
                refY: 6,
                fontSize: 10,
                fill: '#374151',
              },
            },
            position: 'erPortPosition',
          },
        },
      },
    },
    true,
  );

  async function layoutGrid(g) {
    const nodes = g.getNodes().filter((n) => n.shape === 'er-rect');
    const edges = g.getEdges();
    if (!nodes.length) return true;
    const byId = new Map(nodes.map((n) => [String(n.id), n]));
    const neighbors = new Map(nodes.map((n) => [String(n.id), new Set()]));
    edges.forEach((e) => {
      const sCell = typeof e.getSourceCell === 'function' ? e.getSourceCell() : null;
      const tCell = typeof e.getTargetCell === 'function' ? e.getTargetCell() : null;
      const sid = sCell && String(sCell.id);
      const tid = tCell && String(tCell.id);
      if (!sid || !tid || sid === tid || !neighbors.has(sid) || !neighbors.has(tid)) return;
      neighbors.get(sid).add(tid);
      neighbors.get(tid).add(sid);
    });

    const components = [];
    const seen = new Set();
    const degree = (id) => neighbors.get(id)?.size ?? 0;
    nodes.forEach((n) => {
      const root = String(n.id);
      if (seen.has(root)) return;
      const queue = [root];
      const ids = [];
      seen.add(root);
      while (queue.length) {
        const id = queue.shift();
        ids.push(id);
        [...(neighbors.get(id) ?? [])]
          .sort((a, b) => degree(b) - degree(a) || a.localeCompare(b))
          .forEach((next) => {
            if (seen.has(next)) return;
            seen.add(next);
            queue.push(next);
          });
      }
      components.push(ids);
    });
    components.sort((a, b) => b.length - a.length);

    let offsetX = 340;
    let offsetY = 120;
    let rowHeight = 0;
    const viewportWidth = Math.max(1280, container.clientWidth || 1280);
    components.forEach((ids) => {
      const hub = ids.slice().sort((a, b) => degree(b) - degree(a) || a.localeCompare(b))[0];
      const order = [];
      const localSeen = new Set([hub]);
      const queue = [hub];
      while (queue.length) {
        const id = queue.shift();
        order.push(id);
        [...(neighbors.get(id) ?? [])]
          .filter((next) => ids.includes(next))
          .sort((a, b) => degree(b) - degree(a) || a.localeCompare(b))
          .forEach((next) => {
            if (localSeen.has(next)) return;
            localSeen.add(next);
            queue.push(next);
          });
      }
      ids
        .filter((id) => !localSeen.has(id))
        .sort((a, b) => degree(b) - degree(a) || a.localeCompare(b))
        .forEach((id) => order.push(id));

      const count = order.length;
      const cols = count <= 4 ? count : Math.min(5, Math.max(3, Math.ceil(Math.sqrt(count))));
      const rows = Math.ceil(count / cols);
      const cellW = 340;
      const cellH = 215;
      const compW = Math.max(1, cols) * cellW;
      const compH = Math.max(1, rows) * cellH;
      if (offsetX + compW > viewportWidth && offsetX > 340) {
        offsetX = 340;
        offsetY += rowHeight + 150;
        rowHeight = 0;
      }
      order.forEach((id, ix) => {
        const row = Math.floor(ix / cols);
        const colRaw = ix % cols;
        const col = row % 2 === 0 ? colRaw : cols - 1 - colRaw;
        const node = byId.get(id);
        if (!node) return;
        node.position(offsetX + col * cellW, offsetY + row * cellH);
      });
      offsetX += compW + 180;
      rowHeight = Math.max(rowHeight, compH);
    });

    refreshEdgeAnchors(g);
    return true;
  }

  function elkOptionsForLayoutMode(mode) {
    if (mode === 'elk-down') {
      return {
        'elk.algorithm': 'layered',
        'elk.direction': 'DOWN',
        'elk.edgeRouting': 'ORTHOGONAL',
        'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
        'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
        'elk.spacing.nodeNode': '96',
        'elk.spacing.edgeEdge': '38',
        'elk.spacing.edgeNode': '52',
        'elk.layered.spacing.nodeNodeBetweenLayers': '170',
        'elk.layered.spacing.edgeNodeBetweenLayers': '64',
        'elk.padding': '[top=90,left=90,bottom=90,right=90]',
      };
    }
    if (mode === 'elk-tree') {
      return {
        'elk.algorithm': 'mrtree',
        'elk.direction': 'RIGHT',
        'elk.spacing.nodeNode': '96',
        'elk.mrtree.spacing.nodeNode': '96',
        'elk.padding': '[top=90,left=90,bottom=90,right=90]',
      };
    }
    if (mode === 'elk-stress') {
      return {
        'elk.algorithm': 'stress',
        'elk.stress.desiredEdgeLength': '230',
        'elk.spacing.nodeNode': '120',
        'elk.spacing.edgeNode': '64',
        'elk.padding': '[top=90,left=90,bottom=90,right=90]',
      };
    }
    return {
      'elk.algorithm': 'layered',
      'elk.direction': 'RIGHT',
      'elk.edgeRouting': 'ORTHOGONAL',
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
      'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
      'elk.layered.layering.strategy': 'NETWORK_SIMPLEX',
      'elk.layered.mergeEdges': 'false',
      'elk.spacing.nodeNode': '110',
      'elk.spacing.edgeEdge': '44',
      'elk.spacing.edgeNode': '56',
      'elk.layered.spacing.nodeNodeBetweenLayers': '230',
      'elk.layered.spacing.edgeNodeBetweenLayers': '72',
      'elk.layered.spacing.edgeEdgeBetweenLayers': '44',
      'elk.padding': '[top=90,left=90,bottom=90,right=90]',
    };
  }

  async function layoutElkVariant(g, mode) {
    if (typeof ELK !== 'function') {
      console.warn('erd: elkjs bundle did not export a constructor');
      return false;
    }
    const elk = new ELK();
    const nodes = g.getNodes().filter((n) => n.shape === 'er-rect');
    const edges = g.getEdges();
    if (!nodes.length) return true;
    const idSet = new Set(nodes.map((n) => String(n.id)));
    const elkGraph = {
      id: 'root',
      layoutOptions: elkOptionsForLayoutMode(mode),
      children: [],
      edges: [],
    };
    nodes.forEach((n) => {
      const sz = n.size();
      elkGraph.children.push({ id: String(n.id), width: sz.width, height: sz.height });
    });
    edges.forEach((e) => {
      const s = typeof e.getSourceCell === 'function' ? e.getSourceCell() : null;
      const t = typeof e.getTargetCell === 'function' ? e.getTargetCell() : null;
      const sid = s && String(s.id);
      const tid = t && String(t.id);
      if (!sid || !tid || sid === tid || !idSet.has(sid) || !idSet.has(tid)) return;
      elkGraph.edges.push({ id: String(e.id), sources: [sid], targets: [tid] });
    });
    let layout;
    try {
      layout = await elk.layout(elkGraph);
    } catch (err) {
      console.warn(`erd: ${mode} layout failed`, err);
      return false;
    }
    const byId = new Map(nodes.map((n) => [String(n.id), n]));
    (layout.children ?? []).forEach((child) => {
      if (child.x == null || child.y == null) return;
      const n = byId.get(String(child.id));
      if (!n) return;
      n.position(child.x, child.y);
    });
    const edgeById = new Map(edges.map((e) => [String(e.id), e]));
    (layout.edges ?? []).forEach((le) => {
      const edge = edgeById.get(String(le.id));
      if (!edge) return;
      const firstSection = Array.isArray(le.sections) ? le.sections[0] : null;
      const bends = firstSection && Array.isArray(firstSection.bendPoints) ? firstSection.bendPoints : [];
      if (typeof edge.setVertices === 'function') edge.setVertices(bends.map((p) => ({ x: p.x, y: p.y })));
    });
    refreshEdgeAnchors(g, { clearVertices: false });
    return true;
  }

  async function layoutGraph(g) {
    if (activeLayoutMode === 'grid') return layoutGrid(g);
    return layoutElkVariant(g, activeLayoutMode);
  }

  function anchorForDelta(dx, dy, sourceSide) {
    if (Math.abs(dx) > Math.abs(dy)) {
      return dx >= 0 ? (sourceSide ? 'right' : 'left') : (sourceSide ? 'left' : 'right');
    }
    return dy >= 0 ? (sourceSide ? 'bottom' : 'top') : (sourceSide ? 'top' : 'bottom');
  }

  function refreshEdgeAnchors(g, opts = {}) {
    const clearVertices = opts.clearVertices !== false;
    g.getEdges().forEach((edge) => {
      const s = typeof edge.getSourceCell === 'function' ? edge.getSourceCell() : null;
      const t = typeof edge.getTargetCell === 'function' ? edge.getTargetCell() : null;
      if (!s || !t || s.shape !== 'er-rect' || t.shape !== 'er-rect') return;
      if (s.id === t.id) {
        if (typeof edge.setSource === 'function') edge.setSource({ cell: s.id, anchor: { name: 'right' } });
        if (typeof edge.setTarget === 'function') edge.setTarget({ cell: t.id, anchor: { name: 'top' } });
        if (typeof edge.setVertices === 'function') {
          const p = s.position();
          const sz = s.size();
          edge.setVertices([
            { x: p.x + sz.width + 70, y: p.y - 54 },
            { x: p.x + sz.width + 70, y: p.y + 20 },
          ]);
        }
        return;
      }
      const sb = s.getBBox();
      const tb = t.getBBox();
      const sp = { x: sb.x + sb.width / 2, y: sb.y + sb.height / 2 };
      const tp = { x: tb.x + tb.width / 2, y: tb.y + tb.height / 2 };
      const dx = tp.x - sp.x;
      const dy = tp.y - sp.y;
      if (typeof edge.setSource === 'function') edge.setSource({ cell: s.id, anchor: { name: anchorForDelta(dx, dy, true) } });
      if (typeof edge.setTarget === 'function') edge.setTarget({ cell: t.id, anchor: { name: anchorForDelta(dx, dy, false) } });
      if (clearVertices && typeof edge.setVertices === 'function') edge.setVertices([]);
    });
  }

  function layoutFallback(g) {
    const nodes = g.getNodes().filter((n) => n.shape === 'er-rect');
    const degree = new Map(nodes.map((n) => [String(n.id), 0]));
    g.getEdges().forEach((e) => {
      const s = typeof e.getSourceCell === 'function' ? e.getSourceCell() : null;
      const t = typeof e.getTargetCell === 'function' ? e.getTargetCell() : null;
      if (s && degree.has(String(s.id))) degree.set(String(s.id), degree.get(String(s.id)) + 1);
      if (t && degree.has(String(t.id))) degree.set(String(t.id), degree.get(String(t.id)) + 1);
    });
    const centerId =
      nodes.find((n) => /OrderEntity$/.test(String(n.id)))?.id ??
      nodes.slice().sort((a, b) => (degree.get(String(b.id)) ?? 0) - (degree.get(String(a.id)) ?? 0))[0]?.id ??
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
        n.position(420, 280);
        return;
      }
      const ring = Math.ceil(Math.sqrt(i));
      const angle = (i * 137.508 * Math.PI) / 180;
      const radiusX = 260 + ring * 50;
      const radiusY = 170 + ring * 34;
      n.position(420 + Math.cos(angle) * radiusX, 280 + Math.sin(angle) * radiusY);
    });
    refreshEdgeAnchors(g);
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
      router: { name: 'orth' },
      connector: { name: 'rounded', args: { radius: 4 } },
      validateMagnet() {
        return false;
      },
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

  let lodLevel = 'detailed';
  const erdTipEl = document.getElementById('erd-hover-tip');
  let erdTipHideTimer = null;
  const ERD_MAX_TABLE_CHARS = 22;
  const ERD_MAX_FIELD_CHARS = 14;
  const ERD_MAX_TYPE_CHARS = 9;

  function ellipTail(str, maxLen) {
    const t = String(str);
    if (!t.length || maxLen <= 0 || t.length <= maxLen) return t;
    if (maxLen < 2) return '\u2026';
    return t.slice(0, maxLen - 1) + '\u2026';
  }

  function hideErdTip() {
    if (erdTipHideTimer != null) {
      clearTimeout(erdTipHideTimer);
      erdTipHideTimer = null;
    }
    if (erdTipEl) {
      erdTipEl.style.display = 'none';
      erdTipEl.setAttribute('aria-hidden', 'true');
      erdTipEl.textContent = '';
    }
  }

  function showErdTip(clientX, clientY, txt) {
    if (!erdTipEl || !txt) return;
    hideErdTip();
    erdTipEl.textContent = txt;
    erdTipEl.style.display = 'block';
    erdTipEl.setAttribute('aria-hidden', 'false');
    const pw = typeof erdTipEl.offsetWidth === 'number' && erdTipEl.offsetWidth > 0 ? erdTipEl.offsetWidth : 360;
    const ph = typeof erdTipEl.offsetHeight === 'number' && erdTipEl.offsetHeight > 0 ? erdTipEl.offsetHeight : 44;
    const pad = 8;
    let x = clientX + 14;
    let y = clientY + 14;
    if (x + pw + pad > window.innerWidth) x = Math.max(pad, window.innerWidth - pw - pad);
    if (y + ph + pad > window.innerHeight) y = Math.max(pad, window.innerHeight - ph - pad);
    erdTipEl.style.left = `${x}px`;
    erdTipEl.style.top = `${y}px`;
  }

  function scheduleHideErdTip() {
    if (erdTipHideTimer != null) clearTimeout(erdTipHideTimer);
    erdTipHideTimer = setTimeout(() => {
      hideErdTip();
      erdTipHideTimer = null;
    }, 160);
  }

  function refreshErdLodAndText() {
    graph.batchUpdate(() => {
      graph.getNodes().forEach((node) => {
        if (node.shape !== 'er-rect') return;
        const dd = typeof node.getData === 'function' ? node.getData() : {};
        const panel =
          dd.payload_panel && typeof dd.payload_panel === 'object' && !Array.isArray(dd.payload_panel)
            ? dd.payload_panel
            : {};
        const tblFull = String(panel.label != null ? panel.label : '').trim();
        node.attr(
          'label/text',
          ellipTail(tblFull || String(node.attr('label/text') ?? ''), ERD_MAX_TABLE_CHARS),
        );
        const types =
          dd && Array.isArray(dd.lod_port_types)
            ? dd.lod_port_types
            : [];
        const names = Array.isArray(dd.lod_port_names) ? dd.lod_port_names : [];
        const roles = Array.isArray(dd.lod_port_roles) ? dd.lod_port_roles : [];
        const listPorts =
          typeof node.getPorts === 'function'
            ? node.getPorts().filter((p) => p.group === 'list')
            : [];
        listPorts.forEach((slot, i) => {
          const pid = slot?.id == null ? null : String(slot.id);
          if (!pid) return;
          const rawT = types[i] != null ? String(types[i]) : '';
          const rawN = names[i] != null ? String(names[i]) : '';
          const rawR = roles[i] != null ? String(roles[i]) : '';
          node.setPortProp(pid, 'attrs/portRoleLabel/text', rawR);
          node.setPortProp(
            pid,
            'attrs/portTypeLabel/text',
            lodLevel === 'overview' ? '' : ellipTail(rawT, ERD_MAX_TYPE_CHARS),
          );
          node.setPortProp(pid, 'attrs/portNameLabel/fontSize', lodLevel === 'overview' ? 9 : 10);
          node.setPortProp(pid, 'attrs/portNameLabel/text', ellipTail(rawN, ERD_MAX_FIELD_CHARS));
        });
        node.attr('label/fontSize', lodLevel === 'overview' ? 11 : 12);
      });
    });
  }

  function applyLodLevel(level, force) {
    if (!force && lodLevel === level) return;
    lodLevel = level;
    refreshErdLodAndText();
  }

  const erdDomainModel = __ERD_DOMAIN_MODEL_JSON__;
  const domainPicker = document.getElementById('domain-picker');
  const rendererPicker = document.getElementById('renderer-picker');
  const layoutPicker = document.getElementById('layout-picker');
  const mermaidContainer = document.getElementById('mermaid-container');
  const graphvizContainer = document.getElementById('graphviz-container');
  const d2Container = document.getElementById('d2-container');
  const d2SourceContainer = document.getElementById('d2-source-container');
  const rendererModes = [
    { id: 'x6', label: 'X6' },
    { id: 'mermaid', label: 'Mermaid' },
    { id: 'graphviz', label: 'Graphviz' },
    { id: 'd2', label: 'D2' },
    { id: 'd2-source', label: 'D2 source' },
  ];
  const layoutModes = [
    { id: 'grid', label: 'Grid' },
    { id: 'elk-right', label: 'ELK Right' },
    { id: 'elk-down', label: 'ELK Down' },
    { id: 'elk-tree', label: 'ELK Tree' },
    { id: 'elk-stress', label: 'ELK Stress' },
  ];
  const graphvizLayoutModes = [
    { id: 'dot-lr', label: 'Dot LR' },
    { id: 'dot-tb', label: 'Dot Down' },
    { id: 'neato', label: 'Neato' },
    { id: 'fdp', label: 'FDP' },
    { id: 'sfdp', label: 'SFDP' },
    { id: 'circo', label: 'Circo' },
    { id: 'twopi', label: 'Twopi' },
    { id: 'osage', label: 'Osage' },
  ];
  let activeRendererMode = 'x6';
  let activeLayoutMode = 'grid';
  let activeGraphvizLayoutMode = 'dot-lr';
  const domainList = Array.isArray(erdDomainModel?.domains) ? erdDomainModel.domains : [];
  const documentMap =
    erdDomainModel && typeof erdDomainModel.documents === 'object'
      ? erdDomainModel.documents
      : {};
  let activeDomainId =
    typeof erdDomainModel?.initialDomainId === 'string'
      ? erdDomainModel.initialDomainId
      : domainList[0]?.id ?? 'default';

  function activeDocument() {
    const doc = documentMap[activeDomainId];
    if (doc && Array.isArray(doc.cells)) return doc;
    return { cells: [] };
  }

  function erdCells(doc) {
    return Array.isArray(doc?.cells) ? doc.cells : [];
  }

  function erdNodes(doc) {
    return erdCells(doc).filter((cell) => cell?.shape === 'er-rect');
  }

  function erdEdges(doc) {
    return erdCells(doc).filter((cell) => cell?.shape === 'edge');
  }

  function sourceCellId(edge) {
    return typeof edge?.source === 'object' ? String(edge.source.cell ?? '') : String(edge?.source ?? '');
  }

  function targetCellId(edge) {
    return typeof edge?.target === 'object' ? String(edge.target.cell ?? '') : String(edge?.target ?? '');
  }

  function stableDiagramIds(nodes) {
    const used = new Set();
    const out = new Map();
    nodes.forEach((node, ix) => {
      const panel = node?.data?.payload_panel ?? {};
      const label = String(panel.label ?? node?.attrs?.label?.text ?? node?.id ?? `Entity${ix + 1}`);
      let base = label.replace(/[^A-Za-z0-9_]/g, '_').replace(/^_+|_+$/g, '');
      if (!base) base = `Entity${ix + 1}`;
      if (/^[0-9]/.test(base)) base = `E_${base}`;
      let candidate = base;
      let suffix = 2;
      while (used.has(candidate)) {
        candidate = `${base}_${suffix}`;
        suffix += 1;
      }
      used.add(candidate);
      out.set(String(node.id), candidate);
    });
    return out;
  }

  function simpleTypeForDiagram(typeName) {
    const raw = String(typeName ?? '').trim();
    if (!raw) return 'string';
    const lowered = raw.toLowerCase();
    if (lowered.includes('int')) return 'int';
    if (lowered.includes('float') || lowered.includes('decimal') || lowered.includes('money')) return 'float';
    if (lowered.includes('bool')) return 'boolean';
    if (lowered.includes('date') || lowered.includes('time')) return 'datetime';
    return raw.replace(/[^A-Za-z0-9_]/g, '_').slice(0, 48) || 'string';
  }

  function dotId(id) {
    return String(id ?? '').replace(/[^A-Za-z0-9_]/g, '_') || 'Entity';
  }

  function dotString(value) {
    return JSON.stringify(String(value ?? ''));
  }

  function d2Id(id) {
    return dotId(id);
  }

  function d2FieldName(value, fallback) {
    const raw = String(value ?? '').replace(/[^A-Za-z0-9_]/g, '_').replace(/^_+|_+$/g, '');
    const name = raw || fallback || 'field';
    return /^[0-9]/.test(name) ? `f_${name}` : name;
  }

  function d2Type(typeName) {
    const raw = String(typeName ?? '').trim();
    if (!raw) return 'string';
    if (raw.includes('FK ->')) return 'string';
    return simpleTypeForDiagram(raw);
  }

  function d2Constraint(role) {
    const raw = String(role ?? '');
    const constraints = [];
    if (raw.includes('PK')) constraints.push('PK');
    if (raw.includes('FK')) constraints.push('FK');
    return constraints.join(' ');
  }

  function dotHtml(value) {
    return esc(String(value ?? '')).replace(/"/g, '&quot;');
  }

  function edgePanel(edge) {
    const panel = edge?.data?.payload_panel;
    return panel && typeof panel === 'object' && !Array.isArray(panel) ? panel : {};
  }

  function mermaidLeftCardinality(cardinality) {
    return {
      one: '||',
      zero_one: 'o|',
      one_many: '}|',
      zero_many: '}o',
    }[String(cardinality ?? '')] ?? '||';
  }

  function mermaidRightCardinality(cardinality) {
    return {
      one: '||',
      zero_one: '|o',
      one_many: '|{',
      zero_many: 'o{',
    }[String(cardinality ?? '')] ?? '||';
  }

  function mermaidFieldKey(role) {
    const raw = String(role ?? '');
    if (raw.includes('PK')) return 'PK';
    if (raw.includes('FK')) return 'FK';
    return '';
  }

  function buildMermaidErd(doc) {
    const nodes = erdNodes(doc);
    const ids = stableDiagramIds(nodes);
    const lines = ['erDiagram'];
    nodes.forEach((node) => {
      const entityId = ids.get(String(node.id));
      const names = Array.isArray(node?.data?.lod_port_names) ? node.data.lod_port_names : [];
      const types = Array.isArray(node?.data?.lod_port_types) ? node.data.lod_port_types : [];
      const roles = Array.isArray(node?.data?.lod_port_roles) ? node.data.lod_port_roles : [];
      lines.push(`  ${entityId} {`);
      if (!names.length) lines.push('    string id PK');
      names.forEach((name, ix) => {
        const typ = simpleTypeForDiagram(types[ix]);
        const field = String(name ?? `field_${ix + 1}`).replace(/[^A-Za-z0-9_]/g, '_') || `field_${ix + 1}`;
        const role = mermaidFieldKey(roles[ix]);
        lines.push(`    ${typ} ${field}${role ? ` ${role}` : ''}`);
      });
      lines.push('  }');
    });
    erdEdges(doc).forEach((edge) => {
      const src = ids.get(sourceCellId(edge));
      const tgt = ids.get(targetCellId(edge));
      if (!src || !tgt) return;
      const panel = edgePanel(edge);
      const left = mermaidLeftCardinality(panel.source_cardinality);
      const right = mermaidRightCardinality(panel.target_cardinality);
      const label = String(panel.source_field || panel.label || panel.relationship_kind || 'rel')
        .replace(/"/g, "'")
        .replace(/\\s+/g, ' ')
        .trim();
      lines.push(`  ${src} ${left}--${right} ${tgt} : "${label || 'rel'}"`);
    });
    return lines.join('\\n');
  }

  function buildD2Source(doc) {
    const nodes = erdNodes(doc);
    const ids = stableDiagramIds(nodes);
    const fieldMap = new Map();
    const lines = ['direction: right', ''];
    nodes.forEach((node) => {
      const entityId = d2Id(ids.get(String(node.id)));
      const names = Array.isArray(node?.data?.lod_port_names) ? node.data.lod_port_names : [];
      const types = Array.isArray(node?.data?.lod_port_types) ? node.data.lod_port_types : [];
      const roles = Array.isArray(node?.data?.lod_port_roles) ? node.data.lod_port_roles : [];
      const localFields = new Map();
      lines.push(`${entityId}: {`);
      lines.push('  shape: sql_table');
      if (!names.length) lines.push('  id: string PK');
      names.forEach((name, ix) => {
        const field = d2FieldName(name, `field_${ix + 1}`);
        const typ = d2Type(types[ix]);
        const constraint = d2Constraint(roles[ix]);
        localFields.set(String(name ?? ''), field);
        lines.push(`  ${field}: ${typ}${constraint ? ` ${constraint}` : ''}`);
      });
      fieldMap.set(String(node.id), localFields);
      lines.push('}');
      lines.push('');
    });
    erdEdges(doc).forEach((edge) => {
      const srcRaw = sourceCellId(edge);
      const tgtRaw = targetCellId(edge);
      const src = ids.get(srcRaw);
      const tgt = ids.get(tgtRaw);
      if (!src || !tgt) return;
      const panel = edgePanel(edge);
      const sourceField = String(panel.source_field || '');
      const sourceD2Field =
        fieldMap.get(srcRaw)?.get(sourceField) ?? d2FieldName(sourceField || 'id', 'id');
      lines.push(`${d2Id(src)}.${sourceD2Field} -> ${d2Id(tgt)}.id`);
    });
    return lines.join('\\n');
  }

  function graphvizCardinalityLabel(cardinality) {
    return {
      one: '||',
      zero_one: 'o|',
      one_many: '|<',
      zero_many: 'o<',
    }[String(cardinality ?? '')] ?? '';
  }

  function graphvizEngineForLayoutMode(mode) {
    return {
      'dot-lr': 'dot',
      'dot-tb': 'dot',
      neato: 'neato',
      fdp: 'fdp',
      sfdp: 'sfdp',
      circo: 'circo',
      twopi: 'twopi',
      osage: 'osage',
    }[mode] ?? 'dot';
  }

  function graphvizGraphAttrs(mode) {
    if (mode === 'dot-tb') {
      return 'rankdir=TB, bgcolor="transparent", splines=ortho, nodesep=0.8, ranksep=1.25, pad=0.35';
    }
    if (mode === 'neato') {
      return 'bgcolor="transparent", overlap=false, splines=true, sep="+48", model=shortpath, pad=0.35';
    }
    if (mode === 'fdp') {
      return 'bgcolor="transparent", overlap=false, splines=true, K=1.2, sep="+56", pad=0.35';
    }
    if (mode === 'sfdp') {
      return 'bgcolor="transparent", overlap=prism, splines=true, K=1.4, sep="+64", pad=0.35, outputorder=edgesfirst';
    }
    if (mode === 'circo') {
      return 'bgcolor="transparent", overlap=false, splines=true, oneblock=true, mindist=1.3, pad=0.35';
    }
    if (mode === 'twopi') {
      return 'bgcolor="transparent", overlap=false, splines=true, ranksep=1.8, pad=0.35';
    }
    if (mode === 'osage') {
      return 'bgcolor="transparent", overlap=false, splines=ortho, pack=true, packmode=clust, pad=0.35';
    }
    return 'rankdir=LR, bgcolor="transparent", overlap=false, splines=ortho, nodesep=0.8, ranksep=1.4, pad=0.35';
  }

  function buildGraphvizDot(doc) {
    const nodes = erdNodes(doc);
    const ids = stableDiagramIds(nodes);
    const lines = [
      'digraph ERD {',
      `  graph [${graphvizGraphAttrs(activeGraphvizLayoutMode)}];`,
      '  node [shape=plain, fontname="Arial"];',
      '  edge [fontname="Arial", fontsize=10, color="#374151", arrowsize=0.7, dir=none];',
      '',
    ];
    nodes.forEach((node) => {
      const entityId = dotId(ids.get(String(node.id)));
      const panel = node?.data?.payload_panel ?? {};
      const label = dotHtml(panel.label ?? entityId);
      const names = Array.isArray(node?.data?.lod_port_names) ? node.data.lod_port_names : [];
      const types = Array.isArray(node?.data?.lod_port_types) ? node.data.lod_port_types : [];
      const roles = Array.isArray(node?.data?.lod_port_roles) ? node.data.lod_port_roles : [];
      lines.push(`  ${entityId} [label=<`);
      lines.push('    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5" COLOR="#1f2937">');
      lines.push(`      <TR><TD BGCOLOR="#e5e7eb" COLSPAN="3"><B>${label}</B></TD></TR>`);
      if (!names.length) {
        lines.push('      <TR><TD><B>PK</B></TD><TD ALIGN="LEFT">id</TD><TD ALIGN="LEFT">str</TD></TR>');
      }
      names.forEach((name, ix) => {
        const role = dotHtml(roles[ix] ?? '');
        const fname = dotHtml(name ?? `field_${ix + 1}`);
        const typ = dotHtml(types[ix] ?? '');
        const roleCell = role ? `<B>${role}</B>` : '';
        lines.push(`      <TR><TD>${roleCell}</TD><TD ALIGN="LEFT">${fname}</TD><TD ALIGN="LEFT">${typ}</TD></TR>`);
      });
      lines.push('    </TABLE>');
      lines.push('  >];');
      lines.push('');
    });
    erdEdges(doc).forEach((edge) => {
      const src = ids.get(sourceCellId(edge));
      const tgt = ids.get(targetCellId(edge));
      if (!src || !tgt) return;
      const panel = edgePanel(edge);
      const label = String(panel.source_field || panel.label || panel.relationship_kind || 'rel').trim();
      const tail = graphvizCardinalityLabel(panel.source_cardinality);
      const head = graphvizCardinalityLabel(panel.target_cardinality);
      lines.push(
        `  ${dotId(src)} -> ${dotId(tgt)} [label=${dotString(label)}, taillabel=${dotString(tail)}, headlabel=${dotString(head)}];`,
      );
    });
    lines.push('}');
    return lines.join('\\n');
  }

  async function ensureMermaidApi() {
    if (mermaidApi) return mermaidApi;
    const mod = await import(__MERMAID_MODULE_IMPORT__);
    mermaidApi = mod.default ?? mod;
    if (typeof mermaidApi.initialize === 'function') {
      mermaidApi.initialize({
        startOnLoad: false,
        securityLevel: 'loose',
        theme: 'base',
        er: { useMaxWidth: false },
      });
    }
    return mermaidApi;
  }

  function withTimeout(promise, label, ms = 20000) {
    let timer = null;
    const timeout = new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(`${label} timed out after ${ms}ms`)), ms);
    });
    return Promise.race([promise, timeout]).finally(() => {
      if (timer != null) clearTimeout(timer);
    });
  }

  async function ensureGraphvizApi() {
    if (graphvizApi) return graphvizApi;
    const mod = await withTimeout(import(__GRAPHVIZ_MODULE_IMPORT__), 'Graphviz module import');
    const Graphviz = mod.Graphviz ?? mod.default?.Graphviz ?? mod.default;
    if (!Graphviz || typeof Graphviz.load !== 'function') {
      throw new Error('Graphviz WASM module did not expose Graphviz.load()');
    }
    graphvizApi = await Graphviz.load();
    return graphvizApi;
  }

  async function ensureD2Api() {
    if (d2Api) return d2Api;
    const mod = await withTimeout(import(__D2_MODULE_IMPORT__), 'D2 module import');
    const D2 = mod.D2 ?? mod.default?.D2 ?? mod.default;
    if (!D2) throw new Error('D2 module did not expose D2');
    d2Api = new D2();
    return d2Api;
  }

  async function renderMermaidDomain(doc) {
    if (!mermaidContainer) return;
    mermaidContainer.innerHTML = '<div style="font-size:12px;color:#64748b">Rendering Mermaid ERD...</div>';
    const source = buildMermaidErd(doc);
    try {
      const api = await ensureMermaidApi();
      const renderId = `mermaid-erd-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
      const rendered = await api.render(renderId, source);
      mermaidContainer.innerHTML = rendered.svg ?? String(rendered);
    } catch (err) {
      console.warn('erd: mermaid renderer failed', err);
      mermaidContainer.innerHTML =
        '<pre style="white-space:pre-wrap;color:#991b1b;background:#fff;border:1px solid #fecaca;border-radius:8px;padding:12px">' +
        esc(String(err?.message ?? err)) +
        '\\n\\n' +
        esc(source) +
        '</pre>';
    }
  }

  function renderD2SourceDomain(doc) {
    if (!d2SourceContainer) return;
    d2SourceContainer.textContent = buildD2Source(doc);
  }

  async function renderD2Domain(doc) {
    if (!d2Container) return;
    d2Container.innerHTML =
      '<div style="font-size:12px;color:#64748b">Rendering D2 ERD... If the browser WASM worker stalls, this will fall back automatically.</div>';
    const source = buildD2Source(doc);
    try {
      const api = await ensureD2Api();
      const result = await withTimeout(api.compile(source, { layout: 'dagre' }), 'D2 compile');
      const svg = await withTimeout(
        api.render(result.diagram, {
          ...(result.renderOptions ?? {}),
          pad: 80,
          scale: 1,
          noXMLTag: true,
        }),
        'D2 render',
      );
      d2Container.innerHTML = svg;
    } catch (err) {
      console.warn('erd: d2 renderer failed', err);
      d2Container.innerHTML =
        '<pre style="white-space:pre-wrap;color:#991b1b;background:#fff;border:1px solid #fecaca;border-radius:8px;padding:12px">' +
        'D2 browser renderer failed or timed out. The generated D2 source is shown below.\\n\\n' +
        esc(String(err?.message ?? err)) +
        '\\n\\n' +
        esc(source) +
        '</pre>';
    }
  }

  async function renderGraphvizDomain(doc) {
    if (!graphvizContainer) return;
    const engine = graphvizEngineForLayoutMode(activeGraphvizLayoutMode);
    const mode = graphvizLayoutModes.find((item) => item.id === activeGraphvizLayoutMode);
    graphvizContainer.innerHTML =
      '<div style="font-size:12px;color:#64748b">Rendering Graphviz ERD with ' +
      esc(mode?.label ?? engine) +
      '...</div>';
    const source = buildGraphvizDot(doc);
    try {
      const api = await ensureGraphvizApi();
      const svg = await withTimeout(
        Promise.resolve(
          typeof api.layout === 'function'
            ? api.layout(source, 'svg', engine)
            : typeof api.dot === 'function'
              ? api.dot(source)
              : '',
        ),
        `Graphviz ${engine}`,
      );
      if (!svg) throw new Error('Graphviz renderer returned no SVG');
      graphvizContainer.innerHTML = svg;
    } catch (err) {
      console.warn('erd: graphviz renderer failed', err);
      graphvizContainer.innerHTML =
        '<pre style="white-space:pre-wrap;color:#991b1b;background:#fff;border:1px solid #fecaca;border-radius:8px;padding:12px">' +
        esc(String(err?.message ?? err)) +
        '\\n\\n' +
        esc(source) +
        '</pre>';
    }
  }

  async function renderActiveDomain() {
    hideErdTip();
    const doc = activeDocument();
    const isX6 = activeRendererMode === 'x6';
    container.style.display = isX6 ? 'block' : 'none';
    if (mermaidContainer) mermaidContainer.style.display = activeRendererMode === 'mermaid' ? 'block' : 'none';
    if (graphvizContainer) graphvizContainer.style.display = activeRendererMode === 'graphviz' ? 'block' : 'none';
    if (d2Container) d2Container.style.display = activeRendererMode === 'd2' ? 'block' : 'none';
    if (d2SourceContainer) d2SourceContainer.style.display = activeRendererMode === 'd2-source' ? 'block' : 'none';
    if (layoutPicker) layoutPicker.style.display = isX6 || activeRendererMode === 'graphviz' ? 'flex' : 'none';
    if (!isX6) {
      if (typeof graph.resetCells === 'function') graph.resetCells([]);
      if (activeRendererMode === 'mermaid') await renderMermaidDomain(doc);
      if (activeRendererMode === 'graphviz') await renderGraphvizDomain(doc);
      if (activeRendererMode === 'd2') await renderD2Domain(doc);
      if (activeRendererMode === 'd2-source') renderD2SourceDomain(doc);
      syncZoom();
      return;
    }
    if (typeof graph.resetCells === 'function') graph.resetCells([]);
    graph.fromJSON(doc);
    const didLayout = await layoutGraph(graph);
    if (!didLayout) layoutFallback(graph);
    graph.zoomToFit({ padding: { top: 72, right: 260, bottom: 80, left: 310 }, maxScale: 1.0 });
    syncZoom();
    applyLodLevel(currentScale() <= 0.65 ? 'overview' : 'detailed', true);
  }

  function renderLayoutPicker() {
    if (!layoutPicker) return;
    const modes =
      activeRendererMode === 'graphviz'
        ? graphvizLayoutModes
        : activeRendererMode === 'x6'
          ? layoutModes
          : [];
    layoutPicker.style.display = modes.length ? 'flex' : 'none';
    layoutPicker.innerHTML =
      '<div class="legend-title">Layout</div>' +
      modes
        .map((mode) => {
          const activeId = activeRendererMode === 'graphviz' ? activeGraphvizLayoutMode : activeLayoutMode;
          const activeCls = mode.id === activeId ? ' is-active' : '';
          return (
            '<button type="button" class="layout-row' +
            activeCls +
            '" data-layout-id="' +
            mode.id +
            '"><span>' +
            esc(mode.label) +
            '</span></button>'
          );
        })
        .join('');
  }

  function renderRendererPicker() {
    if (!rendererPicker) return;
    rendererPicker.style.display = 'flex';
    rendererPicker.innerHTML =
      '<div class="legend-title">Renderer</div>' +
      rendererModes
        .map((mode) => {
          const activeCls = mode.id === activeRendererMode ? ' is-active' : '';
          return (
            '<button type="button" class="renderer-row' +
            activeCls +
            '" data-renderer-id="' +
            mode.id +
            '"><span>' +
            esc(mode.label) +
            '</span></button>'
          );
        })
        .join('');
  }

  function renderDomainPicker() {
    if (!domainPicker) return;
    if (!domainList.length || domainList.length <= 1) {
      domainPicker.style.display = 'none';
      return;
    }
    domainPicker.style.display = 'flex';
    domainPicker.innerHTML =
      '<div class="legend-title">Domains</div>' +
      domainList
        .map((dom) => {
          const did = String(dom.id ?? '');
          const label = String(dom.label ?? did);
          const iconSrc = dom.iconSrc != null ? String(dom.iconSrc) : '';
          const activeCls = did === activeDomainId ? ' is-active' : '';
          const icon = iconSrc
            ? '<img class="legend-icon" src="' + iconSrc + '" width="20" height="20" alt="" />'
            : '';
          return (
            '<button type="button" class="domain-row' +
            activeCls +
            '" data-domain-id="' +
            did +
            '">' +
            icon +
            '<span>' +
            esc(label) +
            '</span></button>'
          );
        })
        .join('');
  }

  const detailShell = document.getElementById('node-detail-shell');
  const detailBody = document.getElementById('node-detail-body');

  function closeDetail() {
    if (detailShell) {
      detailShell.classList.remove('is-open');
      detailShell.setAttribute('aria-hidden', 'true');
    }
    if (detailBody) detailBody.innerHTML = '';
  }

  domainPicker?.addEventListener('click', async (evt) => {
    const btn = evt.target.closest('.domain-row');
    if (!btn || !domainPicker.contains(btn)) return;
    const did = btn.getAttribute('data-domain-id');
    if (!did || did === activeDomainId || !documentMap[did]) return;
    activeDomainId = did;
    closeDetail();
    hideErdTip();
    renderDomainPicker();
    await renderActiveDomain();
  });

  rendererPicker?.addEventListener('click', async (evt) => {
    const btn = evt.target.closest('.renderer-row');
    if (!btn || !rendererPicker.contains(btn)) return;
    const rid = btn.getAttribute('data-renderer-id');
    if (!rid || rid === activeRendererMode || !rendererModes.some((mode) => mode.id === rid)) return;
    activeRendererMode = rid;
    closeDetail();
    hideErdTip();
    renderRendererPicker();
    await renderActiveDomain();
    renderLayoutPicker();
  });

  layoutPicker?.addEventListener('click', async (evt) => {
    const btn = evt.target.closest('.layout-row');
    if (!btn || !layoutPicker.contains(btn)) return;
    const lid = btn.getAttribute('data-layout-id');
    if (activeRendererMode === 'graphviz') {
      if (!lid || lid === activeGraphvizLayoutMode || !graphvizLayoutModes.some((mode) => mode.id === lid)) return;
      activeGraphvizLayoutMode = lid;
    } else {
      if (!lid || lid === activeLayoutMode || !layoutModes.some((mode) => mode.id === lid)) return;
      activeLayoutMode = lid;
    }
    closeDetail();
    hideErdTip();
    await renderActiveDomain();
    renderLayoutPicker();
  });

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

  graph.on('blank:click', () => {
    closeDetail();
    hideErdTip();
  });

  graph.on('blank:mousemove', hideErdTip);

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

  graph.on('node:port:mouseenter', ({ e, node, port }) => {
    if (erdTipHideTimer != null) {
      clearTimeout(erdTipHideTimer);
      erdTipHideTimer = null;
    }
    const pid = port?.id != null ? String(port.id) : '';
    if (!node || node.shape !== 'er-rect' || !pid) return;
    const dd = typeof node.getData === 'function' ? node.getData() : {};
    const names = Array.isArray(dd.lod_port_names) ? dd.lod_port_names : [];
    const types = Array.isArray(dd.lod_port_types) ? dd.lod_port_types : [];
    const roles = Array.isArray(dd.lod_port_roles) ? dd.lod_port_roles : [];
    const listPorts =
      typeof node.getPorts === 'function'
        ? node.getPorts().filter((p) => p.group === 'list')
        : [];
    const ix = listPorts.findIndex((p) => String(p.id) === pid);
    if (ix < 0) return;
    const fullN = names[ix] != null ? String(names[ix]) : '';
    const fullT = types[ix] != null ? String(types[ix]) : '';
    const fullR = roles[ix] != null ? String(roles[ix]) : '';
    const tip = [fullR, fullN, fullT].filter(Boolean).join('\\n');
    if (tip) showErdTip(e.clientX, e.clientY, tip);
  });

  graph.on('node:port:mouseleave', () => {
    scheduleHideErdTip();
  });

  graph.on('node:mousemove', ({ node, e }) => {
    if (!node || node.shape !== 'er-rect') return;
    const t = e.target;
    if (!(t instanceof Element)) return;
    if (t.closest && t.closest('[class*="x6-port"]')) return;
    const dd = typeof node.getData === 'function' ? node.getData() : {};
    const panel =
      dd.payload_panel && typeof dd.payload_panel === 'object' && !Array.isArray(dd.payload_panel)
        ? dd.payload_panel
        : {};
    const full = String(panel.label != null ? panel.label : '').trim();
    if (!full || full.length <= ERD_MAX_TABLE_CHARS) return;
    showErdTip(e.clientX, e.clientY, full);
  });

  graph.on('node:mouseleave', () => {
    scheduleHideErdTip();
  });

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

  graph.on('translate', () => {
    syncZoom();
    hideErdTip();
  });

  let wheelAccum = 0;
  let wheelRaf = null;
  const flushWheelZoom = () => {
    wheelRaf = null;
    if (activeRendererMode !== 'x6') {
      wheelAccum = 0;
      return;
    }
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
    if (activeRendererMode !== 'x6') return;
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
    if (activeRendererMode !== 'x6') return;
    graph.zoomToFit({ padding: { top: 72, right: 260, bottom: 80, left: 310 }, maxScale: 1.0 });
    syncZoom();
    applyLodLevel(currentScale() <= 0.65 ? 'overview' : 'detailed', true);
  });

  renderDomainPicker();
  renderRendererPicker();
  renderLayoutPicker();
  await renderActiveDomain();
  syncZoom();

  window.addEventListener('resize', () => {
    if (activeRendererMode !== 'x6') return;
    graph.resize(container.clientWidth, container.clientHeight);
    syncZoom();
  });
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

    model_json = json.dumps(
        {
            "domains": [{"id": "default", "label": "Default", "iconSrc": ""}],
            "documents": {"default": payload},
            "initialDomainId": "default",
        },
        ensure_ascii=False,
    )
    js_import = json.dumps(X6_MODULE_URL)
    elk_imp = json.dumps(ELK_MODULE_URL)
    mermaid_imp = json.dumps(MERMAID_MODULE_URL)
    graphviz_imp = json.dumps(GRAPHVIZ_MODULE_URL)
    d2_imp = json.dumps(D2_MODULE_URL)
    bootstrap = (
        _ERD_BOOTSTRAP_JS.replace("__X6_MODULE_IMPORT__", js_import)
        .replace("__ELK_MODULE_IMPORT__", elk_imp)
        .replace("__MERMAID_MODULE_IMPORT__", mermaid_imp)
        .replace("__GRAPHVIZ_MODULE_IMPORT__", graphviz_imp)
        .replace("__D2_MODULE_IMPORT__", d2_imp)
        .replace("__ERD_DOMAIN_MODEL_JSON__", model_json)
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
    domain_cls: type[Any] | None,
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
    application modules registering entities/actions are imported). When ``domain_cls`` is set,
    it is used as initial selection in the right-side domain picker.

    AI-CORE-BEGIN
    PURPOSE: Convenience path from built interchange graph → X6 ER export by reading coordinator graph at call time.
    INPUT: Coordinator after ``build``; ``domain_cls`` ``BaseDomain`` subclass.
    OUTPUT: Same as :func:`write_erd_html`; document is serialized directly from current graph metadata.
    AI-CORE-END
    """
    from action_machine.domain.base_domain import BaseDomain
    from action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
    from graph.node_graph_coordinator import NodeGraphCoordinator
    from maxitor.visualizer.erd_visualizer.erd_graph_data import erd_document_from_coordinator_graph
    from maxitor.visualizer.graph_visualizer.visualizer_icons import (
        svg_data_uri_for_graph_node_icon,
    )

    if not isinstance(coordinator, NodeGraphCoordinator):
        msg = "coordinator must be a built NodeGraphCoordinator"
        raise TypeError(msg)
    if domain_cls is not None and (not isinstance(domain_cls, type) or not issubclass(domain_cls, BaseDomain)):
        msg = "domain_cls must be a BaseDomain subclass"
        raise TypeError(msg)

    domain_nodes = [
        n
        for n in coordinator.get_all_nodes()
        if isinstance(n, DomainGraphNode) and isinstance(n.node_obj, type) and issubclass(n.node_obj, BaseDomain)
    ]
    domain_nodes = sorted(domain_nodes, key=lambda n: str(n.properties.get("name", n.label)).lower())
    domain_documents: dict[str, dict[str, Any]] = {}
    domain_items: list[dict[str, str]] = []
    initial_domain_id: str | None = None
    for dnode in domain_nodes:
        dcls = dnode.node_obj
        doc = erd_document_from_coordinator_graph(coordinator, dcls)
        domain_id = dnode.node_id
        domain_documents[domain_id] = doc
        domain_items.append(
            {
                "id": domain_id,
                "label": str(dnode.properties.get("name", dnode.label)),
                "iconSrc": svg_data_uri_for_graph_node_icon("#377EB8", DomainGraphNode.NODE_TYPE),
            },
        )
        if domain_cls is not None and dcls is domain_cls:
            initial_domain_id = domain_id

    if not domain_items:
        if domain_cls is None:
            msg = "No Domain nodes found in coordinator graph."
            raise LookupError(msg)
        doc = erd_document_from_coordinator_graph(coordinator, domain_cls)
        return write_erd_html(doc, output_path=output_path, title=title, width=width, height=height)

    if initial_domain_id is None:
        initial_domain_id = domain_items[0]["id"]
    model_json = json.dumps(
        {
            "domains": domain_items,
            "documents": domain_documents,
            "initialDomainId": initial_domain_id,
        },
        ensure_ascii=False,
    )
    js_import = json.dumps(X6_MODULE_URL)
    elk_imp = json.dumps(ELK_MODULE_URL)
    mermaid_imp = json.dumps(MERMAID_MODULE_URL)
    graphviz_imp = json.dumps(GRAPHVIZ_MODULE_URL)
    d2_imp = json.dumps(D2_MODULE_URL)
    bootstrap = (
        _ERD_BOOTSTRAP_JS.replace("__X6_MODULE_IMPORT__", js_import)
        .replace("__ELK_MODULE_IMPORT__", elk_imp)
        .replace("__MERMAID_MODULE_IMPORT__", mermaid_imp)
        .replace("__GRAPHVIZ_MODULE_IMPORT__", graphviz_imp)
        .replace("__D2_MODULE_IMPORT__", d2_imp)
        .replace("__ERD_DOMAIN_MODEL_JSON__", model_json)
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
