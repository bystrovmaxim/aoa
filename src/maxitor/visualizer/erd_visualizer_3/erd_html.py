"""
Standalone ERD HTML export.

Renderers: X6 (interactive), Mermaid, Graphviz SVG, D2, D2 source,
           Graphviz Interactive (SVG + overlays), ELK Canvas (draggable tables + SVG edges).

X6 layout engines: ELK Right/Down/Tree/Stress/Force, Dagre LR/TB,
                   Grid, Graphviz-backed X6 (Dot LR/TB, Neato, FDP, SFDP, Circo, Twopi).
"""

from __future__ import annotations

import copy
import json
from functools import cache
from html import escape as html_escape
from pathlib import Path

X6_MODULE_URL      = "https://esm.sh/@antv/x6@2.19.2"
ELK_MODULE_URL     = "https://esm.sh/elkjs@0.11.1"
DAGRE_MODULE_URL   = "https://esm.sh/@dagrejs/dagre@1.1.4"
MERMAID_MODULE_URL = "https://esm.sh/mermaid@11.12.0"
GRAPHVIZ_MODULE_URL = "https://esm.sh/@hpcc-js/wasm-graphviz@1.21.5"
D2_MODULE_URL      = "https://esm.sh/@terrastruct/d2@0.1.33"

_PACKAGE_DIR   = Path(__file__).resolve().parent
_TEMPLATE_HTML = _PACKAGE_DIR / "template.html"


def _default_archive_logs_dir() -> Path:
    return Path("/Users/bystrovmaxim/PythonDev/aoa/archive/logs")


DEFAULT_ERD_HTML_PATH = _default_archive_logs_dir() / "erd.html"


@cache
def _template_raw() -> str:
    return _TEMPLATE_HTML.read_text(encoding="utf-8")


def _load_erd_document_builder():
    """Load the sibling graph-data builder for package and direct directory execution."""
    try:
        from .erd_graph_data import erd_document_from_coordinator_graph
    except ImportError:
        from erd_graph_data import erd_document_from_coordinator_graph

    return erd_document_from_coordinator_graph


