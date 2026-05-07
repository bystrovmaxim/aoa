# src/maxitor/visualizer/erd_visualizer_1/erd_html.py
# mypy: ignore-errors
# pylint: disable=import-outside-toplevel
"""
Standalone ERD HTML export.

Renderers: X6 (interactive), Mermaid, Graphviz SVG, D2, D2 source.
X6 layout engines: ELK Right/Down/Tree/Stress/Force, Dagre LR/TB,
                   Grid, Graphviz-backed X6 (Dot LR/TB, Neato, FDP, SFDP, Circo, Twopi).

Default layout: GV Dot LR — uses Graphviz for positions and X6 for interactivity.
"""

from __future__ import annotations

import copy
import json
from functools import cache
from html import escape as html_escape
from pathlib import Path
from typing import Any

X6_MODULE_URL      = "https://esm.sh/@antv/x6@2.19.2"
ELK_MODULE_URL     = "https://esm.sh/elkjs@0.11.1"
DAGRE_MODULE_URL   = "https://esm.sh/@dagrejs/dagre@1.1.4"
MERMAID_MODULE_URL = "https://esm.sh/mermaid@11.12.0"
GRAPHVIZ_MODULE_URL = "https://esm.sh/@hpcc-js/wasm-graphviz@1.21.5"
D2_MODULE_URL      = "https://esm.sh/@terrastruct/d2@0.1.33"

_PACKAGE_DIR = Path(__file__).resolve().parent
_TEMPLATE_HTML = _PACKAGE_DIR / "template.html"
_LOCAL_OUTPUT_DIR = Path("/Users/bystrovmaxim/PythonDev/aoa/archive/logs")


def _default_archive_logs_dir() -> Path:
    """Return a default output directory that survives moving this folder."""
    return _LOCAL_OUTPUT_DIR


DEFAULT_ERD_HTML_PATH = _default_archive_logs_dir() / "erd.html"


@cache
def _template_raw() -> str:
    return _TEMPLATE_HTML.read_text(encoding="utf-8")


def _load_erd_document_builder():
    """Load the sibling graph-data builder whether this folder is imported or run directly."""
    try:
        from .erd_graph_data import erd_document_from_coordinator_graph
    except ImportError:
        from erd_graph_data import erd_document_from_coordinator_graph

    return erd_document_from_coordinator_graph