_ERD_BOOTSTRAP_JS = """
(async function () {

  /* ── imports ── */
  const { Graph, Shape } = await import(/*X6*/"__X6_URL__");

  let ELK = null;
  try { const m = await import(/*ELK*/"__ELK_URL__"); ELK = m.default ?? m.ELK ?? m; }
  catch (e) { console.warn('erd: elkjs', e); }

  let dagre = null;
  try { const m = await import(/*DAGRE*/"__DAGRE_URL__"); dagre = m.default ?? m; }
  catch (e) { console.warn('erd: dagre', e); }

  let gvApi = null;
  let mmApi = null;
  let d2Api = null;

  /* ── constants ── */
  const LINE_H  = 24;
  const NODE_W  = 200;
  const ROLE_W  = 46;
  const TYPE_X  = 136;
  const MIN_SC  = 0.15;
  const MAX_SC  = 3.0;
  const WHL_K   = 0.0042;
  const IN2PX   = 72;

  /* ── X6 er-rect node ── */
  Graph.registerNode('er-rect', {
    inherit: 'rect',
    markup: [
      { tagName: 'rect', selector: 'body'   },
      { tagName: 'rect', selector: 'header' },
      { tagName: 'text', selector: 'label'  },
    ],
    attrs: {
      body:   { strokeWidth: 1.5, stroke: '#374151', fill: '#f9fafb', rx: 4, ry: 4 },
      header: { refWidth: '100%', height: LINE_H, fill: '#1e3a5f', rx: 4, ry: 4 },
      label:  {
        refX: NODE_W / 2, refY: LINE_H / 2,
        textAnchor: 'middle', textVerticalAnchor: 'middle',
        fontWeight: '600', fill: '#ffffff', fontSize: 12,
      },
    },
    ports: {
      groups: {
        list: {
          markup: [
            { tagName: 'rect', selector: 'portBody'      },
            { tagName: 'line', selector: 'roleDivider'   },
            { tagName: 'text', selector: 'portRoleLabel' },
            { tagName: 'text', selector: 'portNameLabel' },
            { tagName: 'text', selector: 'portTypeLabel' },
          ],
          attrs: {
            portBody:      { width: NODE_W, height: LINE_H, strokeWidth: 0.5,
                             stroke: '#d1d5db', fill: '#f9fafb', magnet: false },
            roleDivider:   { x1: ROLE_W, y1: 0, x2: ROLE_W, y2: LINE_H,
                             stroke: '#d1d5db', strokeWidth: 0.5 },
            portRoleLabel: { ref: 'portBody', refX: 4,          refY: 5,
                             fontSize: 9, fontWeight: 'bold', fill: '#6b7280' },
            portNameLabel: { ref: 'portBody', refX: ROLE_W + 6, refY: 5,
                             fontSize: 10, fill: '#111827' },
            portTypeLabel: { ref: 'portBody', refX: TYPE_X,     refY: 5,
                             fontSize: 9,  fill: '#6b7280' },
          },
        },
      },
    },
  }, true);

  /* ── utils ── */
  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
  function ellip(s, n) {
    const t = String(s == null ? '' : s);
    return (!n || t.length <= n) ? t : t.slice(0, n - 1) + '\\u2026';
  }
  function withTimeout(p, label, ms = 25000) {
    const t = new Promise((_, rej) => {
      const id = setTimeout(() => rej(new Error(label + ' timed out (' + ms + 'ms)')), ms);
    });
    return Promise.race([p, t]).finally(() => clearTimeout(id));
  }

  /* ── state ── */
  const MODEL      = __MODEL_JSON__;
  const domList    = Array.isArray(MODEL?.domains) ? MODEL.domains : [];
  const docMap     = (MODEL?.documents && typeof MODEL.documents === 'object') ? MODEL.documents : {};
  let activeDomain = (MODEL && typeof MODEL.initialDomainId === 'string')
                     ? MODEL.initialDomainId : ((domList[0]?.id) || 'default');
  let activeRenderer = 'graphviz-interactive';
  let activeLayout   = 'x6-gv-dot-lr';
  let activeGvLayout = 'dot-lr';
  let lodLevel       = 'detailed';

  /* ── doc helpers ── */
  function activeDoc() {
    const d = docMap[activeDomain];
    return (d && Array.isArray(d.cells)) ? d : { cells: [] };
  }
  function erdNodes(doc = activeDoc()) {
    return (doc?.cells || []).filter(c => c?.shape === 'er-rect');
  }
  function erdEdges(doc = activeDoc()) {
    return (doc?.cells || []).filter(c => c?.shape === 'edge');
  }
  function srcId(e) {
    return typeof e.source === 'object' ? String(e.source?.cell || '') : String(e.source || '');
  }
  function tgtId(e) {
    return typeof e.target === 'object' ? String(e.target?.cell || '') : String(e.target || '');
  }
  function ePanel(e) {
    return (e?.data?.payload_panel && typeof e.data.payload_panel === 'object' && !Array.isArray(e.data.payload_panel))
      ? e.data.payload_panel : {};
  }

  /* ── X6 Graph ── */
  const container = document.getElementById('container');
  const graph = new Graph({
    container,
    width: container.clientWidth,
    height: container.clientHeight,
    connecting: {
      router: { name: 'orth' },
      connector: { name: 'rounded', args: { radius: 4 } },
      validateMagnet: () => false,
      createEdge() {
        return new Shape.Edge({ attrs: { line: { stroke: '#A2B1C3', strokeWidth: 2 } } });
      },
    },
    mousewheel: { enabled: false, minScale: MIN_SC, maxScale: MAX_SC },
    panning: true,
    background: { color: '#f4f5f7' },
    grid: { visible: true, size: 20 },
  });

  /* ── LOD ── */
  function refreshLod() {
    graph.batchUpdate(() => {
      graph.getNodes().forEach(node => {
        if (node.shape !== 'er-rect') return;
        const dd    = node.getData?.() || {};
        const panel = (dd?.payload_panel && typeof dd.payload_panel === 'object') ? dd.payload_panel : {};
        node.attr('label/text', ellip(String(panel.label || '').trim() || String(node.attr('label/text') || ''), 24));
        const names = Array.isArray(dd.lod_port_names) ? dd.lod_port_names : [];
        const types = Array.isArray(dd.lod_port_types) ? dd.lod_port_types : [];
        const roles = Array.isArray(dd.lod_port_roles) ? dd.lod_port_roles : [];
        const ports = (node.getPorts?.() || []).filter(p => p.group === 'list');
        ports.forEach((slot, i) => {
          const pid = slot?.id != null ? String(slot.id) : null;
          if (!pid) return;
          node.setPortProp(pid, 'attrs/portRoleLabel/text', roles[i] != null ? String(roles[i]) : '');
          node.setPortProp(pid, 'attrs/portTypeLabel/text',
            lodLevel === 'overview' ? '' : ellip(types[i] != null ? String(types[i]) : '', 10));
          node.setPortProp(pid, 'attrs/portNameLabel/fontSize', lodLevel === 'overview' ? 9 : 10);
          node.setPortProp(pid, 'attrs/portNameLabel/text', ellip(names[i] != null ? String(names[i]) : '', 16));
        });
        node.attr('label/fontSize', lodLevel === 'overview' ? 10 : 12);
      });
    });
  }
  function applyLod(level, force) {
    if (!force && lodLevel === level) return;
    lodLevel = level;
    refreshLod();
  }

  /* ── edge anchors ── */
  function anchorName(dx, dy, isSrc) {
    if (Math.abs(dx) >= Math.abs(dy))
      return dx >= 0 ? (isSrc ? 'right' : 'left') : (isSrc ? 'left' : 'right');
    return dy >= 0 ? (isSrc ? 'bottom' : 'top') : (isSrc ? 'top' : 'bottom');
  }
  function refreshAnchors(g, clearVerts = true) {
    g.getEdges().forEach(edge => {
      const s = edge.getSourceCell?.();
      const t = edge.getTargetCell?.();
      if (!s || !t || s.shape !== 'er-rect' || t.shape !== 'er-rect') return;
      if (s.id === t.id) {
        edge.setSource?.({ cell: s.id, anchor: { name: 'right' } });
        edge.setTarget?.({ cell: t.id, anchor: { name: 'top'   } });
        const p = s.position(), sz = s.size();
        edge.setVertices?.([
          { x: p.x + sz.width + 60, y: p.y + sz.height * 0.3 },
          { x: p.x + sz.width + 60, y: p.y - 30 },
        ]);
        return;
      }
      const sb = s.getBBox(), tb = t.getBBox();
      const dx = (tb.x + tb.width  / 2) - (sb.x + sb.width  / 2);
      const dy = (tb.y + tb.height / 2) - (sb.y + sb.height / 2);
      edge.setSource?.({ cell: s.id, anchor: { name: anchorName(dx, dy, true)  } });
      edge.setTarget?.({ cell: t.id, anchor: { name: anchorName(dx, dy, false) } });
      if (clearVerts) edge.setVertices?.([]);
    });
  }

  /* ═══════════════════ Graphviz plain → X6 ═══════════════════ */
  function gvSafeId(id) {
    return String(id).replace(/[^A-Za-z0-9_]/g, '_').replace(/^([^A-Za-z_])/, '_$1') || '_n';
  }
  function gvEngine(mode) {
    const m = String(mode).replace(/^x6-gv-/, '');
    const map = { 'dot-lr':'dot','dot-tb':'dot',neato:'neato',fdp:'fdp',sfdp:'sfdp',circo:'circo',twopi:'twopi',osage:'osage' };
    return map[m] || 'dot';
  }
  function gvGraphAttrs(mode) {
    const m = String(mode).replace(/^x6-gv-/, '');
    const base = 'overlap=false, splines=false';
    if (m === 'dot-tb') return 'rankdir=TB, ' + base + ', nodesep=0.9, ranksep=1.4';
    if (m === 'neato')  return base + ', sep="+40"';
    if (m === 'fdp')    return base + ', K=1.2, sep="+50"';
    if (m === 'sfdp')   return base + ', K=1.5';
    if (m === 'circo')  return base + ', mindist=1.4';
    if (m === 'twopi')  return base + ', ranksep=2.0';
    if (m === 'osage')  return base + ', pack=true';
    return 'rankdir=LR, ' + base + ', nodesep=0.9, ranksep=1.6';
  }
  function buildGvPlainDot(g, mode) {
    const nodes = g.getNodes().filter(n => n.shape === 'er-rect');
    const idMap  = new Map();
    const lines  = [
      'digraph G {',
      '  graph [' + gvGraphAttrs(mode) + '];',
      '  node  [shape=box, style=invis, label="", margin=0, fixedsize=true];',
      '  edge  [dir=none];',
    ];
    nodes.forEach(n => {
      const safe = gvSafeId(String(n.id));
      idMap.set(String(n.id), safe);
      const sz  = n.size();
      const wIn = (Number(sz.width  || NODE_W)  / IN2PX).toFixed(4);
      const hIn = (Number(sz.height || LINE_H*4) / IN2PX).toFixed(4);
      lines.push('  ' + safe + ' [width=' + wIn + ', height=' + hIn + '];');
    });
    const idSet = new Set(nodes.map(n => String(n.id)));
    g.getEdges().forEach(e => {
      const s = e.getSourceCell?.(), t = e.getTargetCell?.();
      const si = s && String(s.id), ti = t && String(t.id);
      if (si && ti && si !== ti && idSet.has(si) && idSet.has(ti))
        lines.push('  ' + idMap.get(si) + ' -> ' + idMap.get(ti) + ';');
    });
    lines.push('}');
    return { dot: lines.join('\\n'), idMap };
  }
  function parsePlain(raw, idMap) {
    const safeToOrig = new Map();
    idMap.forEach((safe, orig) => safeToOrig.set(safe, orig));
    const nodePos = new Map();
    let graphH = 0;
    String(raw || '').split('\\n').forEach(line => {
      const tok = line.trim().split(/\\s+/);
      if (!tok[0]) return;
      if (tok[0] === 'graph' && tok.length >= 4) {
        graphH = parseFloat(tok[3]) || 0;
        return;
      }
      if (tok[0] === 'node' && tok.length >= 6) {
        const name  = tok[1];
        const cx_in = parseFloat(tok[2]);
        const cy_in = parseFloat(tok[3]);
        const w_in  = parseFloat(tok[4]);
        const h_in  = parseFloat(tok[5]);
        if (!name || isNaN(cx_in) || isNaN(cy_in)) return;
        const cx_px = cx_in * IN2PX;
        const cy_px = (graphH - cy_in) * IN2PX;
        const w_px  = w_in * IN2PX;
        const h_px  = h_in * IN2PX;
        const orig  = safeToOrig.get(name);
        if (orig) nodePos.set(orig, { x: cx_px - w_px / 2, y: cy_px - h_px / 2 });
      }
    });
    return nodePos;
  }
  async function ensureGvApi() {
    if (gvApi) return gvApi;
    const mod = await withTimeout(import(/*GV*/"__GV_URL__"), 'Graphviz import');
    const Cls = (mod.Graphviz) || (mod.default?.Graphviz) || mod.default;
    if (!Cls || typeof Cls.load !== 'function') throw new Error('Graphviz: no Graphviz.load()');
    gvApi = await withTimeout(Cls.load(), 'Graphviz.load()');
    return gvApi;
  }
  async function layoutGvX6(g, mode) {
    const nodes = g.getNodes().filter(n => n.shape === 'er-rect');
    if (!nodes.length) return true;
    try {
      const api = await ensureGvApi();
      const built = buildGvPlainDot(g, mode);
      const plain = api.layout(built.dot, 'plain', gvEngine(mode));
      const nodePos = parsePlain(plain, built.idMap);
      if (!nodePos.size) return false;
      const MARGIN = 80;
      g.batchUpdate(() => {
        nodes.forEach(n => {
          const pos = nodePos.get(String(n.id));
          if (pos) n.position(Math.max(10, MARGIN + pos.x), Math.max(10, MARGIN + pos.y));
        });
      });
      refreshAnchors(g, true);
      return true;
    } catch (e) { console.warn('erd: GV plain', e); return false; }
  }

  /* ═══════════════════ ELK layout ═══════════════════ */
  function elkOpts(mode) {
    const base = {
      'elk.spacing.nodeNode': '80',
      'elk.spacing.edgeEdge': '20',
      'elk.spacing.edgeNode': '40',
      'elk.padding': '[top=60,left=60,bottom=60,right=60]',
    };
    let ext = {};
    switch (mode) {
      case 'elk-down':
        ext = { 'elk.algorithm':'layered','elk.direction':'DOWN','elk.edgeRouting':'ORTHOGONAL',
                'elk.layered.nodePlacement.strategy':'BRANDES_KOEPF',
                'elk.layered.spacing.nodeNodeBetweenLayers':'100',
                'elk.layered.spacing.edgeNodeBetweenLayers':'40' };
        break;
      case 'elk-tree':
        ext = { 'elk.algorithm':'mrtree','elk.direction':'RIGHT' };
        break;
      case 'elk-stress':
        ext = { 'elk.algorithm':'stress','elk.stress.desiredEdgeLength':'280','elk.spacing.nodeNode':'100' };
        break;
      case 'elk-force':
        ext = { 'elk.algorithm':'force','elk.force.repulsivePower':'2','elk.spacing.nodeNode':'120' };
        break;
      default:
        ext = { 'elk.algorithm':'layered','elk.direction':'RIGHT','elk.edgeRouting':'ORTHOGONAL',
                'elk.layered.nodePlacement.strategy':'BRANDES_KOEPF',
                'elk.layered.crossingMinimization.strategy':'LAYER_SWEEP',
                'elk.layered.layering.strategy':'NETWORK_SIMPLEX',
                'elk.layered.spacing.nodeNodeBetweenLayers':'200',
                'elk.layered.spacing.edgeNodeBetweenLayers':'60' };
    }
    return Object.assign({}, base, ext);
  }
  async function layoutElk(g, mode) {
    if (typeof ELK !== 'function') return false;
    const elk   = new ELK();
    const nodes = g.getNodes().filter(n => n.shape === 'er-rect');
    if (!nodes.length) return true;
    const idSet = new Set(nodes.map(n => String(n.id)));
    const elkG  = {
      id: 'root',
      layoutOptions: elkOpts(mode),
      children: nodes.map(n => {
        const sz = n.size();
        return {
          id: String(n.id), width: sz.width, height: sz.height,
          layoutOptions: { 'elk.portConstraints': 'FIXED_SIDE' },
          ports: [
            { id: n.id + '__W', layoutOptions: { 'elk.port.side': 'WEST' } },
            { id: n.id + '__E', layoutOptions: { 'elk.port.side': 'EAST' } },
          ],
        };
      }),
      edges: [],
    };
    g.getEdges().forEach(e => {
      const s = e.getSourceCell?.(), t = e.getTargetCell?.();
      const si = s && String(s.id), ti = t && String(t.id);
      if (si && ti && si !== ti && idSet.has(si) && idSet.has(ti))
        elkG.edges.push({ id: String(e.id), sources: [si + '__E'], targets: [ti + '__W'] });
    });
    try {
      const layout = await elk.layout(elkG);
      const byId = new Map(nodes.map(n => [String(n.id), n]));
      (layout.children || []).forEach(c => {
        if (c.x != null && c.y != null) { const n = byId.get(String(c.id)); if (n) n.position(c.x, c.y); }
      });
      const eById = new Map(g.getEdges().map(e => [String(e.id), e]));
      (layout.edges || []).forEach(le => {
        const edge = eById.get(String(le.id));
        const sec  = Array.isArray(le.sections) ? le.sections[0] : null;
        const bends = (sec?.bendPoints) ? sec.bendPoints.map(p => ({ x: p.x, y: p.y })) : [];
        if (edge && bends.length) {
          edge.setVertices?.(bends);
          edge.setConnector?.({ name: 'rounded', args: { radius: 6 } });
        }
      });
      refreshAnchors(g, false);
      return true;
    } catch (e) { console.warn('erd: ELK', mode, e); return false; }
  }

  /* ═══════════════════ Dagre layout ═══════════════════ */
  async function layoutDagre(g, rankdir) {
    if (!dagre) return false;
    const nodes = g.getNodes().filter(n => n.shape === 'er-rect');
    if (!nodes.length) return true;
    const dg = new dagre.graphlib.Graph();
    dg.setDefaultEdgeLabel(() => ({}));
    dg.setGraph({ rankdir, nodesep: 60, ranksep: 160, edgesep: 30, marginx: 60, marginy: 60 });
    nodes.forEach(n => { const sz = n.size(); dg.setNode(String(n.id), { width: sz.width, height: sz.height }); });
    const idSet = new Set(nodes.map(n => String(n.id)));
    g.getEdges().forEach(e => {
      const s = e.getSourceCell?.(), t = e.getTargetCell?.();
      const si = s && String(s.id), ti = t && String(t.id);
      if (si && ti && si !== ti && idSet.has(si) && idSet.has(ti)) dg.setEdge(si, ti);
    });
    try { dagre.layout(dg); } catch(e) { console.warn('erd: dagre', e); return false; }
    g.batchUpdate(() => {
      nodes.forEach(n => {
        const nd = dg.node(String(n.id));
        if (nd) n.position(nd.x - nd.width / 2, nd.y - nd.height / 2);
      });
    });
    refreshAnchors(g, true);
    return true;
  }

  /* ═══════════════════ Grid layout ═══════════════════ */
  async function layoutGrid(g) {
    const nodes = g.getNodes().filter(n => n.shape === 'er-rect');
    if (!nodes.length) return true;
    const adj = new Map(nodes.map(n => [String(n.id), new Set()]));
    g.getEdges().forEach(e => {
      const s = e.getSourceCell?.(), t = e.getTargetCell?.();
      const si = s && String(s.id), ti = t && String(t.id);
      if (si && ti && si !== ti && adj.has(si) && adj.has(ti)) { adj.get(si).add(ti); adj.get(ti).add(si); }
    });
    const deg = id => (adj.get(id)?.size) || 0;
    const components = [], seen = new Set();
    nodes.forEach(n => {
      const root = String(n.id);
      if (seen.has(root)) return;
      const ids = [], q = [root]; seen.add(root);
      while (q.length) {
        const id = q.shift(); ids.push(id);
        Array.from(adj.get(id) || []).sort((a,b) => deg(b)-deg(a)||a.localeCompare(b))
          .forEach(x => { if (!seen.has(x)) { seen.add(x); q.push(x); } });
      }
      components.push(ids);
    });
    components.sort((a,b) => b.length - a.length);
    const byId = new Map(nodes.map(n => [String(n.id), n]));
    const GAP_X = 80, GAP_Y = 60;
    const viewW = Math.max(1280, container.clientWidth || 1280);
    let curX = 80, curY = 80, rowH = 0;
    components.forEach(ids => {
      const sizes = ids.map(id => { const n = byId.get(id); return n ? n.size() : { width: NODE_W, height: LINE_H*4 }; });
      const cellW = Math.max(...sizes.map(s=>s.width))  + GAP_X;
      const cellH = Math.max(...sizes.map(s=>s.height)) + GAP_Y;
      const cols  = ids.length <= 3 ? ids.length : Math.min(5, Math.ceil(Math.sqrt(ids.length * 1.4)));
      const compW = cols * cellW;
      if (curX + compW > viewW && curX > 80) { curX = 80; curY += rowH + 100; rowH = 0; }
      const hub = ids.slice().sort((a,b) => deg(b)-deg(a)||a.localeCompare(b))[0];
      const order = [], ls = new Set([hub]), lq = [hub];
      while (lq.length) {
        const id2 = lq.shift(); order.push(id2);
        Array.from(adj.get(id2) || []).filter(x => ids.includes(x))
          .sort((a,b) => deg(b)-deg(a)||a.localeCompare(b))
          .forEach(x => { if (!ls.has(x)) { ls.add(x); lq.push(x); } });
      }
      ids.filter(id => !ls.has(id)).forEach(id => order.push(id));
      order.forEach((id, ix) => {
        const row = Math.floor(ix / cols), col = ix % cols;
        const n = byId.get(id); if (n) n.position(curX + col * cellW, curY + row * cellH);
      });
      rowH = Math.max(rowH, Math.ceil(ids.length / cols) * cellH);
      curX += compW + 120;
    });
    refreshAnchors(g, true);
    return true;
  }

  function layoutFallback(g) {
    const nodes = g.getNodes().filter(n => n.shape === 'er-rect');
    nodes.forEach((n, i) => {
      const ring  = Math.ceil(Math.sqrt(i + 1));
      const angle = i * 137.508 * Math.PI / 180;
      n.position(500 + Math.cos(angle) * (300 + ring * 60), 350 + Math.sin(angle) * (200 + ring * 40));
    });
    refreshAnchors(g, true);
  }

  async function runLayout(g) {
    if (activeLayout === 'grid')     return layoutGrid(g);
    if (activeLayout === 'dagre-lr') return layoutDagre(g, 'LR');
    if (activeLayout === 'dagre-tb') return layoutDagre(g, 'TB');
    if (activeLayout.startsWith('x6-gv-')) return layoutGvX6(g, activeLayout.replace('x6-gv-', ''));
    return layoutElk(g, activeLayout);
  }

  /* ═══════════════════ Diagram builders (non‑interactive) ═══════════════════ */
  function stableIds(nodes) {
    const used = new Set(), out = new Map();
    nodes.forEach((nd, ix) => {
      const panel = (nd?.data?.payload_panel) || {};
      let lbl = String(panel.label || (nd.attrs?.label?.text) || nd.id || ('E' + (ix+1)));
      let base = lbl.replace(/[^A-Za-z0-9_]/g,'_').replace(/^_+|_+$/g,'') || ('E' + (ix+1));
      if (/^[0-9]/.test(base)) base = 'E_' + base;
      let cand = base, n = 2;
      while (used.has(cand)) { cand = base + '_' + n; n++; }
      used.add(cand);
      out.set(String(nd.id), cand);
    });
    return out;
  }
  function simpleType(t) {
    const r = String(t || '').toLowerCase().trim();
    if (!r) return 'string';
    if (r.includes('int')) return 'int';
    if (r.includes('float') || r.includes('decimal') || r.includes('money')) return 'float';
    if (r.includes('bool')) return 'boolean';
    if (r.includes('date') || r.includes('time')) return 'datetime';
    return String(t || '').replace(/[^A-Za-z0-9_]/g,'_').slice(0,48) || 'string';
  }
  function mmCardL(c) { return ({one:'||',zero_one:'o|',one_many:'}|',zero_many:'}o'})[String(c||'')] || '||'; }
  function mmCardR(c) { return ({one:'||',zero_one:'|o',one_many:'|{',zero_many:'o{'})[String(c||'')] || '||'; }
  function buildMermaid(doc) {
    const nodes = erdNodes(doc), ids = stableIds(nodes);
    const lines = ['erDiagram'];
    nodes.forEach(nd => {
      const id = ids.get(String(nd.id));
      const names = Array.isArray(nd.data?.lod_port_names) ? nd.data.lod_port_names : [];
      const types = Array.isArray(nd.data?.lod_port_types) ? nd.data.lod_port_types : [];
      const roles = Array.isArray(nd.data?.lod_port_roles) ? nd.data.lod_port_roles : [];
      lines.push('  ' + id + ' {');
      if (!names.length) lines.push('    string id PK');
      names.forEach((nm, i) => {
        const typ = simpleType(types[i]);
        const field = String(nm || ('f' + i)).replace(/[^A-Za-z0-9_]/g,'_') || ('f' + i);
        const rr = String(roles[i] || '');
        const role = rr.includes('PK') ? ' PK' : rr.includes('FK') ? ' FK' : '';
        lines.push('    ' + typ + ' ' + field + role);
      });
      lines.push('  }');
    });
    erdEdges(doc).forEach(e => {
      const s = ids.get(srcId(e)), t = ids.get(tgtId(e));
      if (!s || !t) return;
      const p = ePanel(e);
      const lbl = String(p.source_field || p.label || 'rel').replace(/"/g,"'").trim();
      lines.push('  ' + s + ' ' + mmCardL(p.source_cardinality) + '--' + mmCardR(p.target_cardinality) + ' ' + t + ' : "' + (lbl || 'rel') + '"');
    });
    return lines.join('\\n');
  }
  function gvCardLabel(c) { return ({one:'||',zero_one:'o|',one_many:'|<',zero_many:'o<'})[String(c||'')] || ''; }
  function gvGAttrs(mode) {
    const base = 'overlap=false, splines=ortho, bgcolor="#f4f5f7"';
    if (mode === 'dot-tb') return 'rankdir=TB, ' + base + ', nodesep=0.8, ranksep=1.3';
    if (mode === 'neato')  return base + ', sep="+40"';
    if (mode === 'fdp')    return base + ', K=1.2, sep="+50"';
    if (mode === 'sfdp')   return base + ', K=1.5';
    if (mode === 'circo')  return base + ', mindist=1.4';
    if (mode === 'twopi')  return base + ', ranksep=2.0';
    if (mode === 'osage')  return base + ', pack=true';
    return 'rankdir=LR, ' + base + ', nodesep=0.8, ranksep=1.5';
  }
  function buildGvFullDot(doc, mode) {
    const nodes = erdNodes(doc), ids = stableIds(nodes);
    const engine = gvEngine(mode);
    const lines = [
      'digraph ERD {',
      '  graph [' + gvGAttrs(mode) + ', fontname="Arial"];',
      '  node  [shape=plain, fontname="Arial", fontsize=11];',
      '  edge  [fontname="Arial", fontsize=10, color="#374151", dir=none, penwidth=1.5];',
      '',
    ];
    nodes.forEach(nd => {
      const id = gvSafeId(ids.get(String(nd.id)));
      const panel = (nd.data?.payload_panel) || {};
      const lbl = esc(String(panel.label || id)).replace(/"/g,'&quot;');
      const names = Array.isArray(nd.data?.lod_port_names) ? nd.data.lod_port_names : [];
      const types = Array.isArray(nd.data?.lod_port_types) ? nd.data.lod_port_types : [];
      const roles = Array.isArray(nd.data?.lod_port_roles) ? nd.data.lod_port_roles : [];
      const rows = ['<TR><TD BGCOLOR="#1e3a5f" COLSPAN="3" ALIGN="CENTER"><FONT COLOR="white"><B>' + lbl + '</B></FONT></TD></TR>'];
      if (!names.length) rows.push('<TR><TD BGCOLOR="#fff3cd"><B>PK</B></TD><TD>id</TD><TD><I>str</I></TD></TR>');
      names.forEach((nm, i) => {
        const rr = String(roles[i] || '');
        const isPk = rr.includes('PK'), isFk = rr.includes('FK');
        const badge = isPk && isFk ? '<B>PK,FK</B>' : isPk ? '<B>PK</B>' : isFk ? 'FK' : '';
        const bg = isPk ? '#fff3cd' : isFk ? '#e8f4f8' : '#f9fafb';
        const fn = esc(String(nm || ('f' + i)));
        const ft = esc(String(types[i] || ''));
        rows.push('<TR><TD BGCOLOR="' + bg + '">' + badge + '</TD><TD ALIGN="LEFT">' + fn + '</TD><TD ALIGN="LEFT"><I>' + ft + '</I></TD></TR>');
      });
      lines.push('  ' + id + ' [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5" COLOR="#374151">');
      rows.forEach(r => lines.push('    ' + r));
      lines.push('  </TABLE>>];');
      lines.push('');
    });
    erdEdges(doc).forEach(e => {
      const s = gvSafeId(ids.get(srcId(e))), t = gvSafeId(ids.get(tgtId(e)));
      if (!s || !t) return;
      const p = ePanel(e);
      const lbl = String(p.source_field || p.label || '').trim();
      const tail = gvCardLabel(p.source_cardinality);
      const head = gvCardLabel(p.target_cardinality);
      const lp = lbl ? (', label=' + JSON.stringify(lbl)) : '';
      lines.push('  ' + s + ' -> ' + t + ' [taillabel=' + JSON.stringify(tail) + ', headlabel=' + JSON.stringify(head) + lp + '];');
    });
    lines.push('}');
    return { dot: lines.join('\\n'), engine: engine };
  }
  function buildD2(doc) {
    const nodes = erdNodes(doc), ids = stableIds(nodes);
    const fieldMap = new Map();
    const lines = ['direction: right', ''];
    nodes.forEach(nd => {
      const id = gvSafeId(ids.get(String(nd.id)));
      const names = Array.isArray(nd.data?.lod_port_names) ? nd.data.lod_port_names : [];
      const types = Array.isArray(nd.data?.lod_port_types) ? nd.data.lod_port_types : [];
      const roles = Array.isArray(nd.data?.lod_port_roles) ? nd.data.lod_port_roles : [];
      const lf = new Map();
      lines.push(id + ': {', '  shape: sql_table');
      if (!names.length) lines.push('  id: string {constraint: primary_key}');
      names.forEach((nm, i) => {
        const raw = String(nm || ('f' + i)).replace(/[^A-Za-z0-9_]/g,'_') || ('f' + i);
        const fld = /^[0-9]/.test(raw) ? 'f_' + raw : raw;
        const typ = String(types[i] || '').includes('FK') ? 'string' : simpleType(types[i]);
        const rr = String(roles[i] || '');
        const con = (rr.includes('PK') && rr.includes('FK')) ? '{constraint: [primary_key; foreign_key]}'
                  : rr.includes('PK') ? '{constraint: primary_key}'
                  : rr.includes('FK') ? '{constraint: foreign_key}' : '';
        lf.set(String(nm || ''), fld);
        lines.push('  ' + fld + ': ' + typ + (con ? ' ' + con : ''));
      });
      fieldMap.set(String(nd.id), lf);
      lines.push('}', '');
    });
    erdEdges(doc).forEach(e => {
      const sR = srcId(e), tR = tgtId(e);
      const s = gvSafeId(ids.get(sR)), t = gvSafeId(ids.get(tR));
      if (!s || !t) return;
      const p = ePanel(e);
      const sf = String(p.source_field || '');
      const sfld = (fieldMap.get(sR)?.get(sf)) || 'id';
      lines.push(s + '.' + sfld + ' -> ' + t + '.id');
    });
    return lines.join('\\n');
  }

  /* ── API loaders ── */
  async function ensureMermaid() {
    if (mmApi) return mmApi;
    const m = await import(/*MM*/"__MM_URL__");
    mmApi = m.default || m;
    if (typeof mmApi.initialize === 'function')
      mmApi.initialize({ startOnLoad: false, securityLevel: 'loose', theme: 'base', er: { useMaxWidth: false } });
    return mmApi;
  }
  async function ensureD2() {
    if (d2Api) return d2Api;
    const m = await withTimeout(import(/*D2*/"__D2_URL__"), 'D2 import');
    const Cls = m.D2 || (m.default?.D2) || m.default;
    if (!Cls) throw new Error('D2: no D2 export');
    d2Api = new Cls();
    if (typeof d2Api.ready === 'function') await withTimeout(d2Api.ready(), 'D2 ready', 15000);
    return d2Api;
  }

  /* ── Render functions (non‑interactive) ── */
  const mmCont   = document.getElementById('mermaid-container');
  const gvCont   = document.getElementById('graphviz-container');
  const d2Cont   = document.getElementById('d2-container');
  const d2SrcCont = document.getElementById('d2-source-container');
  const gvIntCont = document.getElementById('gv-interactive-container');
  const elkCont   = document.getElementById('elk-canvas-container');
  const zoomToolbar = document.getElementById('zoom-toolbar');

  async function renderMermaid(doc) {
    mmCont.innerHTML = '<div class="erd-loading">Rendering Mermaid…</div>';
    try {
      const api = await ensureMermaid();
      const id = 'mm-' + Date.now();
      const r = await withTimeout(api.render(id, buildMermaid(doc)), 'Mermaid render');
      mmCont.innerHTML = r.svg || String(r);
    } catch(e) {
      mmCont.innerHTML = '<pre class="erd-error">' + esc(String(e?.message || e)) + '</pre>';
    }
  }
  async function renderGvSvg(doc) {
    const built = buildGvFullDot(doc, activeGvLayout);
    gvCont.innerHTML = '<div class="erd-loading">Rendering Graphviz (' + built.engine + ')…</div>';
    try {
      const api = await ensureGvApi();
      const svg = api.layout(built.dot, 'svg', built.engine);
      if (!svg) throw new Error('empty SVG');
      gvCont.innerHTML = svg;
      const svgEl = gvCont.querySelector('svg');
      if (svgEl) {
        if (!svgEl.getAttribute('viewBox')) {
          const w = parseFloat(svgEl.getAttribute('width')  || '0');
          const h = parseFloat(svgEl.getAttribute('height') || '0');
          if (w && h) svgEl.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
        }
        svgEl.removeAttribute('width'); svgEl.removeAttribute('height');
        svgEl.setAttribute('width','100%'); svgEl.setAttribute('height','auto');
      }
    } catch(e) {
      gvCont.innerHTML = '<pre class="erd-error">' + esc(String(e?.message || e)) + '</pre>';
    }
  }
  async function renderD2(doc) {
    d2Cont.innerHTML = '<div class="erd-loading">Rendering D2…</div>';
    const src = buildD2(doc);
    try {
      const api = await ensureD2();
      let svg;
      if (typeof api.layout === 'function') svg = await withTimeout(api.layout(src), 'D2 layout', 30000);
      else if (typeof api.compile === 'function') {
        const res = await withTimeout(api.compile(src, { layout: 'dagre' }), 'D2 compile', 30000);
        if (typeof res === 'string') svg = res;
        else if (res?.svg) svg = res.svg;
        else if (res?.diagram && typeof api.render === 'function')
          svg = await withTimeout(api.render(res.diagram, { ...res.renderOptions, noXMLTag: true }), 'D2 render', 15000);
        else throw new Error('D2: unexpected compile() return');
      } else throw new Error('D2: no usable API');
      if (!svg || typeof svg !== 'string') throw new Error('D2: empty SVG');
      d2Cont.innerHTML = svg;
    } catch(e) {
      d2Cont.innerHTML = '<pre class="erd-error">' + esc(String(e?.message || e)) + '\\n\\nD2 source:\\n' + esc(src) + '</pre>';
    }
  }
  function renderD2Src(doc) { d2SrcCont.textContent = buildD2(doc); }

  function x6DocWithoutPorts(doc) {
    return {
      cells: (doc?.cells || []).map(cell => {
        if (cell?.shape !== 'er-rect') return cell;
        const copy = { ...cell };
        delete copy.ports;
        return copy;
      }),
    };
  }

  /* ═══════════════════ NEW INTERACTIVE RENDERERS ═══════════════════ */

  /* ── Graphviz Interactive ── */
  let gvInteractiveSvg = null, gvPanZoom = {x:0, y:0, scale:1};

  async function renderGraphvizInteractive(doc) {
    gvIntCont.innerHTML = '<div class="erd-loading">Building Graphviz Interactive…</div>';
    const built = buildGvFullDot(doc, activeGvLayout);
    try {
      const api = await ensureGvApi();
      const svgStr = api.layout(built.dot, 'svg', built.engine);
      if (!svgStr) throw new Error('empty SVG');

      const parser = new DOMParser();
      const svgDoc = parser.parseFromString(svgStr, 'image/svg+xml');
      const svgRoot = svgDoc.documentElement;
      svgRoot.setAttribute('width', '100%');
      svgRoot.setAttribute('height', '100%');
      const mainGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      mainGroup.setAttribute('id', 'gv-main-group');
      while (svgRoot.firstChild) mainGroup.appendChild(svgRoot.firstChild);
      svgRoot.appendChild(mainGroup);

      const idMap = {};
      const allCells = activeDoc().cells || [];
      allCells.filter(c => c.shape === 'er-rect').forEach(c => { idMap[gvSafeId(c.id)] = c.id; });

      mainGroup.querySelectorAll('g.node').forEach(node => {
        const title = node.querySelector('title');
        if (!title) return;
        const gvId = title.textContent;
        const entityId = idMap[gvId];
        if (!entityId) return;

        const bbox = node.getBBox();
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', bbox.x);
        rect.setAttribute('y', bbox.y);
        rect.setAttribute('width', bbox.width);
        rect.setAttribute('height', bbox.height);
        rect.setAttribute('fill', 'transparent');
        rect.style.pointerEvents = 'all';
        rect.style.cursor = 'pointer';

        rect.addEventListener('mouseenter', () => {
          mainGroup.querySelectorAll('g.edge path, g.edge polyline').forEach(p => p.setAttribute('stroke', '#374151'));
          mainGroup.querySelectorAll('g.edge').forEach(edge => {
            const et = edge.querySelector('title');
            if (!et) return;
            const text = et.textContent || '';
            if (text.includes(entityId) || text.includes(gvId)) {
              edge.querySelectorAll('path, polyline').forEach(p => p.setAttribute('stroke', '#e41a1c'));
              edge.querySelectorAll('text').forEach(t => t.setAttribute('fill', '#e41a1c'));
            }
          });
        });
        rect.addEventListener('mouseleave', () => {
          mainGroup.querySelectorAll('g.edge path, g.edge polyline').forEach(p => p.setAttribute('stroke', '#374151'));
          mainGroup.querySelectorAll('g.edge text').forEach(t => t.setAttribute('fill', '#000'));
        });
        rect.addEventListener('click', () => showDetailForEntity(entityId));

        node.parentNode.insertBefore(rect, node);
      });

      gvIntCont.innerHTML = '';
      gvIntCont.appendChild(svgRoot);
      gvInteractiveSvg = svgRoot;

      function applyTransform() {
        mainGroup.setAttribute('transform', `translate(${gvPanZoom.x},${gvPanZoom.y}) scale(${gvPanZoom.scale})`);
      }
      gvIntCont.onwheel = e => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        gvPanZoom.scale *= delta;
        gvPanZoom.scale = Math.min(3, Math.max(0.15, gvPanZoom.scale));
        applyTransform();
      };
      let isPanning = false, startX, startY, origX, origY;
      gvIntCont.onmousedown = e => {
        if (e.target.closest('rect[fill="transparent"]')) return;
        isPanning = true;
        startX = e.clientX; startY = e.clientY;
        origX = gvPanZoom.x; origY = gvPanZoom.y;
        e.preventDefault();
      };
      window.addEventListener('mousemove', e => {
        if (!isPanning) return;
        gvPanZoom.x = origX + e.clientX - startX;
        gvPanZoom.y = origY + e.clientY - startY;
        applyTransform();
      });
      window.addEventListener('mouseup', () => { isPanning = false; });

    } catch(e) {
      gvIntCont.innerHTML = '<pre class="erd-error">' + esc(String(e?.message || e)) + '</pre>';
    }
  }

  /* ── ELK Canvas ── */
  let elkCanvasNodes = {}, elkZoom = 1;
  const elkWrapper = document.createElement('div');
  elkWrapper.style.position = 'relative';
  elkWrapper.style.width = '2000px';
  elkWrapper.style.height = '2000px';
  elkWrapper.style.transformOrigin = '0 0';
  const elkSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  elkSvg.setAttribute('width', '100%');
  elkSvg.setAttribute('height', '100%');
  elkSvg.style.position = 'absolute';
  elkSvg.style.top = 0;
  elkSvg.style.left = 0;
  elkSvg.style.pointerEvents = 'none';
  elkWrapper.appendChild(elkSvg);

  function updateElkEdges() {
    elkSvg.innerHTML = '';
    const doc = activeDoc();
    const edges = erdEdges(doc);
    edges.forEach(e => {
      const src = elkCanvasNodes[srcId(e)];
      const tgt = elkCanvasNodes[tgtId(e)];
      if (!src || !tgt) return;
      const sr = src.getBoundingClientRect();
      const tr = tgt.getBoundingClientRect();
      const wr = elkWrapper.getBoundingClientRect();
      const x1 = sr.left + sr.width/2 - wr.left;
      const y1 = sr.top + sr.height/2 - wr.top;
      const x2 = tr.left + tr.width/2 - wr.left;
      const y2 = tr.top + tr.height/2 - wr.top;
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', x1); line.setAttribute('y1', y1);
      line.setAttribute('x2', x2); line.setAttribute('y2', y2);
      line.setAttribute('stroke', '#374151');
      line.setAttribute('stroke-width', '1.5');
      elkSvg.appendChild(line);
    });
  }

  async function renderElkCanvas(doc) {
    elkCont.innerHTML = '';
    elkCanvasNodes = {};
    elkCont.appendChild(elkWrapper);

    if (typeof ELK !== 'function') {
      elkCont.innerHTML = '<div class="erd-error">ELK not available</div>';
      return;
    }

    const nodesData = erdNodes(doc);
    if (!nodesData.length) {
      elkCont.innerHTML = '<div class="erd-error">No entities</div>';
      return;
    }

    elkWrapper.querySelectorAll('.elk-node').forEach(n => n.remove());

    nodesData.forEach((nd, i) => {
      const div = document.createElement('div');
      div.className = 'elk-node';
      div.id = 'elk-node-' + nd.id;
      div.style.left = '50px';
      div.style.top = (50 + i * 200) + 'px';

      const panel = (nd.data?.payload_panel) || {};
      const headerText = esc(String(panel.label || nd.attrs?.label?.text || ''));
      div.innerHTML = `<div class="elk-node-header">${headerText}</div>`;
      const names = nd.data?.lod_port_names || [];
      const types = nd.data?.lod_port_types || [];
      names.forEach((name, idx) => {
        const row = document.createElement('div');
        row.className = 'elk-node-row';
        row.innerHTML = `<span class="field-name">${esc(name)}</span><span class="field-type">${esc(types[idx] || '')}</span>`;
        div.appendChild(row);
      });

      let dragging = false, startX, startY, origLeft, origTop;
      div.addEventListener('mousedown', e => {
        dragging = true;
        startX = e.clientX;
        startY = e.clientY;
        origLeft = parseInt(div.style.left) || 0;
        origTop = parseInt(div.style.top) || 0;
        e.preventDefault();
      });
      window.addEventListener('mousemove', e => {
        if (!dragging) return;
        div.style.left = (origLeft + e.clientX - startX) + 'px';
        div.style.top = (origTop + e.clientY - startY) + 'px';
        requestAnimationFrame(updateElkEdges);
      });
      window.addEventListener('mouseup', () => { dragging = false; });
      div.addEventListener('click', () => showDetailForEntity(nd.id));

      elkWrapper.appendChild(div);
      elkCanvasNodes[nd.id] = div;
    });

    // Run ELK layout
    const elk = new ELK();
    const idSet = new Set(nodesData.map(n => String(n.id)));
    const elkGraph = {
      id: 'root',
      layoutOptions: elkOpts('elk-right'),
      children: nodesData.map(n => ({
        id: String(n.id),
        width: 200,
        height: LINE_H * (1 + (n.data?.lod_port_names?.length || 0)),
        layoutOptions: { 'elk.portConstraints': 'FIXED_SIDE' },
        ports: [
          { id: n.id + '__W', layoutOptions: { 'elk.port.side': 'WEST' } },
          { id: n.id + '__E', layoutOptions: { 'elk.port.side': 'EAST' } },
        ],
      })),
      edges: erdEdges(doc).map(e => ({
        id: String(e.id),
        sources: [String(srcId(e)) + '__E'],
        targets: [String(tgtId(e)) + '__W'],
      })),
    };
    try {
      const layout = await elk.layout(elkGraph);
      (layout.children || []).forEach(child => {
        if (child.x == null || child.y == null) return;
        const nodeDiv = elkCanvasNodes[child.id];
        if (nodeDiv) {
          nodeDiv.style.left = child.x + 'px';
          nodeDiv.style.top = child.y + 'px';
        }
      });
    } catch (e) { console.warn('ELK Canvas layout failed', e); }

    updateElkEdges();

    elkCont.onwheel = e => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      elkZoom = Math.min(3, Math.max(0.15, elkZoom * delta));
      elkWrapper.style.transform = `scale(${elkZoom})`;
    };
  }

  /* ── Detail panel (unified) ── */
  const detailShell = document.getElementById('node-detail-shell');
  const detailBody  = document.getElementById('node-detail-body');
  const detailTitle = document.getElementById('node-detail-title');
  const detailClose = document.getElementById('node-detail-close');
  const COPY_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';

  function closeDetail() {
    detailShell?.classList.remove('open');
    if (detailBody) detailBody.innerHTML = '';
  }
  function showDetail(cell) {
    if (!detailShell || !detailBody) return;
    const raw   = (cell.getData?.()) || cell.data || {};
    const panel = (raw?.payload_panel && typeof raw.payload_panel === 'object') ? raw.payload_panel : {};
    const title = cell.shape === 'er-rect'
      ? (String(cell.attr?.('label/text') || '').trim() || String(panel.label || panel.id || cell.id || ''))
      : String(panel.label || panel.id || cell.id || '');
    detailTitle.textContent = title;
    let html = '';
    Object.keys(panel).sort().forEach(k => {
      let v = panel[k] == null ? '' : (typeof panel[k] === 'object' ? JSON.stringify(panel[k]) : String(panel[k]));
      const multi = v.length > 140 || /[\\r\\n]/.test(v);
      html += '<div class="detail-section"><div class="detail-section-title">' + esc(k) + '</div>';
      if (multi) html += '<div class="prop-value-multiline">' + esc(v) + '</div>';
      else html += '<div class="field-row"><span class="field-name">' + esc(v) + '</span></div>';
      html += '</div>';
    });
    detailBody.innerHTML = html;
    detailShell.classList.add('open');
  }
  function showDetailForEntity(entityId) {
    const doc = activeDoc();
    const cell = doc.cells.find(c => c.id === entityId && c.shape === 'er-rect');
    if (cell) showDetail(cell);
  }
  detailClose?.addEventListener('click', closeDetail);

  /* ── Picker definitions ── */
  const rendererModes = [
    { id: 'x6',                     label: 'X6 (interactive)' },
    { id: 'mermaid',                label: 'Mermaid' },
    { id: 'graphviz',               label: 'Graphviz SVG' },
    { id: 'graphviz-interactive',   label: 'GV Interactive' },
    { id: 'elk-canvas',             label: 'ELK Canvas' },
    { id: 'd2',                     label: 'D2' },
    { id: 'd2-source',              label: 'D2 source' },
  ];
  const layoutModes = [
    { id: 'x6-gv-dot-lr', label: 'GV Dot LR ✦' },
    { id: 'x6-gv-dot-tb', label: 'GV Dot TB'   },
    { id: 'x6-gv-neato',  label: 'GV Neato'    },
    { id: 'x6-gv-fdp',    label: 'GV FDP'      },
    { id: 'x6-gv-sfdp',   label: 'GV SFDP'     },
    { id: 'x6-gv-circo',  label: 'GV Circo'    },
    { id: 'x6-gv-twopi',  label: 'GV Twopi'    },
    { id: 'elk-right',    label: 'ELK Right'    },
    { id: 'elk-down',     label: 'ELK Down'     },
    { id: 'elk-tree',     label: 'ELK Tree'     },
    { id: 'elk-stress',   label: 'ELK Stress'   },
    { id: 'elk-force',    label: 'ELK Force'    },
    { id: 'dagre-lr',     label: 'Dagre LR'     },
    { id: 'dagre-tb',     label: 'Dagre TB'     },
    { id: 'grid',         label: 'Grid'         },
  ];
  const gvLayoutModes = [
    { id: 'dot-lr', label: 'Dot LR ✦' },
    { id: 'dot-tb', label: 'Dot TB'  },
    { id: 'neato',  label: 'Neato'   },
    { id: 'fdp',    label: 'FDP'     },
    { id: 'sfdp',   label: 'SFDP'    },
    { id: 'circo',  label: 'Circo'   },
    { id: 'twopi',  label: 'Twopi'   },
    { id: 'osage',  label: 'Osage'   },
  ];

  const domPicker = document.getElementById('domain-pill-bar');
  const renPicker = document.getElementById('renderer-pill-bar');
  const layPicker = document.getElementById('layout-pill-bar');
  const domainGroup = document.getElementById('domain-picker');
  const layoutGroup = document.getElementById('layout-picker');

  function renderDomainPicker() {
    if (!domPicker) return;
    if (domList.length <= 1) { domainGroup.style.display = 'none'; return; }
    domainGroup.style.display = 'flex';
    domPicker.innerHTML = domList.map(d => {
      const icon = d.iconSrc ? '<img class="legend-icon" src="' + d.iconSrc + '" width="18" height="18" alt="">' : '';
      return `<button class="pill${d.id === activeDomain ? ' active' : ''}" data-did="${d.id}">${icon}<span>${esc(d.label)}</span></button>`;
    }).join('');
  }

  function renderRendererPicker() {
    if (!renPicker) return;
    renPicker.innerHTML = rendererModes.map(m =>
      `<button class="pill${m.id === activeRenderer ? ' active' : ''}" data-rid="${m.id}">${esc(m.label)}</button>`
    ).join('');
  }

  function renderLayoutPicker() {
    if (!layPicker) return;
    const isX6 = activeRenderer === 'x6';
    const isGv = activeRenderer === 'graphviz' || activeRenderer === 'graphviz-interactive';
    const modes = isX6 ? layoutModes : isGv ? gvLayoutModes : [];
    layoutGroup.style.display = modes.length ? 'flex' : 'none';
    if (!modes.length) return;
    const actId = isGv ? activeGvLayout : activeLayout;
    layPicker.innerHTML = modes.map(m =>
      `<button class="pill${m.id === actId ? ' active' : ''}" data-lid="${m.id}">${esc(m.label)}</button>`
    ).join('');
  }

  /* ── Event listeners for pickers ── */
  domPicker?.addEventListener('click', async e => {
    const btn = e.target.closest('[data-did]');
    if (!btn) return;
    const did = btn.getAttribute('data-did');
    if (did === activeDomain || !docMap[did]) return;
    activeDomain = did;
    renderDomainPicker();
    await renderAll();
  });
  renPicker?.addEventListener('click', async e => {
    const btn = e.target.closest('[data-rid]');
    if (!btn) return;
    const rid = btn.getAttribute('data-rid');
    if (rid === activeRenderer) return;
    activeRenderer = rid;
    renderRendererPicker();
    renderLayoutPicker();
    await renderAll();
  });
  layPicker?.addEventListener('click', async e => {
    const btn = e.target.closest('[data-lid]');
    if (!btn) return;
    const lid = btn.getAttribute('data-lid');
    if ((activeRenderer === 'graphviz' || activeRenderer === 'graphviz-interactive')) {
      if (lid === activeGvLayout) return;
      activeGvLayout = lid;
    } else {
      if (lid === activeLayout) return;
      activeLayout = lid;
    }
    renderLayoutPicker();
    await renderAll();
  });

  /* ── Zoom toolbar updates ── */
  function curScale() { return (graph?.transform?.getScale?.().sx) || 1; }
  function doZoom(factor) {
    if (activeRenderer === 'x6') {
      const s = Math.min(MAX_SC, Math.max(MIN_SC, curScale() * factor));
      graph.zoomTo?.(s);
      syncZoom();
    } else if (activeRenderer === 'graphviz-interactive') {
      gvPanZoom.scale = Math.min(3, Math.max(0.15, gvPanZoom.scale * factor));
      gvInteractiveSvg?.querySelector('#gv-main-group')
        ?.setAttribute('transform', `translate(${gvPanZoom.x},${gvPanZoom.y}) scale(${gvPanZoom.scale})`);
    } else if (activeRenderer === 'elk-canvas') {
      elkZoom = Math.min(3, Math.max(0.15, elkZoom * factor));
      elkWrapper.style.transform = `scale(${elkZoom})`;
    }
  }
  document.getElementById('btn-zoom-in')?.addEventListener('click', () => doZoom(1.25));
  document.getElementById('btn-zoom-out')?.addEventListener('click', () => doZoom(0.8));
  document.getElementById('btn-zoom-fit')?.addEventListener('click', () => {
    if (activeRenderer === 'x6') {
      graph.zoomToFit({ padding: { top: 72, right: 280, bottom: 80, left: 80 }, maxScale: 1.1 });
      syncZoom();
      applyLod(curScale() <= 0.6 ? 'overview' : 'detailed', true);
    }
    // for interactive renderers fit could be implemented but skipped for brevity
  });

  /* ── Graph events (X6) ── */
  graph.on('blank:click', closeDetail);
  graph.on('cell:click', ({ cell }) => {
    if (cell.shape === 'er-rect') showDetail(cell);
  });

  /* ── Main render dispatcher ── */
  async function renderAll() {
    const doc = activeDoc();
    const isX6 = activeRenderer === 'x6';
    const isGVInt = activeRenderer === 'graphviz-interactive';
    const isElkC = activeRenderer === 'elk-canvas';
    const isGv = activeRenderer === 'graphviz';
    container.style.display     = isX6 ? 'block' : 'none';
    mmCont.style.display        = activeRenderer === 'mermaid' ? 'block' : 'none';
    gvCont.style.display        = isGv ? 'block' : 'none';
    gvIntCont.style.display     = isGVInt ? 'block' : 'none';
    elkCont.style.display       = isElkC ? 'block' : 'none';
    d2Cont.style.display        = activeRenderer === 'd2' ? 'block' : 'none';
    d2SrcCont.style.display     = activeRenderer === 'd2-source' ? 'block' : 'none';
    zoomToolbar.style.display   = (isX6 || isGVInt || isElkC) ? 'flex' : 'none';

    if (isX6) {
      graph.resetCells?.();
      graph.fromJSON(x6DocWithoutPorts(doc));
      await new Promise(r => requestAnimationFrame(r));
      const ok = await runLayout(graph);
      if (!ok) layoutFallback(graph);
      graph.zoomToFit({ padding: { top: 72, right: 280, bottom: 80, left: 80 }, maxScale: 1.1 });
      syncZoom();
      applyLod(curScale() <= 0.6 ? 'overview' : 'detailed', true);
    } else if (isGVInt) {
      await renderGraphvizInteractive(doc);
    } else if (isElkC) {
      await renderElkCanvas(doc);
    } else if (activeRenderer === 'mermaid') {
      await renderMermaid(doc);
    } else if (isGv) {
      await renderGvSvg(doc);
    } else if (activeRenderer === 'd2') {
      await renderD2(doc);
    } else if (activeRenderer === 'd2-source') {
      renderD2Src(doc);
    }
    syncZoom();
  }

  function syncZoom() { /* X6 zoom label update, already defined, no-op for other renderers */ }

  /* ── Init ── */
  renderDomainPicker();
  renderRendererPicker();
  renderLayoutPicker();
  await renderAll();
  syncZoom();

})();
"""


def _make_bootstrap(model_json: str) -> str:
    js = _ERD_BOOTSTRAP_JS
    for placeholder, url in [
        ("__X6_URL__", X6_MODULE_URL),
        ("__ELK_URL__", ELK_MODULE_URL),
        ("__DAGRE_URL__", DAGRE_MODULE_URL),
        ("__MM_URL__", MERMAID_MODULE_URL),
        ("__GV_URL__", GRAPHVIZ_MODULE_URL),
        ("__D2_URL__", D2_MODULE_URL),
    ]:
        js = js.replace(placeholder, url)
    js = js.replace("__MODEL_JSON__", model_json)
    return js


def write_erd_html(document, *, output_path=None, title="Entity diagram", width="100%", height="100vh"):
    payload = copy.deepcopy(document)
    if "cells" not in payload:
        raise TypeError('write_erd_html expects document with top-level "cells"')
    model_json = json.dumps({
        "domains": [{"id": "default", "label": "Default", "iconSrc": ""}],
        "documents": {"default": payload},
        "initialDomainId": "default",
    }, ensure_ascii=False)
    out = DEFAULT_ERD_HTML_PATH if output_path is None else Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = (
        _template_raw()
        .replace("@@HTML_ESCAPED_TITLE@@", html_escape(title))
        .replace("@@CONTAINER_WIDTH@@", width)
        .replace("@@CONTAINER_HEIGHT@@", height)
        .replace("@@INLINE_ERD_SCRIPT@@", _make_bootstrap(model_json).strip())
    )
    out.write_text(html, encoding="utf-8")
    return out