# JS is kept in a regular string; only the backslashes needed by JS are escaped.
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
  // plain-format coords are in inches; 1 inch = 72 pt (graphviz default)
  const IN2PX   = 72;

  /* ── X6 port layout ── */
  Graph.registerPortLayout('erPortPos',
    (args) => args.map((_, i) => ({ position: { x: 0, y: (i + 1) * LINE_H }, angle: 0 })),
    true);

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
          position: 'erPortPos',
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
  function withTimeout(p, label, ms) {
    ms = ms || 25000;
    var id;
    var t = new Promise(function(_, rej) {
      id = setTimeout(function() { rej(new Error(label + ' timed out (' + ms + 'ms)')); }, ms);
    });
    return Promise.race([p, t]).finally(function() { clearTimeout(id); });
  }

  /* ── state ── */
  const MODEL      = __MODEL_JSON__;
  const domList    = Array.isArray(MODEL && MODEL.domains) ? MODEL.domains : [];
  const docMap     = (MODEL && MODEL.documents && typeof MODEL.documents === 'object') ? MODEL.documents : {};
  var activeDomain = (MODEL && typeof MODEL.initialDomainId === 'string')
                     ? MODEL.initialDomainId : ((domList[0] && domList[0].id) || 'default');
  var activeRenderer = 'x6';
  var activeLayout   = 'x6-gv-dot-lr';   /* default: graphviz coords in X6 */
  var activeGvLayout = 'dot-lr';
  var lodLevel       = 'detailed';

  /* ── doc helpers ── */
  function activeDoc() {
    var d = docMap[activeDomain];
    return (d && Array.isArray(d.cells)) ? d : { cells: [] };
  }
  function erdNodes(doc) {
    return (doc && Array.isArray(doc.cells)) ? doc.cells.filter(function(c) { return c && c.shape === 'er-rect'; }) : [];
  }
  function erdEdges(doc) {
    return (doc && Array.isArray(doc.cells)) ? doc.cells.filter(function(c) { return c && c.shape === 'edge'; }) : [];
  }
  function srcId(e) {
    return typeof e.source === 'object' ? String((e.source && e.source.cell) || '') : String(e.source || '');
  }
  function tgtId(e) {
    return typeof e.target === 'object' ? String((e.target && e.target.cell) || '') : String(e.target || '');
  }
  function ePanel(e) {
    var p = e && e.data && e.data.payload_panel;
    return (p && typeof p === 'object' && !Array.isArray(p)) ? p : {};
  }
  function nPanel(n) {
    var p = n && n.data && n.data.payload_panel;
    return (p && typeof p === 'object' && !Array.isArray(p)) ? p : {};
  }

  /* ── X6 Graph ── */
  var container = document.getElementById('container');
  var graph = new Graph({
    container: container,
    width: container.clientWidth,
    height: container.clientHeight,
    connecting: {
      router: { name: 'orth' },
      connector: { name: 'rounded', args: { radius: 4 } },
      validateMagnet: function() { return false; },
      createEdge: function() {
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
    graph.batchUpdate(function() {
      graph.getNodes().forEach(function(node) {
        if (node.shape !== 'er-rect') return;
        var dd    = (node.getData && node.getData()) || {};
        var panel = (dd && dd.payload_panel && typeof dd.payload_panel === 'object') ? dd.payload_panel : {};
        node.attr('label/text', ellip(String(panel.label || '').trim() || String(node.attr('label/text') || ''), 24));
        var names = Array.isArray(dd.lod_port_names) ? dd.lod_port_names : [];
        var types = Array.isArray(dd.lod_port_types) ? dd.lod_port_types : [];
        var roles = Array.isArray(dd.lod_port_roles) ? dd.lod_port_roles : [];
        var ports = (node.getPorts ? node.getPorts() : []).filter(function(p) { return p.group === 'list'; });
        ports.forEach(function(slot, i) {
          var pid = slot && slot.id != null ? String(slot.id) : null;
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

  /* ── edge anchors ──
     clearVerts=true  after grid/dagre because route vertices are not needed.
     clearVerts=false after ELK/GV because the layout engine already routed them. */
  function anchorName(dx, dy, isSrc) {
    if (Math.abs(dx) >= Math.abs(dy))
      return dx >= 0 ? (isSrc ? 'right' : 'left') : (isSrc ? 'left' : 'right');
    return dy >= 0 ? (isSrc ? 'bottom' : 'top') : (isSrc ? 'top' : 'bottom');
  }
  function refreshAnchors(g, clearVerts) {
    if (clearVerts === undefined) clearVerts = true;
    g.getEdges().forEach(function(edge) {
      var s = edge.getSourceCell && edge.getSourceCell();
      var t = edge.getTargetCell && edge.getTargetCell();
      if (!s || !t || s.shape !== 'er-rect' || t.shape !== 'er-rect') return;
      if (s.id === t.id) {
        edge.setSource && edge.setSource({ cell: s.id, anchor: { name: 'right' } });
        edge.setTarget && edge.setTarget({ cell: t.id, anchor: { name: 'top'   } });
        var p = s.position(), sz = s.size();
        edge.setVertices && edge.setVertices([
          { x: p.x + sz.width + 60, y: p.y + sz.height * 0.3 },
          { x: p.x + sz.width + 60, y: p.y - 30 },
        ]);
        return;
      }
      var sb = s.getBBox(), tb = t.getBBox();
      var dx = (tb.x + tb.width  / 2) - (sb.x + sb.width  / 2);
      var dy = (tb.y + tb.height / 2) - (sb.y + sb.height / 2);
      edge.setSource && edge.setSource({ cell: s.id, anchor: { name: anchorName(dx, dy, true)  } });
      edge.setTarget && edge.setTarget({ cell: t.id, anchor: { name: anchorName(dx, dy, false) } });
      if (clearVerts) edge.setVertices && edge.setVertices([]);
    });
  }

  /* ════════════════════════════════════════════════════════════════════
     LAYOUT 1 — GRAPHVIZ → X6
     Graphviz computes coordinates in plain format; X6 keeps interactivity.
     ════════════════════════════════════════════════════════════════════ */
  function gvSafeId(id) {
    return String(id).replace(/[^A-Za-z0-9_]/g, '_').replace(/^([^A-Za-z_])/, '_$1') || '_n';
  }
  function gvEngine(mode) {
    var m = String(mode).replace(/^x6-gv-/, '');
    var map = { 'dot-lr':'dot','dot-tb':'dot',neato:'neato',fdp:'fdp',sfdp:'sfdp',circo:'circo',twopi:'twopi',osage:'osage' };
    return map[m] || 'dot';
  }
  function gvRankdir(mode) {
    return String(mode).replace(/^x6-gv-/, '') === 'dot-tb' ? 'TB' : 'LR';
  }
  function gvGraphAttrs(mode) {
    var m = String(mode).replace(/^x6-gv-/, '');
    /* splines=false for plain: only node positions are needed because X6 draws edges. */
    var base = 'overlap=false, splines=false';
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
    var nodes = g.getNodes().filter(function(n) { return n.shape === 'er-rect'; });
    var idMap  = new Map();
    var lines  = [
      'digraph G {',
      '  graph [' + gvGraphAttrs(mode) + '];',
      '  node  [shape=box, style=invis, label="", margin=0, fixedsize=true];',
      '  edge  [dir=none];',
    ];
    nodes.forEach(function(n) {
      var safe = gvSafeId(String(n.id));
      idMap.set(String(n.id), safe);
      var sz  = n.size();
      var wIn = (Number(sz.width  || NODE_W)  / IN2PX).toFixed(4);
      var hIn = (Number(sz.height || LINE_H*4) / IN2PX).toFixed(4);
      lines.push('  ' + safe + ' [width=' + wIn + ', height=' + hIn + '];');
    });
    var idSet = new Set(nodes.map(function(n) { return String(n.id); }));
    g.getEdges().forEach(function(e) {
      var s = e.getSourceCell && e.getSourceCell();
      var t = e.getTargetCell && e.getTargetCell();
      var si = s && String(s.id);
      var ti = t && String(t.id);
      if (si && ti && si !== ti && idSet.has(si) && idSet.has(ti))
        lines.push('  ' + idMap.get(si) + ' -> ' + idMap.get(ti) + ';');
    });
    lines.push('}');
    return { dot: lines.join('\\n'), idMap: idMap };
  }

  /* Parse Graphviz plain format.
     Specification: https://graphviz.org/docs/outputs/plain/
       graph <scale> <width_in> <height_in>
       node  <name> <cx_in> <cy_in> <w_in> <h_in> ...
     Units are inches. Y=0 is bottom-up, so flip with y_x6 = (graphH - cy) * IN2PX. */
  function parsePlain(raw, idMap) {
    var safeToOrig = new Map();
    idMap.forEach(function(safe, orig) { safeToOrig.set(safe, orig); });

    var nodePos = new Map();   /* origId -> {x, y} top-left corner in px */
    var graphH  = 0;

    String(raw || '').split('\\n').forEach(function(line) {
      var tok = line.trim().split(/\\s+/);
      if (!tok[0]) return;

      if (tok[0] === 'graph' && tok.length >= 4) {
        graphH = parseFloat(tok[3]) || 0;   /* height in inches */
        return;
      }
      if (tok[0] === 'node' && tok.length >= 6) {
        var name  = tok[1];
        var cx_in = parseFloat(tok[2]);
        var cy_in = parseFloat(tok[3]);
        var w_in  = parseFloat(tok[4]);
        var h_in  = parseFloat(tok[5]);
        if (!name || isNaN(cx_in) || isNaN(cy_in)) return;
        /* Y-flip: Graphviz origin is bottom-left, X6 origin is top-left. */
        var cx_px = cx_in * IN2PX;
        var cy_px = (graphH - cy_in) * IN2PX;
        var w_px  = w_in * IN2PX;
        var h_px  = h_in * IN2PX;
        var orig  = safeToOrig.get(name);
        if (orig) nodePos.set(orig, { x: cx_px - w_px / 2, y: cy_px - h_px / 2 });
      }
    });
    return nodePos;
  }

  async function ensureGvApi() {
    if (gvApi) return gvApi;
    var mod = await withTimeout(import(/*GV*/"__GV_URL__"), 'Graphviz import');
    var Cls = (mod.Graphviz) || (mod.default && mod.default.Graphviz) || mod.default;
    if (!Cls || typeof Cls.load !== 'function') throw new Error('Graphviz: no Graphviz.load()');
    gvApi = await withTimeout(Cls.load(), 'Graphviz.load()');
    return gvApi;
  }

  async function layoutGvX6(g, mode) {
    var nodes = g.getNodes().filter(function(n) { return n.shape === 'er-rect'; });
    if (!nodes.length) return true;
    var api;
    try { api = await ensureGvApi(); }
    catch (e) { console.warn('erd: GV api', e); return false; }

    var built = buildGvPlainDot(g, mode);
    var engine = gvEngine(mode);
    var plain;
    try { plain = api.layout(built.dot, 'plain', engine); }
    catch (e) { console.warn('erd: GV layout', e); return false; }

    var nodePos = parsePlain(plain, built.idMap);
    if (!nodePos.size) { console.warn('erd: GV plain: no nodes'); return false; }

    var MARGIN = 80;
    g.batchUpdate(function() {
      nodes.forEach(function(n) {
        var pos = nodePos.get(String(n.id));
        if (!pos) return;
        n.position(Math.max(10, MARGIN + pos.x), Math.max(10, MARGIN + pos.y));
      });
    });
    /* After GV layout, X6 draws edges with its orth router, so reset vertices. */
    refreshAnchors(g, true);
    return true;
  }

  /* ════════════════════════════════════════════════════════════════════
     LAYOUT 2 — ELK
     ════════════════════════════════════════════════════════════════════ */
  function elkOpts(mode) {
    var base = {
      'elk.spacing.nodeNode': '80',
      'elk.spacing.edgeEdge': '20',
      'elk.spacing.edgeNode': '40',
      'elk.padding': '[top=60,left=60,bottom=60,right=60]',
    };
    var ext = {};
    if (mode === 'elk-down') {
      ext = { 'elk.algorithm':'layered','elk.direction':'DOWN','elk.edgeRouting':'ORTHOGONAL',
              'elk.layered.nodePlacement.strategy':'BRANDES_KOEPF',
              'elk.layered.spacing.nodeNodeBetweenLayers':'100',
              'elk.layered.spacing.edgeNodeBetweenLayers':'40' };
    } else if (mode === 'elk-tree') {
      ext = { 'elk.algorithm':'mrtree','elk.direction':'RIGHT' };
    } else if (mode === 'elk-stress') {
      ext = { 'elk.algorithm':'stress','elk.stress.desiredEdgeLength':'280','elk.spacing.nodeNode':'100' };
    } else if (mode === 'elk-force') {
      ext = { 'elk.algorithm':'force','elk.force.repulsivePower':'2','elk.spacing.nodeNode':'120' };
    } else {
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
    if (typeof ELK !== 'function') { console.warn('erd: no ELK'); return false; }
    var elk   = new ELK();
    var nodes = g.getNodes().filter(function(n) { return n.shape === 'er-rect'; });
    if (!nodes.length) return true;
    var idSet = new Set(nodes.map(function(n) { return String(n.id); }));
    var elkG  = {
      id: 'root',
      layoutOptions: elkOpts(mode),
      children: nodes.map(function(n) {
        var sz = n.size();
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
    g.getEdges().forEach(function(e) {
      var s = e.getSourceCell && e.getSourceCell();
      var t = e.getTargetCell && e.getTargetCell();
      var si = s && String(s.id), ti = t && String(t.id);
      if (!si || !ti || si === ti || !idSet.has(si) || !idSet.has(ti)) return;
      elkG.edges.push({ id: String(e.id), sources: [si + '__E'], targets: [ti + '__W'] });
    });
    var layout;
    try { layout = await elk.layout(elkG); }
    catch (e) { console.warn('erd: ELK', mode, e); return false; }

    var byId = new Map(nodes.map(function(n) { return [String(n.id), n]; }));
    (layout.children || []).forEach(function(c) {
      if (c.x != null && c.y != null) { var n = byId.get(String(c.id)); if (n) n.position(c.x, c.y); }
    });
    var eById = new Map(g.getEdges().map(function(e) { return [String(e.id), e]; }));
    (layout.edges || []).forEach(function(le) {
      var edge = eById.get(String(le.id));
      var sec  = Array.isArray(le.sections) ? le.sections[0] : null;
      var bends = (sec && sec.bendPoints) ? sec.bendPoints.map(function(p) { return { x: p.x, y: p.y }; }) : [];
      if (edge && bends.length) {
        edge.setVertices && edge.setVertices(bends);
        edge.setConnector && edge.setConnector({ name: 'rounded', args: { radius: 6 } });
      }
    });
    refreshAnchors(g, false);
    return true;
  }

  /* ════════════════════════════════════════════════════════════════════
     LAYOUT 3 — DAGRE
     ════════════════════════════════════════════════════════════════════ */
  async function layoutDagre(g, rankdir) {
    if (!dagre) { console.warn('erd: no dagre'); return false; }
    var nodes = g.getNodes().filter(function(n) { return n.shape === 'er-rect'; });
    if (!nodes.length) return true;
    var dg = new dagre.graphlib.Graph();
    dg.setDefaultEdgeLabel(function() { return {}; });
    dg.setGraph({ rankdir: rankdir, nodesep: 60, ranksep: 160, edgesep: 30, marginx: 60, marginy: 60 });
    nodes.forEach(function(n) { var sz = n.size(); dg.setNode(String(n.id), { width: sz.width, height: sz.height }); });
    var idSet = new Set(nodes.map(function(n) { return String(n.id); }));
    g.getEdges().forEach(function(e) {
      var s = e.getSourceCell && e.getSourceCell();
      var t = e.getTargetCell && e.getTargetCell();
      var si = s && String(s.id), ti = t && String(t.id);
      if (si && ti && si !== ti && idSet.has(si) && idSet.has(ti)) dg.setEdge(si, ti);
    });
    try { dagre.layout(dg); } catch(e) { console.warn('erd: dagre', e); return false; }
    g.batchUpdate(function() {
      nodes.forEach(function(n) {
        var nd = dg.node(String(n.id));
        if (nd) n.position(nd.x - nd.width / 2, nd.y - nd.height / 2);
      });
    });
    refreshAnchors(g, true);
    return true;
  }

  /* ════════════════════════════════════════════════════════════════════
     LAYOUT 4 — GRID
     ════════════════════════════════════════════════════════════════════ */
  async function layoutGrid(g) {
    var nodes = g.getNodes().filter(function(n) { return n.shape === 'er-rect'; });
    if (!nodes.length) return true;
    var adj = new Map(nodes.map(function(n) { return [String(n.id), new Set()]; }));
    g.getEdges().forEach(function(e) {
      var s = e.getSourceCell && e.getSourceCell();
      var t = e.getTargetCell && e.getTargetCell();
      var si = s && String(s.id), ti = t && String(t.id);
      if (si && ti && si !== ti && adj.has(si) && adj.has(ti)) { adj.get(si).add(ti); adj.get(ti).add(si); }
    });
    var deg = function(id) { return (adj.get(id) && adj.get(id).size) || 0; };
    var components = [], seen = new Set();
    nodes.forEach(function(n) {
      var root = String(n.id);
      if (seen.has(root)) return;
      var ids = [], q = [root]; seen.add(root);
      while (q.length) {
        var id = q.shift(); ids.push(id);
        Array.from(adj.get(id) || []).sort(function(a,b){ return deg(b)-deg(a)||a.localeCompare(b); })
          .forEach(function(x) { if (!seen.has(x)) { seen.add(x); q.push(x); } });
      }
      components.push(ids);
    });
    components.sort(function(a,b){ return b.length - a.length; });
    var byId = new Map(nodes.map(function(n) { return [String(n.id), n]; }));
    var GAP_X = 80, GAP_Y = 60;
    var viewW = Math.max(1280, container.clientWidth || 1280);
    var curX = 80, curY = 80, rowH = 0;
    components.forEach(function(ids) {
      var sizes = ids.map(function(id) { var n = byId.get(id); return n ? n.size() : { width: NODE_W, height: LINE_H * 4 }; });
      var cellW = Math.max.apply(null, sizes.map(function(s){return s.width;}))  + GAP_X;
      var cellH = Math.max.apply(null, sizes.map(function(s){return s.height;})) + GAP_Y;
      var cols  = ids.length <= 3 ? ids.length : Math.min(5, Math.ceil(Math.sqrt(ids.length * 1.4)));
      var compW = cols * cellW;
      if (curX + compW > viewW && curX > 80) { curX = 80; curY += rowH + 100; rowH = 0; }
      var hub = ids.slice().sort(function(a,b){ return deg(b)-deg(a)||a.localeCompare(b); })[0];
      var order = [], ls = new Set([hub]), lq = [hub];
      while (lq.length) {
        var id2 = lq.shift(); order.push(id2);
        Array.from(adj.get(id2) || []).filter(function(x){ return ids.indexOf(x) >= 0; })
          .sort(function(a,b){ return deg(b)-deg(a)||a.localeCompare(b); })
          .forEach(function(x) { if (!ls.has(x)) { ls.add(x); lq.push(x); } });
      }
      ids.filter(function(id){ return !ls.has(id); }).forEach(function(id){ order.push(id); });
      order.forEach(function(id, ix) {
        var row = Math.floor(ix / cols), col = ix % cols;
        var n = byId.get(id); if (n) n.position(curX + col * cellW, curY + row * cellH);
      });
      rowH = Math.max(rowH, Math.ceil(ids.length / cols) * cellH);
      curX += compW + 120;
    });
    refreshAnchors(g, true);
    return true;
  }

  function layoutFallback(g) {
    var nodes = g.getNodes().filter(function(n) { return n.shape === 'er-rect'; });
    nodes.forEach(function(n, i) {
      var ring  = Math.ceil(Math.sqrt(i + 1));
      var angle = i * 137.508 * Math.PI / 180;
      n.position(500 + Math.cos(angle) * (300 + ring * 60), 350 + Math.sin(angle) * (200 + ring * 40));
    });
    refreshAnchors(g, true);
  }

  async function runLayout(g) {
    if (activeLayout === 'grid')     return layoutGrid(g);
    if (activeLayout === 'dagre-lr') return layoutDagre(g, 'LR');
    if (activeLayout === 'dagre-tb') return layoutDagre(g, 'TB');
    if (activeLayout.indexOf('x6-gv-') === 0) return layoutGvX6(g, activeLayout.replace('x6-gv-', ''));
    return layoutElk(g, activeLayout);
  }

  /* ════════════════════════════════════════════════════════════════════
     DIAGRAM BUILDERS (Mermaid / Graphviz SVG / D2)
     ════════════════════════════════════════════════════════════════════ */
  function stableIds(nodes) {
    var used = new Set(), out = new Map();
    nodes.forEach(function(nd, ix) {
      var panel = (nd && nd.data && nd.data.payload_panel) || {};
      var lbl   = String(panel.label || (nd.attrs && nd.attrs.label && nd.attrs.label.text) || nd.id || ('E' + (ix+1)));
      var base  = lbl.replace(/[^A-Za-z0-9_]/g,'_').replace(/^_+|_+$/g,'') || ('E' + (ix+1));
      if (/^[0-9]/.test(base)) base = 'E_' + base;
      var cand = base, n = 2;
      while (used.has(cand)) { cand = base + '_' + n; n++; }
      used.add(cand);
      out.set(String(nd.id), cand);
    });
    return out;
  }
  function simpleType(t) {
    var r = String(t || '').toLowerCase().trim();
    if (!r) return 'string';
    if (r.indexOf('int') >= 0) return 'int';
    if (r.indexOf('float') >= 0 || r.indexOf('decimal') >= 0 || r.indexOf('money') >= 0) return 'float';
    if (r.indexOf('bool') >= 0) return 'boolean';
    if (r.indexOf('date') >= 0 || r.indexOf('time') >= 0) return 'datetime';
    return String(t || '').replace(/[^A-Za-z0-9_]/g,'_').slice(0,48) || 'string';
  }

  /* ── Mermaid ── */
  function mmCardL(c) { return ({one:'||',zero_one:'o|',one_many:'}|',zero_many:'}o'})[String(c||'')] || '||'; }
  function mmCardR(c) { return ({one:'||',zero_one:'|o',one_many:'|{',zero_many:'o{'})[String(c||'')] || '||'; }
  function buildMermaid(doc) {
    var nodes = erdNodes(doc), ids = stableIds(nodes);
    var lines = ['erDiagram'];
    nodes.forEach(function(nd) {
      var id    = ids.get(String(nd.id));
      var names = Array.isArray(nd.data && nd.data.lod_port_names) ? nd.data.lod_port_names : [];
      var types = Array.isArray(nd.data && nd.data.lod_port_types) ? nd.data.lod_port_types : [];
      var roles = Array.isArray(nd.data && nd.data.lod_port_roles) ? nd.data.lod_port_roles : [];
      lines.push('  ' + id + ' {');
      if (!names.length) lines.push('    string id PK');
      names.forEach(function(nm, i) {
        var typ   = simpleType(types[i]);
        var field = String(nm || ('f' + i)).replace(/[^A-Za-z0-9_]/g,'_') || ('f' + i);
        var rr    = String(roles[i] || '');
        var role  = rr.indexOf('PK') >= 0 ? ' PK' : rr.indexOf('FK') >= 0 ? ' FK' : '';
        lines.push('    ' + typ + ' ' + field + role);
      });
      lines.push('  }');
    });
    erdEdges(doc).forEach(function(e) {
      var s = ids.get(srcId(e)), t = ids.get(tgtId(e));
      if (!s || !t) return;
      var p   = ePanel(e);
      var lbl = String(p.source_field || p.label || 'rel').replace(/"/g,"'").trim();
      lines.push('  ' + s + ' ' + mmCardL(p.source_cardinality) + '--' + mmCardR(p.target_cardinality) + ' ' + t + ' : "' + (lbl || 'rel') + '"');
    });
    return lines.join('\\n');
  }

  /* ── Graphviz SVG (full HTML-label DOT) ── */
  function gvCardLabel(c) { return ({one:'||',zero_one:'o|',one_many:'|<',zero_many:'o<'})[String(c||'')] || ''; }
  function gvGAttrs(mode) {
    var base = 'overlap=false, splines=ortho, bgcolor="#f4f5f7"';
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
    var nodes = erdNodes(doc), ids = stableIds(nodes);
    var engine = gvEngine(mode);
    var nodeByGvId = new Map();
    var edgeByGvId = new Map();
    var lines = [
      'digraph ERD {',
      '  graph [' + gvGAttrs(mode) + ', fontname="Arial"];',
      '  node  [shape=plain, fontname="Arial", fontsize=11];',
      '  edge  [fontname="Arial", fontsize=10, color="#374151", dir=none, penwidth=1.5];',
      '',
    ];
    nodes.forEach(function(nd) {
      var id    = gvSafeId(ids.get(String(nd.id)));
      var panel = nPanel(nd);
      nodeByGvId.set(id, nd);
      var lbl   = esc(String(panel.label || id)).replace(/"/g,'&quot;');
      var names = Array.isArray(nd.data && nd.data.lod_port_names) ? nd.data.lod_port_names : [];
      var types = Array.isArray(nd.data && nd.data.lod_port_types) ? nd.data.lod_port_types : [];
      var roles = Array.isArray(nd.data && nd.data.lod_port_roles) ? nd.data.lod_port_roles : [];
      var rows  = ['<TR><TD BGCOLOR="#1e3a5f" COLSPAN="3" ALIGN="CENTER"><FONT COLOR="white"><B>' + lbl + '</B></FONT></TD></TR>'];
      if (!names.length) rows.push('<TR><TD BGCOLOR="#fff3cd"><B>PK</B></TD><TD>id</TD><TD><I>str</I></TD></TR>');
      names.forEach(function(nm, i) {
        var rr  = String(roles[i] || '');
        var isPk = rr.indexOf('PK') >= 0, isFk = rr.indexOf('FK') >= 0;
        var badge = isPk && isFk ? '<B>PK,FK</B>' : isPk ? '<B>PK</B>' : isFk ? 'FK' : '';
        var bg    = isPk ? '#fff3cd' : isFk ? '#e8f4f8' : '#f9fafb';
        var fn    = esc(String(nm || ('f' + i)));
        var ft    = esc(String(types[i] || ''));
        rows.push('<TR><TD BGCOLOR="' + bg + '">' + badge + '</TD><TD ALIGN="LEFT">' + fn + '</TD><TD ALIGN="LEFT"><I>' + ft + '</I></TD></TR>');
      });
      lines.push('  ' + id + ' [id=' + JSON.stringify('gv-node-' + id) + ', tooltip=' + JSON.stringify(String(panel.label || id)) + ', label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5" COLOR="#374151">');
      rows.forEach(function(r){ lines.push('    ' + r); });
      lines.push('  </TABLE>>];');
      lines.push('');
    });
    erdEdges(doc).forEach(function(e, ix) {
      var s = gvSafeId(ids.get(srcId(e))), t = gvSafeId(ids.get(tgtId(e)));
      if (!s || !t) return;
      var edgeId = 'gv-edge-' + gvSafeId(String(e.id || (s + '_' + t + '_' + ix)));
      edgeByGvId.set(edgeId, e);
      var p   = ePanel(e);
      var lbl = String(p.source_field || p.label || '').trim();
      var tail = gvCardLabel(p.source_cardinality);
      var head = gvCardLabel(p.target_cardinality);
      var lp   = lbl ? (', label=' + JSON.stringify(lbl)) : '';
      lines.push('  ' + s + ' -> ' + t + ' [id=' + JSON.stringify(edgeId) + ', tooltip=' + JSON.stringify(lbl || p.relationship_kind || 'relationship') + ', taillabel=' + JSON.stringify(tail) + ', headlabel=' + JSON.stringify(head) + lp + '];');
    });
    lines.push('}');
    return { dot: lines.join('\\n'), engine: engine, nodeByGvId: nodeByGvId, edgeByGvId: edgeByGvId };
  }

  /* ── D2 ── */
  function buildD2(doc) {
    var nodes = erdNodes(doc), ids = stableIds(nodes);
    var fieldMap = new Map();
    var lines = ['direction: right', ''];
    nodes.forEach(function(nd) {
      var id    = gvSafeId(ids.get(String(nd.id)));
      var names = Array.isArray(nd.data && nd.data.lod_port_names) ? nd.data.lod_port_names : [];
      var types = Array.isArray(nd.data && nd.data.lod_port_types) ? nd.data.lod_port_types : [];
      var roles = Array.isArray(nd.data && nd.data.lod_port_roles) ? nd.data.lod_port_roles : [];
      var lf = new Map();
      lines.push(id + ': {', '  shape: sql_table');
      if (!names.length) lines.push('  id: string {constraint: primary_key}');
      names.forEach(function(nm, i) {
        var raw = String(nm || ('f' + i)).replace(/[^A-Za-z0-9_]/g,'_') || ('f' + i);
        var fld = /^[0-9]/.test(raw) ? 'f_' + raw : raw;
        var typ = String(types[i] || '').indexOf('FK') >= 0 ? 'string' : simpleType(types[i]);
        var rr  = String(roles[i] || '');
        var con = (rr.indexOf('PK') >= 0 && rr.indexOf('FK') >= 0) ? '{constraint: [primary_key; foreign_key]}'
                : rr.indexOf('PK') >= 0 ? '{constraint: primary_key}'
                : rr.indexOf('FK') >= 0 ? '{constraint: foreign_key}' : '';
        lf.set(String(nm || ''), fld);
        lines.push('  ' + fld + ': ' + typ + (con ? ' ' + con : ''));
      });
      fieldMap.set(String(nd.id), lf);
      lines.push('}', '');
    });
    erdEdges(doc).forEach(function(e) {
      var sR = srcId(e), tR = tgtId(e);
      var s  = gvSafeId(ids.get(sR)), t = gvSafeId(ids.get(tR));
      if (!s || !t) return;
      var p  = ePanel(e);
      var sf = String(p.source_field || '');
      var sfld = (fieldMap.get(sR) && fieldMap.get(sR).get(sf)) || 'id';
      lines.push(s + '.' + sfld + ' -> ' + t + '.id');
    });
    return lines.join('\\n');
  }

  /* ── API loaders ── */
  async function ensureMermaid() {
    if (mmApi) return mmApi;
    var m = await import(/*MM*/"__MM_URL__");
    mmApi = m.default || m;
    if (typeof mmApi.initialize === 'function')
      mmApi.initialize({ startOnLoad: false, securityLevel: 'loose', theme: 'base', er: { useMaxWidth: false } });
    return mmApi;
  }
  async function ensureD2() {
    if (d2Api) return d2Api;
    var m   = await withTimeout(import(/*D2*/"__D2_URL__"), 'D2 import');
    var Cls = m.D2 || (m.default && m.default.D2) || m.default;
    if (!Cls) throw new Error('D2: no D2 export');
    d2Api = new Cls();
    if (typeof d2Api.ready === 'function') await withTimeout(d2Api.ready(), 'D2 ready', 15000);
    return d2Api;
  }

  /* ── Render functions ── */
  var mmCont   = document.getElementById('mermaid-container');
  var gvCont   = document.getElementById('graphviz-container');
  var d2Cont   = document.getElementById('d2-container');
  var d2SrcCont = document.getElementById('d2-source-container');
  var gvSvgState = null;
  var gvView = { base: null, viewBox: null, dragging: false, lastX: 0, lastY: 0 };

  function closestGvItem(target) {
    if (!target || !gvCont) return null;
    var el = target.closest && target.closest('[data-gv-kind]');
    return el && gvCont.contains(el) ? el : null;
  }

  function indexGvSvg(svgEl, built) {
    var nodeByEl = new Map();
    var edgeByEl = new Map();
    if (!svgEl) return { svg: null, nodeByEl: nodeByEl, edgeByEl: edgeByEl };

    built.nodeByGvId.forEach(function(node, id) {
      var g = svgEl.querySelector('#gv-node-' + id);
      if (!g) g = Array.prototype.find.call(svgEl.querySelectorAll('g.node'), function(item) {
        return (item.querySelector('title') && item.querySelector('title').textContent) === id;
      });
      if (!g) return;
      g.setAttribute('data-gv-kind', 'node');
      g.setAttribute('data-gv-id', id);
      g.setAttribute('tabindex', '0');
      g.style.cursor = 'pointer';
      nodeByEl.set(g, node);
    });

    built.edgeByGvId.forEach(function(edge, id) {
      var g = svgEl.querySelector('#' + id);
      if (!g) return;
      g.setAttribute('data-gv-kind', 'edge');
      g.setAttribute('data-gv-id', id);
      g.setAttribute('tabindex', '0');
      g.style.cursor = 'pointer';
      edgeByEl.set(g, edge);
    });

    return { svg: svgEl, nodeByEl: nodeByEl, edgeByEl: edgeByEl };
  }

  function parseSvgViewBox(svgEl) {
    if (!svgEl) return null;
    var raw = String(svgEl.getAttribute('viewBox') || '').trim().split(/[\\s,]+/).map(Number);
    if (raw.length >= 4 && raw.every(function(n) { return Number.isFinite(n); })) {
      return { x: raw[0], y: raw[1], w: raw[2], h: raw[3] };
    }
    var w = parseFloat(svgEl.getAttribute('width') || '0');
    var h = parseFloat(svgEl.getAttribute('height') || '0');
    return (w && h) ? { x: 0, y: 0, w: w, h: h } : null;
  }

  function setGvViewBox(vb) {
    if (!gvSvgState || !gvSvgState.svg || !vb) return;
    gvView.viewBox = { x: vb.x, y: vb.y, w: vb.w, h: vb.h };
    gvSvgState.svg.setAttribute('viewBox', [vb.x, vb.y, vb.w, vb.h].join(' '));
    syncZoom();
  }

  function fitGvView() {
    if (!gvView.base) return;
    setGvViewBox(gvView.base);
  }

  function zoomGvView(factor, cx, cy) {
    if (!gvSvgState || !gvSvgState.svg || !gvView.viewBox) return;
    var rect = gvSvgState.svg.getBoundingClientRect();
    var vb = gvView.viewBox;
    var relX = rect.width ? (cx - rect.left) / rect.width : 0.5;
    var relY = rect.height ? (cy - rect.top) / rect.height : 0.5;
    var anchorX = vb.x + vb.w * relX;
    var anchorY = vb.y + vb.h * relY;
    var nextW = vb.w / factor;
    var nextH = vb.h / factor;
    setGvViewBox({
      x: anchorX - nextW * relX,
      y: anchorY - nextH * relY,
      w: nextW,
      h: nextH,
    });
  }

  function clearGvHighlight() {
    if (!gvSvgState || !gvSvgState.svg) return;
    gvSvgState.svg.querySelectorAll('.gv-hover, .gv-related, .gv-dim').forEach(function(el) {
      el.classList.remove('gv-hover', 'gv-related', 'gv-dim');
    });
  }

  function setGvHighlight(el) {
    clearGvHighlight();
    if (!el || !gvSvgState || !gvSvgState.svg) return;
    var kind = el.getAttribute('data-gv-kind');
    el.classList.add('gv-hover');
    if (kind === 'node') {
      var node = gvSvgState.nodeByEl.get(el);
      var nodeId = node && String(node.id);
      var relatedIds = new Set([nodeId]);
      gvSvgState.edgeByEl.forEach(function(edge, edgeEl) {
        if (srcId(edge) === nodeId || tgtId(edge) === nodeId) {
          edgeEl.classList.add('gv-related');
          relatedIds.add(srcId(edge));
          relatedIds.add(tgtId(edge));
        }
      });
      gvSvgState.nodeByEl.forEach(function(item, nodeEl) {
        if (relatedIds.has(String(item.id))) nodeEl.classList.add('gv-related');
      });
    }
  }

  function gvPayloadForEl(el) {
    if (!el || !gvSvgState) return null;
    if (el.getAttribute('data-gv-kind') === 'node') {
      var node = gvSvgState.nodeByEl.get(el);
      return node ? { panel: nPanel(node), title: nPanel(node).label || node.id } : null;
    }
    if (el.getAttribute('data-gv-kind') === 'edge') {
      var edge = gvSvgState.edgeByEl.get(el);
      var panel = edge ? ePanel(edge) : null;
      return edge ? { panel: panel, title: panel.source_field || panel.label || panel.relationship_kind || edge.id } : null;
    }
    return null;
  }

  async function renderMermaid(doc) {
    mmCont.innerHTML = '<div class="erd-loading">Rendering Mermaid\u2026</div>';
    var src = buildMermaid(doc);
    try {
      var api = await ensureMermaid();
      var id  = 'mm-' + Date.now();
      var r   = await withTimeout(api.render(id, src), 'Mermaid render');
      mmCont.innerHTML = r.svg || String(r);
    } catch(e) {
      mmCont.innerHTML = '<pre class="erd-error">' + esc(String(e && e.message || e)) + '\\n\\n' + esc(src) + '</pre>';
    }
  }
  async function renderGvSvg(doc) {
    var built = buildGvFullDot(doc, activeGvLayout);
    gvCont.innerHTML = '<div class="erd-loading">Rendering Graphviz (' + built.engine + ')\u2026</div>';
    try {
      var api = await ensureGvApi();
      var svg = api.layout(built.dot, 'svg', built.engine);
      if (!svg) throw new Error('empty SVG');
      gvCont.innerHTML = svg;
      var svgEl = gvCont.querySelector('svg');
      if (svgEl) {
        if (!svgEl.getAttribute('viewBox')) {
          var w = parseFloat(svgEl.getAttribute('width')  || '0');
          var h = parseFloat(svgEl.getAttribute('height') || '0');
          if (w && h) svgEl.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
        }
        svgEl.removeAttribute('width'); svgEl.removeAttribute('height');
        svgEl.style.width = '100%';
        svgEl.style.height = 'auto';
      }
      gvSvgState = indexGvSvg(svgEl, built);
      gvView.base = parseSvgViewBox(svgEl);
      gvView.viewBox = gvView.base && { x: gvView.base.x, y: gvView.base.y, w: gvView.base.w, h: gvView.base.h };
      syncZoom();
    } catch(e) {
      gvSvgState = null;
      gvView.base = null;
      gvView.viewBox = null;
      gvCont.innerHTML = '<pre class="erd-error">' + esc(String(e && e.message || e)) + '\\n\\n' + esc(built.dot) + '</pre>';
    }
  }
  async function renderD2(doc) {
    d2Cont.innerHTML = '<div class="erd-loading">Rendering D2\u2026</div>';
    var src = buildD2(doc);
    try {
      var api = await ensureD2();
      var svg;
      if (typeof api.layout === 'function') {
        svg = await withTimeout(api.layout(src), 'D2 layout', 30000);
      } else if (typeof api.compile === 'function') {
        var res = await withTimeout(api.compile(src, { layout: 'dagre' }), 'D2 compile', 30000);
        if (typeof res === 'string') svg = res;
        else if (res && typeof res.svg === 'string') svg = res.svg;
        else if (res && res.diagram && typeof api.render === 'function')
          svg = await withTimeout(api.render(res.diagram, Object.assign({}, res.renderOptions || {}, { noXMLTag: true })), 'D2 render', 15000);
        else throw new Error('D2: unexpected compile() return');
      } else throw new Error('D2: no usable API');
      if (!svg || typeof svg !== 'string') throw new Error('D2: empty SVG');
      d2Cont.innerHTML = svg;
    } catch(e) {
      d2Cont.innerHTML = '<pre class="erd-error">D2 failed.\\n' + esc(String(e && e.message || e)) + '\\n\\nD2 source:\\n' + esc(src) + '</pre>';
    }
  }
  function renderD2Src(doc) { d2SrcCont.textContent = buildD2(doc); }

  function resetGvState() {
    gvSvgState = null;
    gvView.base = null;
    gvView.viewBox = null;
    gvView.dragging = false;
    if (gvCont) gvCont.classList.remove('is-panning');
  }

  /* ── Pickers ── */
  var rendererModes = [
    { id: 'x6',        label: 'X6 (interactive)' },
    { id: 'mermaid',   label: 'Mermaid'           },
    { id: 'graphviz',  label: 'Graphviz SVG'      },
    { id: 'd2',        label: 'D2'                },
    { id: 'd2-source', label: 'D2 source'         },
  ];
  var layoutModes = [
    { id: 'x6-gv-dot-lr', label: 'GV Dot LR \u2756' },
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
  var gvLayoutModes = [
    { id: 'dot-lr', label: 'Dot LR \u2756' },
    { id: 'dot-tb', label: 'Dot TB'  },
    { id: 'neato',  label: 'Neato'   },
    { id: 'fdp',    label: 'FDP'     },
    { id: 'sfdp',   label: 'SFDP'    },
    { id: 'circo',  label: 'Circo'   },
    { id: 'twopi',  label: 'Twopi'   },
    { id: 'osage',  label: 'Osage'   },
  ];

  var domPicker = document.getElementById('domain-picker');
  var renPicker = document.getElementById('renderer-picker');
  var layPicker = document.getElementById('layout-picker');

  function renderDomainPicker() {
    if (!domPicker) return;
    if (domList.length <= 1) { domPicker.style.display = 'none'; return; }
    domPicker.style.display = 'flex';
    domPicker.innerHTML = '<div class="legend-title">Domains</div>' +
      domList.map(function(d) {
        var icon = d.iconSrc ? '<img class="legend-icon" src="' + d.iconSrc + '" width="18" height="18" alt="">' : '';
        return '<button type="button" class="domain-row' + (d.id === activeDomain ? ' is-active' : '') + '" data-did="' + d.id + '">' + icon + '<span>' + esc(d.label || d.id) + '</span></button>';
      }).join('');
  }
  function renderRendererPicker() {
    if (!renPicker) return;
    renPicker.style.display = 'flex';
    renPicker.innerHTML = '<div class="legend-title">Renderer</div>' +
      rendererModes.map(function(m) {
        return '<button type="button" class="renderer-row' + (m.id === activeRenderer ? ' is-active' : '') + '" data-rid="' + m.id + '"><span>' + esc(m.label) + '</span></button>';
      }).join('');
  }
  function renderLayoutPicker() {
    if (!layPicker) return;
    var isX6 = activeRenderer === 'x6', isGv = activeRenderer === 'graphviz';
    var modes = isX6 ? layoutModes : isGv ? gvLayoutModes : [];
    layPicker.style.display = modes.length ? 'flex' : 'none';
    if (!modes.length) return;
    var actId = isGv ? activeGvLayout : activeLayout;
    layPicker.innerHTML = '<div class="legend-title">' + (isGv ? 'Graphviz Layout' : 'X6 Layout') + '</div>' +
      modes.map(function(m) {
        return '<button type="button" class="layout-row' + (m.id === actId ? ' is-active' : '') + '" data-lid="' + m.id + '"><span>' + esc(m.label) + '</span></button>';
      }).join('');
  }

  /* ── Tooltip ── */
  var tipEl = document.getElementById('erd-hover-tip');
  var tipTimer = null;
  function hideTip() {
    if (tipTimer != null) { clearTimeout(tipTimer); tipTimer = null; }
    if (tipEl) { tipEl.style.display = 'none'; tipEl.setAttribute('aria-hidden','true'); }
  }
  function showTip(cx, cy, txt) {
    if (!tipEl || !txt) return;
    hideTip();
    tipEl.textContent = txt;
    tipEl.style.display = 'block';
    tipEl.setAttribute('aria-hidden','false');
    var pw = tipEl.offsetWidth || 360, ph = tipEl.offsetHeight || 44, pad = 8;
    var x = cx + 14, y = cy + 14;
    if (x + pw + pad > window.innerWidth)  x = Math.max(pad, window.innerWidth  - pw - pad);
    if (y + ph + pad > window.innerHeight) y = Math.max(pad, window.innerHeight - ph - pad);
    tipEl.style.left = x + 'px'; tipEl.style.top = y + 'px';
  }
  function scheduleTipHide() {
    if (tipTimer != null) clearTimeout(tipTimer);
    tipTimer = setTimeout(function() { hideTip(); tipTimer = null; }, 160);
  }

  /* ── Detail panel ── */
  var detailShell = document.getElementById('node-detail-shell');
  var detailBody  = document.getElementById('node-detail-body');
  var detailTitle = document.getElementById('node-detail-title');
  var COPY_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
  function closeDetail() {
    if (detailShell) { detailShell.classList.remove('is-open'); detailShell.setAttribute('aria-hidden','true'); }
    if (detailBody) detailBody.innerHTML = '';
  }
  function showDetailPanel(panel, title) {
    if (!detailShell || !detailBody || !panel) return;
    panel = (panel && typeof panel === 'object' && !Array.isArray(panel)) ? panel : {};
    title = String(title || panel.label || panel.id || '');
    var html = '<h2 class="properties-entity-name is-kind">' + esc(title) + '</h2>';
    Object.keys(panel).sort().forEach(function(k) {
      var v = panel[k] == null ? '' : (typeof panel[k] === 'object' ? JSON.stringify(panel[k]) : String(panel[k]));
      var multi = v.length > 140 || /[\\r\\n]/.test(v);
      html += '<div class="prop-block"><div class="prop-label">' + esc(k) + '</div>';
      if (multi) html += '<div class="prop-value prop-value-multiline">' + esc(v) + '</div>';
      else {
        html += '<div class="prop-value prop-value-row"><span style="flex:1">' + esc(v) + '</span>';
        if (v) html += '<button type="button" class="copy-btn" data-copy="' + encodeURIComponent(v) + '" title="Copy">' + COPY_SVG + '</button>';
        html += '</div>';
      }
      html += '</div>';
    });
    detailBody.innerHTML = html;
    if (detailTitle) detailTitle.textContent = title || 'Entity';
    detailShell.classList.add('is-open');
    detailShell.setAttribute('aria-hidden','false');
  }
  function showDetail(cell) {
    if (!cell) return;
    var raw   = (cell.getData && cell.getData()) || {};
    var panel = (raw && raw.payload_panel && typeof raw.payload_panel === 'object' && !Array.isArray(raw.payload_panel)) ? raw.payload_panel : {};
    var title = (cell.isNode && cell.isNode() && cell.shape === 'er-rect')
      ? (String(cell.attr('label/text') || '').trim() || String(panel.label || panel.id || cell.id || ''))
      : String(panel.label || panel.id || cell.id || '');
    showDetailPanel(panel, title);
  }
  if (detailShell) {
    detailShell.addEventListener('click', function(e) {
      var btn = e.target.closest('.copy-btn');
      if (btn) { try { navigator.clipboard && navigator.clipboard.writeText(decodeURIComponent(btn.getAttribute('data-copy') || '')); } catch(_) {} }
    });
  }
  var closeBtn = document.getElementById('node-detail-close');
  if (closeBtn) closeBtn.addEventListener('click', function(e) { e.stopPropagation(); closeDetail(); });

  if (gvCont) {
    gvCont.addEventListener('wheel', function(e) {
      if (activeRenderer !== 'graphviz') return;
      e.preventDefault();
      zoomGvView(Math.exp(-e.deltaY * WHL_K), e.clientX, e.clientY);
    }, { passive: false });
    gvCont.addEventListener('pointerdown', function(e) {
      if (activeRenderer !== 'graphviz' || !gvView.viewBox || closestGvItem(e.target)) return;
      gvView.dragging = true;
      gvView.lastX = e.clientX;
      gvView.lastY = e.clientY;
      gvCont.setPointerCapture && gvCont.setPointerCapture(e.pointerId);
      gvCont.classList.add('is-panning');
    });
    gvCont.addEventListener('pointermove', function(e) {
      if (!gvView.dragging || !gvSvgState || !gvSvgState.svg || !gvView.viewBox) return;
      var rect = gvSvgState.svg.getBoundingClientRect();
      var dx = e.clientX - gvView.lastX;
      var dy = e.clientY - gvView.lastY;
      gvView.lastX = e.clientX;
      gvView.lastY = e.clientY;
      setGvViewBox({
        x: gvView.viewBox.x - dx * gvView.viewBox.w / Math.max(1, rect.width),
        y: gvView.viewBox.y - dy * gvView.viewBox.h / Math.max(1, rect.height),
        w: gvView.viewBox.w,
        h: gvView.viewBox.h,
      });
    });
    ['pointerup', 'pointercancel', 'pointerleave'].forEach(function(name) {
      gvCont.addEventListener(name, function(e) {
        if (!gvView.dragging) return;
        gvView.dragging = false;
        try { gvCont.releasePointerCapture && gvCont.releasePointerCapture(e.pointerId); } catch (_) {}
        gvCont.classList.remove('is-panning');
      });
    });
    gvCont.addEventListener('click', function(e) {
      var el = closestGvItem(e.target);
      if (!el) { closeDetail(); clearGvHighlight(); return; }
      var payload = gvPayloadForEl(el);
      if (payload) showDetailPanel(payload.panel, payload.title);
      setGvHighlight(el);
    });
    gvCont.addEventListener('mousemove', function(e) {
      var el = closestGvItem(e.target);
      if (!el) { hideTip(); clearGvHighlight(); return; }
      setGvHighlight(el);
      var payload = gvPayloadForEl(el);
      if (payload && payload.title) showTip(e.clientX, e.clientY, payload.title);
    });
    gvCont.addEventListener('mouseleave', function() {
      hideTip();
      clearGvHighlight();
    });
  }

  /* ── Graph events ── */
  graph.on('blank:click',     function() { closeDetail(); hideTip(); });
  graph.on('blank:mousemove', hideTip);
  graph.on('cell:click', function(arg) {
    var cell = arg.cell;
    if (!cell || !cell.id) return;
    var d = (cell.getData && cell.getData()) || {};
    if (d && d.payload_panel && typeof d.payload_panel === 'object') showDetail(cell);
  });
  graph.on('node:port:mouseenter', function(arg) {
    if (tipTimer != null) { clearTimeout(tipTimer); tipTimer = null; }
    var node = arg.node, port = arg.port, e = arg.e;
    if (!node || node.shape !== 'er-rect') return;
    var pid = port && port.id != null ? String(port.id) : '';
    if (!pid) return;
    var dd    = (node.getData && node.getData()) || {};
    var names = Array.isArray(dd.lod_port_names) ? dd.lod_port_names : [];
    var types = Array.isArray(dd.lod_port_types) ? dd.lod_port_types : [];
    var roles = Array.isArray(dd.lod_port_roles) ? dd.lod_port_roles : [];
    var ports = (node.getPorts ? node.getPorts() : []).filter(function(p){ return p.group === 'list'; });
    var ix    = ports.findIndex(function(p){ return String(p.id) === pid; });
    if (ix < 0) return;
    var tip = [roles[ix], names[ix], types[ix]].filter(Boolean).join('\\n');
    if (tip) showTip(e.clientX, e.clientY, tip);
  });
  graph.on('node:port:mouseleave', scheduleTipHide);
  graph.on('node:mousemove', function(arg) {
    var node = arg.node, e = arg.e;
    if (!node || node.shape !== 'er-rect') return;
    if (e.target instanceof Element && e.target.closest && e.target.closest('[class*="x6-port"]')) return;
    var dd   = (node.getData && node.getData()) || {};
    var full = String((dd.payload_panel && dd.payload_panel.label) || '').trim();
    if (full && full.length > 24) showTip(e.clientX, e.clientY, full);
  });
  graph.on('node:mouseleave', scheduleTipHide);

  /* ── Zoom ── */
  var zoomPct = document.getElementById('zoom-pct');
  function curScale() { return (graph.transform && graph.transform.getScale && graph.transform.getScale().sx) || 1; }
  function clamp(s)   { return Math.min(MAX_SC, Math.max(MIN_SC, s)); }
  function setZoom(s) {
    var next = clamp(s);
    if (typeof graph.zoomTo === 'function') { graph.zoomTo(next); return; }
    graph.zoom(next / (curScale() || 1));
  }
  function syncZoom() {
    if (!zoomPct) return;
    if (activeRenderer === 'graphviz' && gvView.base && gvView.viewBox) {
      zoomPct.textContent = Math.round((gvView.base.w / gvView.viewBox.w) * 100) + '%';
      return;
    }
    zoomPct.textContent = Math.round(curScale() * 100) + '%';
  }

  graph.on('scale',     function() { syncZoom(); applyLod(curScale() <= 0.6 ? 'overview' : 'detailed'); });
  graph.on('translate', function() { syncZoom(); hideTip(); });

  var wheelAcc = 0, wheelRaf = null;
  function flushWheel() {
    wheelRaf = null;
    if (activeRenderer !== 'x6') { wheelAcc = 0; return; }
    setZoom(curScale() * Math.exp(-Math.max(-120, Math.min(120, wheelAcc)) * WHL_K));
    wheelAcc = 0; syncZoom();
  }
  container.addEventListener('wheel', function(e) {
    e.preventDefault(); wheelAcc += e.deltaY;
    if (wheelRaf == null) wheelRaf = requestAnimationFrame(flushWheel);
  }, { passive: false });

  function doZoom(f) {
    if (activeRenderer === 'graphviz') {
      var rect = gvSvgState && gvSvgState.svg ? gvSvgState.svg.getBoundingClientRect() : null;
      zoomGvView(f, rect ? rect.left + rect.width / 2 : window.innerWidth / 2, rect ? rect.top + rect.height / 2 : window.innerHeight / 2);
      return;
    }
    if (activeRenderer === 'x6') { setZoom(curScale() * f); syncZoom(); }
  }
  var ziBtn = document.getElementById('btn-zoom-in');
  var zoBtn = document.getElementById('btn-zoom-out');
  var zfBtn = document.getElementById('btn-zoom-fit');
  if (ziBtn) ziBtn.addEventListener('click', function() { doZoom(1.25); });
  if (zoBtn) zoBtn.addEventListener('click', function() { doZoom(0.80); });
  if (zfBtn) zfBtn.addEventListener('click', function() {
    if (activeRenderer === 'graphviz') { fitGvView(); return; }
    if (activeRenderer !== 'x6') return;
    graph.zoomToFit({ padding: { top: 72, right: 280, bottom: 80, left: 80 }, maxScale: 1.1 });
    syncZoom();
    applyLod(curScale() <= 0.6 ? 'overview' : 'detailed', true);
  });

  /* ── Main render ── */
  async function renderAll() {
    hideTip();
    var doc  = activeDoc();
    var isX6 = activeRenderer === 'x6';
    var isGv = activeRenderer === 'graphviz';
    container.style.display = isX6 ? 'block' : 'none';
    if (mmCont)    mmCont.style.display    = activeRenderer === 'mermaid'   ? 'block' : 'none';
    if (gvCont)    gvCont.style.display    = isGv                           ? 'block' : 'none';
    if (d2Cont)    d2Cont.style.display    = activeRenderer === 'd2'        ? 'block' : 'none';
    if (d2SrcCont) d2SrcCont.style.display = activeRenderer === 'd2-source' ? 'block' : 'none';
    if (layPicker) layPicker.style.display = (isX6 || isGv)                 ? 'flex'  : 'none';
    if (!isX6) {
      graph.resetCells && graph.resetCells([]);
      if (activeRenderer === 'mermaid')   await renderMermaid(doc);
      if (isGv)                           await renderGvSvg(doc);
      if (activeRenderer === 'd2')        await renderD2(doc);
      if (activeRenderer === 'd2-source') renderD2Src(doc);
      syncZoom(); return;
    }
    resetGvState();
    graph.resetCells && graph.resetCells([]);
    graph.fromJSON(doc);
    await new Promise(function(r) { requestAnimationFrame(r); });
    var ok = await runLayout(graph);
    if (!ok) layoutFallback(graph);
    graph.zoomToFit({ padding: { top: 72, right: 280, bottom: 80, left: 80 }, maxScale: 1.1 });
    syncZoom();
    applyLod(curScale() <= 0.6 ? 'overview' : 'detailed', true);
  }

  /* ── Picker events ── */
  if (domPicker) domPicker.addEventListener('click', async function(e) {
    var btn = e.target.closest('[data-did]');
    if (!btn) return;
    var did = btn.getAttribute('data-did');
    if (!did || did === activeDomain || !docMap[did]) return;
    activeDomain = did; closeDetail(); hideTip();
    renderDomainPicker(); await renderAll();
  });
  if (renPicker) renPicker.addEventListener('click', async function(e) {
    var btn = e.target.closest('[data-rid]');
    if (!btn) return;
    var rid = btn.getAttribute('data-rid');
    if (!rid || rid === activeRenderer || !rendererModes.some(function(m){ return m.id === rid; })) return;
    activeRenderer = rid; closeDetail(); hideTip();
    renderRendererPicker(); renderLayoutPicker(); await renderAll();
  });
  if (layPicker) layPicker.addEventListener('click', async function(e) {
    var btn = e.target.closest('[data-lid]');
    if (!btn) return;
    var lid = btn.getAttribute('data-lid');
    if (activeRenderer === 'graphviz') {
      if (!lid || lid === activeGvLayout || !gvLayoutModes.some(function(m){ return m.id === lid; })) return;
      activeGvLayout = lid;
    } else {
      if (!lid || lid === activeLayout || !layoutModes.some(function(m){ return m.id === lid; })) return;
      activeLayout = lid;
    }
    closeDetail(); hideTip(); renderLayoutPicker(); await renderAll();
  });

  window.addEventListener('resize', function() {
    if (activeRenderer !== 'x6') return;
    graph.resize(container.clientWidth, container.clientHeight); syncZoom();
  });

  /* ── Init ── */
  renderDomainPicker(); renderRendererPicker(); renderLayoutPicker();
  await renderAll();
  syncZoom();

})();
"""


def _make_bootstrap(model_json: str) -> str:
    """Inject URL constants into JS without json.dumps quotes inside import()."""
    js = _ERD_BOOTSTRAP_JS
    js = js.replace("__X6_URL__",    X6_MODULE_URL)
    js = js.replace("__ELK_URL__",   ELK_MODULE_URL)
    js = js.replace("__DAGRE_URL__", DAGRE_MODULE_URL)
    js = js.replace("__MM_URL__",    MERMAID_MODULE_URL)
    js = js.replace("__GV_URL__",    GRAPHVIZ_MODULE_URL)
    js = js.replace("__D2_URL__",    D2_MODULE_URL)
    js = js.replace("__MODEL_JSON__", model_json)
    return js


def write_erd_html(
    document: dict[str, Any],
    *,
    output_path: str | Path | None = None,
    title: str = "Entity diagram",
    width: str = "100%",
    height: str = "100vh",
) -> Path:
    """Write standalone ERD HTML from an X6 ``{cells: [...]}`` document."""
    payload = copy.deepcopy(document)
    if "cells" not in payload:
        raise TypeError('write_erd_html expects document with top-level "cells"')
    model_json = json.dumps({
        "domains":         [{"id": "default", "label": "Default", "iconSrc": ""}],
        "documents":       {"default": payload},
        "initialDomainId": "default",
    }, ensure_ascii=False)
    out = DEFAULT_ERD_HTML_PATH if output_path is None else Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = (
        _template_raw()
        .replace("@@HTML_ESCAPED_TITLE@@", html_escape(title))
        .replace("@@CONTAINER_WIDTH@@",    width)
        .replace("@@CONTAINER_HEIGHT@@",   height)
        .replace("@@INLINE_ERD_SCRIPT@@",  _make_bootstrap(model_json).strip())
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
    """Derive ERD cells from coordinator interchange graph and write standalone HTML."""
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
    domain_documents: dict[str, dict[str, Any]] = {}
    domain_items:     list[dict[str, str]]       = []
    initial_domain_id: str | None = None

    for dnode in domain_nodes:
        dcls      = dnode.node_obj
        doc       = erd_document_from_coordinator_graph(coordinator, dcls)
        domain_id = dnode.node_id
        domain_documents[domain_id] = doc
        domain_items.append({
            "id":      domain_id,
            "label":   str(dnode.properties.get("name", dnode.label)),
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
        "domains":         domain_items,
        "documents":       domain_documents,
        "initialDomainId": initial_domain_id,
    }, ensure_ascii=False)

    out = DEFAULT_ERD_HTML_PATH if output_path is None else Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = (
        _template_raw()
        .replace("@@HTML_ESCAPED_TITLE@@", html_escape(title))
        .replace("@@CONTAINER_WIDTH@@",    width)
        .replace("@@CONTAINER_HEIGHT@@",   height)
        .replace("@@INLINE_ERD_SCRIPT@@",  _make_bootstrap(model_json).strip())
    )
    out.write_text(html, encoding="utf-8")
    return out