def write_erd_html_from_coordinator(
    coordinator, domain_cls=None, *, output_path=None, title="Entity diagram", width="100%", height="100vh"
):
    from action_machine.domain.base_domain import BaseDomain
    from action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
    from graph.node_graph_coordinator import NodeGraphCoordinator
    from maxitor.visualizer.graph_visualizer.visualizer_icons import svg_data_uri_for_graph_node_icon

    erd_document_from_coordinator_graph = _load_erd_document_builder()

    if not isinstance(coordinator, NodeGraphCoordinator):
        raise TypeError("coordinator must be a built NodeGraphCoordinator")
    if domain_cls is not None and (
        not isinstance(domain_cls, type) or not issubclass(domain_cls, BaseDomain)
    ):
        raise TypeError("domain_cls must be a BaseDomain subclass")

    domain_nodes = sorted(
        [n for n in coordinator.get_all_nodes()
         if isinstance(n, DomainGraphNode)
         and isinstance(n.node_obj, type)
         and issubclass(n.node_obj, BaseDomain)],
        key=lambda n: str(n.properties.get("name", n.label)).lower(),
    )
    domain_documents: dict[str, dict] = {}
    domain_items: list[dict] = []
    initial_domain_id = None

    for dnode in domain_nodes:
        dcls = dnode.node_obj
        doc = erd_document_from_coordinator_graph(coordinator, dcls)
        domain_id = dnode.node_id
        domain_documents[domain_id] = doc
        domain_items.append({
            "id": domain_id,
            "label": str(dnode.properties.get("name", dnode.label)),
            "iconSrc": svg_data_uri_for_graph_node_icon("#1e3a5f", DomainGraphNode.NODE_TYPE),
        })
        if domain_cls is not None and dcls is domain_cls:
            initial_domain_id = domain_id

    if not domain_items:
        if domain_cls is None:
            raise LookupError("No Domain nodes found in coordinator graph.")
        doc = erd_document_from_coordinator_graph(coordinator, domain_cls)
        return write_erd_html(doc, output_path=output_path, title=title, width=width, height=height)

    if initial_domain_id is None:
        initial_domain_id = domain_items[0]["id"]

    model_json = json.dumps({
        "domains": domain_items,
        "documents": domain_documents,
        "initialDomainId": initial_domain_id,
    }, ensure_ascii=False)

    out = DEFAULT_ERD_HTML_PATH if output_path is None else Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = (
        _template_raw()
        .replace("@@HTML_ESCAPED_TITLE@@", html_escape(title))
        .replace("@@CONTAINER_WIDTH@@", width)
        .replace("@@CONTAINER_HEIGHT@@", height)
        .replace("@@INLINE_ERD_SCRIPT@@", _make_bootstrap(model_json).strip())
    )
    out.write_text(html, encoding="utf-8")
    return out
