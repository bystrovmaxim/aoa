# src/maxitor/visualizer/erd_visualizer_2/erd_html.py
# mypy: ignore-errors
# pylint: disable=import-outside-toplevel

from __future__ import annotations

import html
import json
from pathlib import Path

from action_machine.system_core.type_introspection import TypeIntrospection
from maxitor.visualizer.graph_visualizer.visualizer_icons import (
    svg_data_uri_for_interchange_domain_legend,
)
from maxitor.visualizer.shared.chrome import read_interchange_chrome_css

# ── Package layout ────────────────────────────────────────────────────────────
_PACKAGE_DIR = Path(__file__).resolve().parent
_TEMPLATE_HTML = _PACKAGE_DIR / "template.html"
DEFAULT_ERD_HTML_PATH = "/Users/bystrovmaxim/PythonDev/aoa/archive/logs/erd.html"

# ── CDN URLs ──────────────────────────────────────────────────────────────────
MERMAID_MODULE_URL = "https://esm.sh/mermaid@11.12.0"
GRAPHVIZ_MODULE_URL = "https://esm.sh/@hpcc-js/wasm-graphviz@1.21.5"

# Cytoscape stack (UMD)
_CYTOSCAPE_URL = "https://unpkg.com/cytoscape@3.30.2/dist/cytoscape.min.js"
_CYTOSCAPE_DAGRE_URL = "https://unpkg.com/cytoscape-dagre@2.5.0/cytoscape-dagre.js"
_DAGRE_UMD_URL = "https://unpkg.com/dagre@0.8.5/dist/dagre.min.js"

# ── Domain entity color palette ───────────────────────────────────────────────
_ENTITY_COLORS = [
    "#3b82f6",
    "#8b5cf6",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#06b6d4",
    "#ec4899",
    "#64748b",
]

# ── Bootstrap JS (Python format-string; JS braces are doubled) ────────────────
_ERD_BOOTSTRAP_TEMPLATE = """\
// ════════════════════════════════════════════════════════════════════════════
//  ERD Viewer Bootstrap  —  injected by erd_html.py
// ════════════════════════════════════════════════════════════════════════════

const __MERMAID_URL__ = "{MERMAID_URL}";
const __GRAPHVIZ_URL__ = "{GRAPHVIZ_URL}";

const ERD_DATA = {ERD_DATA_JSON};

// ── helpers ──────────────────────────────────────────────────────────────────
function escHtml(s) {{
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function escAttr(s) {{
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}}

function mergeDomainPayloads(parts) {{
  const nodeById = new Map();
  const edgeSig = e =>
    String(e.source) +
    '\\u001f' +
    String(e.target) +
    '\\u001f' +
    String(e.label || '');
  const seenEdges = new Set();
  const edgesOut = [];
  for (const part of parts) {{
    for (const n of (part.nodes || [])) nodeById.set(n.id, n);
    for (const e of (part.edges || [])) {{
      const sig = edgeSig(e);
      if (seenEdges.has(sig)) continue;
      seenEdges.add(sig);
      edgesOut.push(e);
    }}
  }}
  return {{ nodes: [...nodeById.values()], edges: edgesOut }};
}}

function loadScript(url, id) {{
  return new Promise((resolve, reject) => {{
    if (document.getElementById(id)) {{ resolve(); return; }}
    const s = document.createElement('script');
    s.id  = id;
    s.src = url;
    s.type = 'text/javascript';
    s.onload  = resolve;
    s.onerror = () => reject(new Error('Failed to load: ' + url));
    document.head.appendChild(s);
  }});
}}

// ── state ────────────────────────────────────────────────────────────────────
let activeRenderer = 'd3gv';
let activeLayout   = 'gv-dot-lr';
/** @type {{Set<string>}} Domain keys toggled on (subset of ``ERD_DATA.domains``). */
let enabledDomains = new Set();
let cyInstance     = null;
let currentNodes   = [];
let currentEdges   = [];

let gvApi = null;
let nhFilterWired = false;
let domainPickerWired = false;

// ── Zoom / pan (same mechanics as erd_visualizer: rAF wheel + exp factor, 1.25 / 0.8, clamp)
const MIN_SCALE = 0.2;
const MAX_SCALE = 2.5;
const WHEEL_ZOOM_SENSITIVITY = 0.0045;

let svgPan = {{ vpid: '', pnid: '', scale: 1, tx: 0, ty: 0 }};
let svgWheelAccum = 0;
let svgWheelRaf = null;
let cyInteract = null;
let cyWheelAccum = 0;
let cyWheelRaf = null;
let svgPanDrag = null;

function clampUserScale(scale) {{
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
}}

function svgApplyTransform() {{
  const panner = document.getElementById(svgPan.pnid);
  if (!panner) return;
  panner.style.transform =
    'translate(' + svgPan.tx + 'px,' + svgPan.ty + 'px) scale(' + svgPan.scale + ')';
}}

function fitSvgPanorama() {{
  const vp = document.getElementById(svgPan.vpid);
  const panner = document.getElementById(svgPan.pnid);
  if (!vp || !panner) return;
  const svg = panner.querySelector('svg');
  if (!svg) return;
  svg.removeAttribute('width');
  svg.removeAttribute('height');

  const vb = svg.viewBox && svg.viewBox.baseVal;
  let w;
  let h;
  let bx = 0;
  let by = 0;
  if (vb && Number(vb.width) > 0 && Number(vb.height) > 0) {{
    w = vb.width;
    h = vb.height;
    bx = vb.x || 0;
    by = vb.y || 0;
  }} else {{
    try {{
      const bbox = svg.getBBox();
      w = bbox.width || 1;
      h = bbox.height || 1;
      bx = bbox.x || 0;
      by = bbox.y || 0;
    }} catch (_) {{
      w = 800;
      h = 600;
    }}
  }}
  if (!Number.isFinite(w) || w < 1) w = 1;
  if (!Number.isFinite(h) || h < 1) h = 1;

  // Ensure the SVG has a real layout box (required after stripping width/height).
  if (vb && Number(vb.width) > 0) {{
    svg.setAttribute('width', String(vb.width));
    svg.setAttribute('height', String(vb.height));
  }} else {{
    svg.setAttribute('width', String(w));
    svg.setAttribute('height', String(h));
  }}

  const cw = vp.clientWidth || 1;
  const ch = vp.clientHeight || 1;
  let s = Math.min(cw / w, ch / h) * 0.92;
  s = Math.max(0.05, Math.min(s, MAX_SCALE));
  svgPan.scale = s;
  svgPan.tx = (cw - w * s) / 2 - bx * s;
  svgPan.ty = (ch - h * s) / 2 - by * s;
  svgApplyTransform();
  syncZoomPct();
}}

function zoomSvgFromViewportCenter(factor) {{
  const vp = document.getElementById(svgPan.vpid);
  if (!vp || !svgPan.pnid) return;
  const cx = vp.clientWidth / 2;
  const cy = vp.clientHeight / 2;
  const s0 = svgPan.scale;
  const s1 = clampUserScale(s0 * factor);
  if (s1 === s0) return;
  svgPan.tx = cx - (cx - svgPan.tx) * (s1 / s0);
  svgPan.ty = cy - (cy - svgPan.ty) * (s1 / s0);
  svgPan.scale = s1;
  svgApplyTransform();
  syncZoomPct();
}}

let svgPanInteract = null;

function flushSvgWheelZoom() {{
  svgWheelRaf = null;
  const vp = document.getElementById(svgPan.vpid);
  if (!vp || !svgPan.pnid) return;
  const dy = Math.max(-120, Math.min(120, svgWheelAccum));
  svgWheelAccum = 0;
  const factor = Math.exp(-dy * WHEEL_ZOOM_SENSITIVITY);
  const rect = vp.getBoundingClientRect();
  const wx = typeof svgPan.wheelClientX === 'number' ? svgPan.wheelClientX : rect.left + rect.width / 2;
  const wy = typeof svgPan.wheelClientY === 'number' ? svgPan.wheelClientY : rect.top + rect.height / 2;
  svgPan.wheelClientX = svgPan.wheelClientY = undefined;
  const ox = wx - rect.left;
  const oy = wy - rect.top;
  const s0 = svgPan.scale;
  const s1 = clampUserScale(s0 * factor);
  if (s1 === s0) return;
  svgPan.tx = ox - (ox - svgPan.tx) * (s1 / s0);
  svgPan.ty = oy - (oy - svgPan.ty) * (s1 / s0);
  svgPan.scale = s1;
  svgApplyTransform();
  syncZoomPct();
}}

function attachSvgViewportInteraction() {{
  const vp = document.getElementById(svgPan.vpid);
  if (!vp) return;
  if (svgPanInteract) svgPanInteract.abort();
  svgPanInteract = new AbortController();
  const sig = svgPanInteract.signal;

  vp.addEventListener(
    'wheel',
    (evt) => {{
      evt.preventDefault();
      svgPan.wheelClientX = evt.clientX;
      svgPan.wheelClientY = evt.clientY;
      svgWheelAccum += evt.deltaY;
      if (svgWheelRaf == null) svgWheelRaf = requestAnimationFrame(flushSvgWheelZoom);
    }},
    {{ passive: false, signal: sig }},
  );
  vp.addEventListener('mousedown', (evt) => {{
    if (evt.button !== 0) return;
    evt.preventDefault();
    svgPanDrag = {{ x: evt.clientX, y: evt.clientY, tx: svgPan.tx, ty: svgPan.ty }};
    vp.classList.add('erd-panning');
  }}, {{ signal: sig }});
  window.addEventListener('mousemove', (evt) => {{
    if (!svgPanDrag) return;
    svgPan.tx = svgPanDrag.tx + (evt.clientX - svgPanDrag.x);
    svgPan.ty = svgPanDrag.ty + (evt.clientY - svgPanDrag.y);
    svgApplyTransform();
  }}, {{ signal: sig }});
  window.addEventListener('mouseup', () => {{
    if (svgPanDrag) {{
      svgPanDrag = null;
      vp.classList.remove('erd-panning');
    }}
  }}, {{ signal: sig }});
}}

function currentZoomRatio() {{
  if (activeRenderer === 'cytoscape' && cyInstance)
    return cyInstance.zoom();
  if ((activeRenderer === 'd3gv' || activeRenderer === 'mermaid') && svgPan.pnid)
    return svgPan.scale;
  return 1;
}}

function syncZoomPct() {{
  const lab = document.getElementById('zoom-pct');
  if (lab) lab.textContent = Math.round(Number(currentZoomRatio()) * 100) + '%';
}}

function flushCyWheelZoom() {{
  cyWheelRaf = null;
  if (!cyInstance) return;
  const dy = Math.max(-120, Math.min(120, cyWheelAccum));
  cyWheelAccum = 0;
  const factor = Math.exp(-dy * WHEEL_ZOOM_SENSITIVITY);
  const z0 = cyInstance.zoom();
  const z1 = clampUserScale(z0 * factor);
  cyInstance.zoom(z1);
  syncZoomPct();
}}

function zoomCyRelative(factor) {{
  if (!cyInstance) return;
  cyInstance.zoom(clampUserScale(cyInstance.zoom() * factor));
  syncZoomPct();
}}

function installZoomChrome() {{
  document.getElementById('btn-zoom-in')?.addEventListener('click', () => {{
    if (activeRenderer === 'cytoscape') zoomCyRelative(1.25);
    else if (activeRenderer === 'd3gv' || activeRenderer === 'mermaid')
      zoomSvgFromViewportCenter(1.25);
  }});
  document.getElementById('btn-zoom-out')?.addEventListener('click', () => {{
    if (activeRenderer === 'cytoscape') zoomCyRelative(0.8);
    else if (activeRenderer === 'd3gv' || activeRenderer === 'mermaid')
      zoomSvgFromViewportCenter(0.8);
  }});
  document.getElementById('btn-zoom-fit')?.addEventListener('click', () => {{
    if (activeRenderer === 'cytoscape' && cyInstance) {{
      cyInstance.fit(undefined, 40);
      syncZoomPct();
      return;
    }}
    if (activeRenderer === 'd3gv' || activeRenderer === 'mermaid') fitSvgPanorama();
  }});
}}

// ── domain data ──────────────────────────────────────────────────────────────
function mergeSelectedDomainPayloads() {{
  const domains = ERD_DATA && ERD_DATA.domains;
  if (!domains) return {{ nodes: [], edges: [] }};
  const keys = Object.keys(domains);
  if (!keys.length) return {{ nodes: [], edges: [] }};
  const on = keys.filter(k => enabledDomains.has(k));
  if (!on.length) return {{ nodes: [], edges: [] }};
  if (on.length === 1) return domains[on[0]];
  return mergeDomainPayloads(on.map(k => domains[k]));
}}

function scopeFilterDisabled() {{
  const dq = ERD_DATA && ERD_DATA.domain_qualifiers;
  if (!dq || typeof dq !== 'object') return true;
  if (!Object.keys(dq).length) return true;
  return false;
}}

function selectedDomainQualifiers() {{
  const dq = ERD_DATA.domain_qualifiers || {{}};
  const out = new Set();
  for (const k of enabledDomains) {{
    const q = dq[k];
    if (q) out.add(q);
  }}
  return out;
}}

function applyNeighborhoodScope(raw) {{
  const nodes = raw.nodes || [];
  const edges = raw.edges || [];
  if (scopeFilterDisabled()) return {{ nodes, edges }};
  if (!nodes.length) return {{ nodes, edges }};
  if (!nodes.some(n => n.domain_qualifier)) return {{ nodes, edges }};

  const coreQuals = selectedDomainQualifiers();
  if (!coreQuals.size) return {{ nodes: [], edges: [] }};

  const expand =
    document.getElementById('neighborhood-expand') === null
      ? true
      : !!document.getElementById('neighborhood-expand').checked;

  const coreIds = new Set();
  for (const n of nodes) {{
    const q = n.domain_qualifier || '';
    if (q && coreQuals.has(q)) coreIds.add(n.id);
  }}

  const keepIds = new Set(coreIds);
  if (expand) {{
    for (const e of edges) {{
      if (coreIds.has(e.source) || coreIds.has(e.target)) {{
        keepIds.add(e.source);
        keepIds.add(e.target);
      }}
    }}
  }}

  const nodesOut = nodes.filter(n => keepIds.has(n.id));
  const ok = new Set(nodesOut.map(n => n.id));
  const edgesOut = edges.filter(e => ok.has(e.source) && ok.has(e.target));
  return {{ nodes: nodesOut, edges: edgesOut }};
}}

function getDomainData() {{
  return applyNeighborhoodScope(mergeSelectedDomainPayloads());
}}

// ════════════════════════════════════════════════════════════════════════════
//  Renderer 1 — Graphviz SVG via @hpcc-js/wasm-graphviz
// ════════════════════════════════════════════════════════════════════════════

async function ensureGraphvizApi() {{
  if (gvApi) return gvApi;
  const mod = await import(__GRAPHVIZ_URL__);
  const Cls = mod.Graphviz || mod.default?.Graphviz || mod.default;
  if (!Cls || typeof Cls.load !== 'function') {{
    throw new Error('Graphviz.load() was not found in @hpcc-js/wasm-graphviz');
  }}
  gvApi = await Cls.load();
  return gvApi;
}}

async function initD3Graphviz() {{
  const cont = document.getElementById('d3gv-container');
  cont.innerHTML = '<div class="erd-loading">&#x23F3; Loading Graphviz\u2026</div>';

  const {{ nodes, edges }} = getDomainData();
  currentNodes = nodes || [];
  currentEdges = edges || [];

  const dot = buildDotSource();
  const engine = getGvEngine();
  try {{
    const api = await ensureGraphvizApi();
    const svg = api.layout(dot, 'svg', engine);
    cont.innerHTML =
      '<div class="erd-svg-viewport" id="gv-viewport">' +
        '<div class="erd-svg-panner" id="gv-panner">' + svg + '</div></div>';
    const svgEl = cont.querySelector('#gv-panner svg');
    if (svgEl) {{
      svgEl.removeAttribute('width');
      svgEl.removeAttribute('height');
      const gg = svgEl.querySelector('g.graph');
      const bgPoly = gg && gg.querySelector('polygon');
      if (bgPoly) {{
        const fill = String(bgPoly.getAttribute('fill') || '').toLowerCase();
        if (fill === '#f8fafc' || fill === '#f4f5f7' || fill === 'lightgray' || fill === 'lightgrey')
          bgPoly.setAttribute('fill', 'none');
      }}
    }}
    svgPan.vpid = 'gv-viewport';
    svgPan.pnid = 'gv-panner';
    requestAnimationFrame(() => {{
      requestAnimationFrame(() => {{
        fitSvgPanorama();
        attachSvgViewportInteraction();
      }});
    }});
    onGvRendered();
    syncZoomPct();
  }} catch(e) {{
    cont.innerHTML = '<div class="erd-error">Graphviz render error:\\n' + e + '</div>';
  }}
}}

function onGvRendered() {{
  const root = document.getElementById('d3gv-container');
  if (!root) return;
  const nodes = root.querySelectorAll('g.node');
  const edges = root.querySelectorAll('g.edge');
  nodes.forEach(el => {{
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => {{
      const title = el.querySelector('title')?.textContent?.trim();
      const nd = currentNodes.find(n => n.id === title || n.label === title);
      if (nd) showNodeDetail(nd);
    }});
    el.addEventListener('mouseenter', () => {{
      const title = el.querySelector('title')?.textContent?.trim() || '';
      nodes.forEach(n => {{
        n.style.opacity = n.querySelector('title')?.textContent?.trim() === title ? '1' : '0.35';
      }});
      edges.forEach(e => {{
        const edgeTitle = e.querySelector('title')?.textContent?.trim() || '';
        e.style.opacity = edgeTitle.includes(title) ? '1' : '0.2';
      }});
    }});
    el.addEventListener('mouseleave', () => {{
      nodes.forEach(n => n.style.opacity = '1');
      edges.forEach(e => e.style.opacity = '1');
    }});
  }});
}}

function getGvEngine() {{
  if (activeLayout === 'gv-dot-lr' || activeLayout === 'gv-dot-tb') return 'dot';
  if (activeLayout === 'gv-neato')  return 'neato';
  if (activeLayout === 'gv-fdp')    return 'fdp';
  if (activeLayout === 'gv-circo')  return 'circo';
  return 'dot';
}}

// ════════════════════════════════════════════════════════════════════════════
//  Renderer 2 — Cytoscape.js
// ════════════════════════════════════════════════════════════════════════════
async function initCytoscape() {{
  const cont = document.getElementById('cy-container');
  cont.innerHTML = '<div class="erd-loading">&#x23F3; Loading Cytoscape\u2026</div>';

  if (cyInteract) cyInteract.abort();
  cyInteract = new AbortController();
  const cySig = cyInteract.signal;

  try {{
    await loadScript('{DAGRE_UMD_URL}',       'dagre-umd');
    await loadScript('{CYTOSCAPE_URL}',       'cytoscape-script');
    await loadScript('{CYTOSCAPE_DAGRE_URL}', 'cy-dagre');
  }} catch(e) {{
    cont.innerHTML = '<div class="erd-error">Cytoscape loading error:\\n' + e + '</div>';
    return;
  }}

  cont.innerHTML = '<div id="cy-graph" style="width:100%;height:100%;background:transparent;"></div>';

  const {{ nodes, edges }} = getDomainData();
  currentNodes = nodes || [];
  currentEdges = edges || [];

  const isLR = activeLayout === 'cy-dagre-lr';
  const elements = [
    ...currentNodes.map(nd => ({{
      group: 'nodes',
      data:  {{ id: nd.id, label: nd.label || nd.id,
                fields: nd.fields || [], color: nd.color || '#3b82f6' }},
    }})),
    ...currentEdges.map(ed => ({{
      group: 'edges',
      data:  {{ id: 'e_' + ed.source + '_' + ed.target,
                source: ed.source, target: ed.target, label: ed.label || '' }},
    }})),
  ];

  if (cyInstance) {{ try {{ cyInstance.destroy(); }} catch(_){{}} }}

  cyInstance = cytoscape({{
    container: document.getElementById('cy-graph'),
    elements,
    style:  buildCytoscapeStyle(),
    layout: {{ name: 'dagre', rankDir: isLR ? 'LR' : 'TB',
               nodeSep: 60, rankSep: 100, padding: 40,
               animate: true, animationDuration: 400 }},
    minZoom: MIN_SCALE,
    maxZoom: MAX_SCALE,
    zoomingEnabled: true,
    userZoomingEnabled: false,
    boxSelectionEnabled: false,
  }});

  cyInstance.on('zoom', () => syncZoomPct());

  const cyGraph = document.getElementById('cy-graph');
  cyGraph.addEventListener(
    'wheel',
    (e) => {{
      e.preventDefault();
      cyWheelAccum += e.deltaY;
      if (cyWheelRaf == null) cyWheelRaf = requestAnimationFrame(flushCyWheelZoom);
    }},
    {{ passive: false, signal: cySig }},
  );

  cyInstance.on('tap', 'node', evt => {{
    const nd = currentNodes.find(n => n.id === evt.target.id());
    if (nd) showNodeDetail(nd);
  }});

  syncZoomPct();
}}

function buildCytoscapeStyle() {{
  return [
    {{ selector: 'node', style: {{
        shape: 'roundrectangle', 'background-color': 'data(color)',
        label: 'data(label)', color: '#fff', 'font-size': '13px',
        'font-weight': 'bold', 'text-valign': 'center', 'text-halign': 'center',
        padding: '14px', 'text-wrap': 'wrap', 'text-max-width': '180px',
        'min-width': '160px', 'border-width': 0,
    }} }},
    {{ selector: 'edge', style: {{
        width: 1.5, 'line-color': '#94a3b8',
        'target-arrow-color': '#94a3b8', 'target-arrow-shape': 'triangle',
        'curve-style': 'bezier', label: 'data(label)',
        'font-size': '10px', color: '#64748b',
        'text-background-color': '#fff', 'text-background-opacity': 0.8,
        'text-background-padding': '2px',
    }} }},
    {{ selector: 'node:selected', style: {{
        'border-width': 3, 'border-color': '#1d4ed8', 'background-color': '#2563eb',
    }} }},
    {{ selector: 'edge:selected', style: {{
        'line-color': '#2563eb', 'target-arrow-color': '#2563eb', width: 2.5,
    }} }},
  ];
}}

// ════════════════════════════════════════════════════════════════════════════
//  Renderer 3 — Mermaid
// ════════════════════════════════════════════════════════════════════════════
async function initMermaid() {{
  const cont = document.getElementById('mermaid-container');
  cont.innerHTML = '<div class="erd-loading">&#x23F3; Loading Mermaid\u2026</div>';
  try {{
    const m = await import(__MERMAID_URL__);
    const mermaid = m.default || m;
    mermaid.initialize({{ startOnLoad: false, theme: 'default',
                          er: {{ useMaxWidth: false }} }});
    const {{ svg }} = await mermaid.render('mermaid-erd-svg', buildMermaidSource());
    cont.innerHTML =
      '<div class="erd-svg-viewport" id="mm-viewport">' +
        '<div class="erd-svg-panner" id="mm-panner">' + svg + '</div></div>';
    const svgEl = cont.querySelector('#mm-panner svg');
    if (svgEl) {{
      svgEl.removeAttribute('width');
      svgEl.removeAttribute('height');
    }}
    svgPan.vpid = 'mm-viewport';
    svgPan.pnid = 'mm-panner';
    requestAnimationFrame(() => {{
      requestAnimationFrame(() => {{
        fitSvgPanorama();
        attachSvgViewportInteraction();
      }});
    }});
    syncZoomPct();
  }} catch(e) {{
    cont.innerHTML = '<div class="erd-error">Mermaid error:\\n' + e + '</div>';
  }}
}}

// ════════════════════════════════════════════════════════════════════════════
//  DOT / Mermaid source builders
// ════════════════════════════════════════════════════════════════════════════
function buildDotSource() {{
  const {{ nodes, edges }} = getDomainData();
  const isLR = activeLayout === 'gv-dot-lr' || activeLayout === 'cy-dagre-lr';
  const lines = ['digraph ERD {{'];
  // Neato ignores rankdir / nodesep / ranksep; those attrs produce a poor spring layout. Use
  // spring-specific spacing (see graphviz attrs: overlap, sep) without changing dot/fdp/circo.
  if (activeLayout === 'gv-neato') {{
    lines.push(
      '  graph [fontname="Helvetica" bgcolor=transparent pad="0.5" '
        + 'overlap=false splines=false sep="+40"]',
    );
  }} else {{
    lines.push(
      '  graph [rankdir=' + (isLR ? 'LR' : 'TB') +
        ' fontname="Helvetica" bgcolor=transparent pad="0.5" nodesep="0.8" ranksep="1.2"]',
    );
  }}
  lines.push(
    '  node  [shape=none fontname="Helvetica" fontsize=11 margin="0"]',
    '  edge  [fontname="Helvetica" fontsize=9 color="#94a3b8" arrowsize=0.7]',
    '',
  );

  for (const nd of (nodes || [])) {{
    const color = nd.color || '#3b82f6';
    const rows  = (nd.fields || []).map(f => {{
      const bg      = f.primary_key ? '#fef9c3' : f.foreign_key ? '#dbeafe' : '#ffffff';
      const icon    = f.primary_key ? 'PK' : f.foreign_key ? 'FK' : '';
      const iconTd  = icon
        ? '<TD BGCOLOR="' + bg + '" ALIGN="CENTER" WIDTH="28"><FONT POINT-SIZE="9"><B>' + icon + '</B></FONT></TD>'
        : '<TD BGCOLOR="' + bg + '" WIDTH="28"></TD>';
      return '<TR>' + iconTd +
        '<TD BGCOLOR="' + bg + '" ALIGN="LEFT">' + escHtml(f.name) + '</TD>' +
        '<TD BGCOLOR="' + bg + '" ALIGN="LEFT"><FONT COLOR="#64748b"><I>' +
          escHtml(f.type || '') + '</I></FONT></TD>' +
        '</TR>';
    }}).join('\\n      ');

    lines.push(
      '  "' + nd.id + '" [label=<<TABLE BGCOLOR="white" BORDER="1" CELLBORDER="0" ' +
      'CELLSPACING="0" CELLPADDING="4" STYLE="ROUNDED" COLOR="' + color + '">' +
      '<TR><TD COLSPAN="3" BGCOLOR="' + color + '" ALIGN="CENTER">' +
      '<FONT COLOR="white" POINT-SIZE="12"><B>' + escHtml(nd.label || nd.id) + '</B></FONT>' +
      '</TD></TR>' + rows + '</TABLE>>]'
    );
  }}

  lines.push('');
  for (const ed of (edges || [])) {{
    const lbl = ed.label ? ' [label="' + escHtml(ed.label) + '" fontsize=9]' : '';
    lines.push('  "' + ed.source + '" -> "' + ed.target + '"' + lbl);
  }}
  lines.push('}}');
  return lines.join('\\n');
}}

function buildMermaidSource() {{
  const {{ nodes, edges }} = getDomainData();
  const lines = ['erDiagram'];
  for (const nd of (nodes || [])) {{
    lines.push('  ' + nd.id.replace(/[^\\w]/g,'_') + ' {{');
    for (const f of (nd.fields || [])) {{
      lines.push('    ' + (f.type || 'string').replace(/[^\\w]/g, '_') +
                 ' ' + f.name.replace(/[^\\w]/g, '_'));
    }}
    lines.push('  }}');
  }}
  for (const ed of (edges || [])) {{
    lines.push('  ' + ed.source.replace(/[^\\w]/g,'_') + ' ||--o{{ ' +
               ed.target.replace(/[^\\w]/g,'_') +
               ' : "' + escHtml(ed.label || 'has') + '"');
  }}
  return lines.join('\\n');
}}

// ════════════════════════════════════════════════════════════════════════════
//  Node detail panel
// ════════════════════════════════════════════════════════════════════════════
function showNodeDetail(nd) {{
  const shell = document.getElementById('node-detail-shell');
  const title = document.getElementById('node-detail-title');
  const body  = document.getElementById('node-detail-body');
  if (!shell || !body) return;

  title.textContent = nd.label || nd.id;
  let h = '<div class="detail-section"><div class="detail-section-title">Fields</div>';
  for (const f of (nd.fields || [])) {{
    const badges = [
      f.primary_key ? '<span class="badge badge-pk">PK</span>' : '',
      f.foreign_key ? '<span class="badge badge-fk">FK</span>' : '',
      f.unique      ? '<span class="badge badge-uq">UQ</span>' : '',
      f.not_null    ? '<span class="badge badge-nn">NN</span>' : '',
    ].join('');
    h += '<div class="field-row">' +
         '<span class="field-icon">' +
           (f.primary_key ? '&#128273;' : f.foreign_key ? '&#128279;' : '&middot;') +
         '</span>' +
         '<div style="flex:1">' +
           '<div style="display:flex;gap:4px;align-items:center">' +
             '<span class="field-name">' + escHtml(f.name) + '</span>' +
             '<span class="field-type">' + escHtml(f.type || '') + '</span>' +
           '</div>' +
           '<div class="field-badges">' + badges + '</div>' +
         '</div></div>';
  }}
  h += '</div>';

  const relOut = currentEdges.filter(e => e.source === nd.id);
  const relIn  = currentEdges.filter(e => e.target === nd.id);
  if (relOut.length || relIn.length) {{
    h += '<div class="detail-section"><div class="detail-section-title">Relations</div>';
    for (const e of relOut)
      h += '<div class="rel-row">' +
           '<span class="rel-arrow">→</span>' +
           '<span class="rel-target">' + escHtml(e.target) + '</span>' +
           '<span style="color:#5c6370;font-size:10px">' + escHtml(e.label || '') + '</span>' +
           '</div>';
    for (const e of relIn)
      h += '<div class="rel-row">' +
           '<span class="rel-arrow">←</span>' +
           '<span class="rel-target">' + escHtml(e.source) + '</span>' +
           '<span style="color:#5c6370;font-size:10px">' + escHtml(e.label || '') + '</span>' +
           '</div>';
    h += '</div>';
  }}

  body.innerHTML = h;
  shell.classList.add('is-open');
}}

document.getElementById('node-detail-close')
  ?.addEventListener('click', () =>
    document.getElementById('node-detail-shell')?.classList.remove('is-open'));

// ════════════════════════════════════════════════════════════════════════════
//  Renderer switching
// ════════════════════════════════════════════════════════════════════════════
const ALL_CONT_IDS = [
  'd3gv-container', 'cy-container',
  'mermaid-container',
];
const RENDERER_SHOWS = {{
  d3gv:      ['d3gv-container'],
  cytoscape: ['cy-container'],
  mermaid:   ['mermaid-container'],
}};

function buildModeDockHtml() {{
  const gvLR =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" ' +
    'fill="none" stroke="currentColor" stroke-width="1.25" stroke-linejoin="round">' +
    '<rect x="1" y="5" width="4" height="6" rx="0.75"/>' +
    '<path d="M5 8h1" stroke-linecap="round"/>' +
    '<rect x="6" y="5" width="4" height="6" rx="0.75"/>' +
    '<path d="M10 8h1" stroke-linecap="round"/>' +
    '<rect x="11" y="5" width="4" height="6" rx="0.75"/>' +
    '</svg>';
  const gvTB =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" ' +
    'fill="none" stroke="currentColor" stroke-width="1.25" stroke-linejoin="round">' +
    '<rect x="4.5" y="1.5" width="7" height="3" rx="0.75"/>' +
    '<path d="M8 4.5v1.2" stroke-linecap="round"/>' +
    '<rect x="4.5" y="6.2" width="7" height="3" rx="0.75"/>' +
    '<path d="M8 9.2v1.2" stroke-linecap="round"/>' +
    '<rect x="4.5" y="11" width="7" height="3" rx="0.75"/>' +
    '</svg>';
  const gvNeato =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" ' +
    'fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round">' +
    '<circle cx="4" cy="4.5" r="1.7"/><circle cx="12" cy="4" r="1.7"/>' +
    '<circle cx="5.5" cy="12" r="1.7"/><circle cx="11.5" cy="11" r="1.7"/>' +
    '<path d="M5.5 6.2Q8 8 10.3 5.7M10.3 5.7q1 3 .7 4.8M6.8 10.2q2 1.2 3.9-.2"/>' +
    '</svg>';
  const gvFdp =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" ' +
    'fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round">' +
    '<circle cx="8" cy="8" r="1.8" fill="currentColor" fill-opacity="0.25"/>' +
    '<circle cx="8" cy="2.5" r="1.3"/><circle cx="13.5" cy="8" r="1.3"/>' +
    '<circle cx="8" cy="13.5" r="1.3"/><circle cx="2.5" cy="8" r="1.3"/>' +
    '<circle cx="11.5" cy="4" r="1.2"/><circle cx="4.5" cy="12" r="1.2"/>' +
    '<path d="M8 3.8v2.3M12.2 4.8 10.8 6.5M13.2 8.7l-2.4.6M11 11l-1.7 1.5M8.1 10.2v2.2M4.7 11.8 3.8 10M2.7 8l2.6-.5M4.5 4.8 5.8 6.4"/>' +
    '</svg>';
  const gvCirco =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" ' +
    'fill="none" stroke="currentColor" stroke-width="1.2">' +
    '<circle cx="8" cy="8" r="5.5" stroke-opacity="0.35"/>' +
    '<circle cx="8" cy="2.5" r="1.35"/><circle cx="13.2" cy="6.2" r="1.35"/>' +
    '<circle cx="11.2" cy="12.8" r="1.35"/><circle cx="4.8" cy="12.8" r="1.35"/>' +
    '<circle cx="2.8" cy="6.2" r="1.35"/>' +
    '</svg>';
  const cyLR =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" ' +
    'fill="none" stroke="currentColor" stroke-width="1.25" stroke-linejoin="round">' +
    '<rect x="1.5" y="3" width="4" height="3" rx="0.5"/><rect x="9.5" y="3" width="4" height="3" rx="0.5"/>' +
    '<rect x="5.5" y="9.5" width="5" height="3.5" rx="0.5"/>' +
    '<path d="M5.5 4.5H9M12.5 4.5v4.8M8 9.5V8.2H11.5" stroke-linecap="round"/>' +
    '</svg>';
  const cyTB =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" ' +
    'fill="none" stroke="currentColor" stroke-width="1.25" stroke-linejoin="round">' +
    '<rect x="4.5" y="1.5" width="7" height="3" rx="0.5"/>' +
    '<rect x="4.5" y="6.5" width="7" height="3" rx="0.5"/>' +
    '<rect x="1.5" y="11.5" width="5" height="3" rx="0.5"/><rect x="9.5" y="11.5" width="5" height="3" rx="0.5"/>' +
    '<path d="M8 4.5v2M8 9.5v1.5M4.5 13H3v-2.5h2.5M12.5 13H14v-2.5h-2.5" stroke-linecap="round"/>' +
    '</svg>';
  const mm =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" ' +
    'fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M2 9.5 Q6 3.5 10 9.5 T14 7"/>' +
    '<path d="M12.5 5.5l2 2-2.5 1.2" opacity="0.9"/>' +
    '<circle cx="4" cy="10" r="1.1" fill="currentColor"/>' +
    '</svg>';

  const rows = [
    [ 'gv-dot-lr',   'gv', 'Dot — left to right', gvLR ],
    [ 'gv-dot-tb',   'gv', 'Dot — top to bottom', gvTB ],
    [ 'gv-neato',    'gv', 'Neato — spring layout', gvNeato ],
    [ 'gv-fdp',      'gv', 'FDP — force layout', gvFdp ],
    [ 'gv-circo',    'gv', 'Circo — radial tiers', gvCirco ],
    [ 'cy-dagre-lr', 'cy', 'Dagre — left to right', cyLR ],
    [ 'cy-dagre-tb', 'cy', 'Dagre — top to bottom', cyTB ],
    [ 'mermaid',     'mm', 'Mermand', mm ],
  ];

  return rows
    .map((r) => {{
      return (
        '<button type="button" class="mode-btn mode-btn--' +
        r[1] +
        '" data-mode="' +
        r[0] +
        '" title="' +
        escAttr(r[2]) +
        '">' +
        r[3] +
        '</button>'
      );
    }})
    .join('');
}}

let modeDockWired = false;

function syncModeDock() {{
  const dock = document.getElementById('mode-dock');
  if (!dock) return;
  dock.querySelectorAll('.mode-btn').forEach((btn) => {{
    const key = btn.getAttribute('data-mode');
    let on = false;
    if (key === 'mermaid') on = activeRenderer === 'mermaid';
    else if (key && key.indexOf('cy-') === 0)
      on = activeRenderer === 'cytoscape' && activeLayout === key;
    else if (key) on = activeRenderer === 'd3gv' && activeLayout === key;
    btn.classList.toggle('active', on);
  }});
}}

function applyModePreset(key) {{
  if (key === 'mermaid') {{
    activeRenderer = 'mermaid';
  }} else if (key === 'cy-dagre-lr' || key === 'cy-dagre-tb') {{
    activeRenderer = 'cytoscape';
    activeLayout = key;
  }} else {{
    activeRenderer = 'd3gv';
    activeLayout = key;
  }}
  switchRenderer(activeRenderer);
}}

function initModeDock() {{
  const dock = document.getElementById('mode-dock');
  if (!dock) return;
  dock.innerHTML = buildModeDockHtml();
  if (modeDockWired) return;
  modeDockWired = true;
  dock.addEventListener('click', (evt) => {{
    const b = evt.target.closest('.mode-btn');
    if (!b || !dock.contains(b)) return;
    const k = b.getAttribute('data-mode');
    if (k) applyModePreset(k);
  }});
}}

function switchRenderer(name) {{
  activeRenderer = name;
  for (const id of ALL_CONT_IDS) {{
    const el = document.getElementById(id);
    if (el) {{ el.style.display = 'none'; el.classList.remove('active'); }}
  }}
  const zt = document.getElementById('zoom-toolbar');
  if (zt) zt.style.display = '';

  for (const id of (RENDERER_SHOWS[name] || [])) {{
    const el = document.getElementById(id);
    if (el) {{ el.style.display = ''; el.classList.add('active'); }}
  }}

  syncModeDock();
  switch (name) {{
    case 'd3gv':      initD3Graphviz(); break;
    case 'cytoscape': initCytoscape();  break;
    case 'mermaid':   initMermaid();    break;
  }}
}}

function renderDomainPanel() {{
  const domains = ERD_DATA?.domains || {{}};
  const keys = Object.keys(domains);
  const picker = document.getElementById('domain-picker');
  if (!picker) return;
  if (keys.length <= 1) {{
    picker.style.display = 'none';
    return;
  }}
  const accents = ERD_DATA.domain_accent_colors || {{}};
  const legendIcons = ERD_DATA.domain_legend_icons || {{}};
  picker.style.display = 'flex';
  picker.innerHTML =
    '<div class="legend-title">Domains</div>' +
    keys.map((k) => {{
      const isOn = enabledDomains.has(k);
      const color = accents[k] || '#3b82f6';
      const iconSrc = legendIcons[k] || '';
      const rowCls = 'domain-row' + (isOn ? ' is-on' : ' is-off');
      const lead = iconSrc
        ? '<img class="legend-icon" src="' + escAttr(iconSrc) + '" width="20" height="20" alt="" />'
        : '<span class="legend-icon legend-icon--fallback" style="background-color:' +
          escAttr(color) +
          '"></span>';
      return (
        '<button type="button" class="' + rowCls + '" data-domain="' + escAttr(k) + '"' +
        ' role="switch" aria-pressed="' + isOn + '"' +
        ' title="Toggle domain visibility in the diagram">' +
        lead +
        '<span class="domain-row-label">' + escHtml(k) + '</span>' +
        '</button>'
      );
    }}).join('');
}}

function wireDomainPickerOnce() {{
  if (domainPickerWired) return;
  const picker = document.getElementById('domain-picker');
  if (!picker) return;
  domainPickerWired = true;
  picker.addEventListener('click', (evt) => {{
    const btn = evt.target.closest('.domain-row');
    if (!btn || !picker.contains(btn)) return;
    const key = btn.getAttribute('data-domain');
    const domains = ERD_DATA?.domains || {{}};
    if (!key || !domains[key]) return;
    if (enabledDomains.has(key)) enabledDomains.delete(key);
    else enabledDomains.add(key);
    renderDomainPanel();
    switchRenderer(activeRenderer);
  }});
}}

function initNeighborhoodFilter() {{
  const grp = document.getElementById('neighborhood-filter');
  if (grp) {{
    const dq = ERD_DATA?.domain_qualifiers;
    grp.style.display = dq && Object.keys(dq).length ? 'flex' : 'none';
  }}
  const cb = document.getElementById('neighborhood-expand');
  if (cb && !nhFilterWired) {{
    cb.addEventListener('change', () => switchRenderer(activeRenderer));
    nhFilterWired = true;
  }}
}}

function initDomainPicker() {{
  wireDomainPickerOnce();
  const domains = ERD_DATA?.domains || {{}};
  const keys = Object.keys(domains);
  const picker = document.getElementById('domain-picker');
  if (!keys.length || !picker) {{
    initNeighborhoodFilter();
    return;
  }}

  if (keys.length === 1) {{
    enabledDomains = new Set(keys);
    picker.style.display = 'none';
    initNeighborhoodFilter();
    return;
  }}

  enabledDomains = new Set();
  renderDomainPanel();
  initNeighborhoodFilter();
}}

// ════════════════════════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════════════════════════
(function boot() {{
  initDomainPicker();
  initModeDock();
  installZoomChrome();
  switchRenderer('d3gv');
}})();
"""

# ── ErdGraphPayload serialization for the JS runtime ─────────────────────────


def _role_to_flags(role: str) -> dict:
    """Convert a field role string into boolean flags for JS."""
    return {
        "primary_key": role in ("pk", "pk_fk"),
        "foreign_key": role in ("fk", "pk_fk"),
    }


def _serialize_entity(entity, color: str) -> dict:
    """
    Convert ErdEntitySpec into the JS node shape.
    """
    fields = []
    for f in entity.fields:
        flags = _role_to_flags(f.role)
        fields.append(
            {
                "name": f.name,
                "type": f.type or "",
                "primary_key": flags["primary_key"],
                "foreign_key": flags["foreign_key"],
            }
        )
    # If there are no fields, keep the table visible with an id row and attributes.
    if not fields:
        fields.append({"name": "id", "type": "str", "primary_key": True, "foreign_key": False})
        for k, v in (entity.attributes or {}).items():
            if k == "id":
                continue
            fields.append({"name": k, "type": str(v), "primary_key": False, "foreign_key": False})
    qual = (getattr(entity, "declaring_domain_qual", None) or "").strip()
    out = {
        "id": entity.id,
        "label": entity.label,
        "color": color,
        "fields": fields,
    }
    if qual:
        out["domain_qualifier"] = qual
    return out


def _serialize_edge(rel) -> dict:
    """Convert ErdEdgeSpec into the JS edge shape."""
    return {
        "source": rel.source,
        "target": rel.target,
        "label": rel.label or "",
    }


def _payload_to_domain_dict(payload) -> dict:
    """
    Convert ErdGraphPayload into the JSON-ready domain dictionary.
    """
    nodes = []
    for i, entity in enumerate(payload.entities):
        accent = (getattr(entity, "accent_color", None) or "").strip()
        color = accent if accent else _ENTITY_COLORS[i % len(_ENTITY_COLORS)]
        nodes.append(_serialize_entity(entity, color))

    edges = [_serialize_edge(rel) for rel in payload.relationships]
    return {"nodes": nodes, "edges": edges}


def _domain_accent_from_payload_dict(d: dict) -> str:
    """First entity table header color in this domain (matches Graphviz / graph nodes)."""
    for n in d.get("nodes") or []:
        c = (n.get("color") or "").strip()
        if c:
            return c
    return _ENTITY_COLORS[0]


def _with_domain_accent_colors(erd_data: dict) -> dict:
    """Attach ``domain_accent_colors`` for the left domain panel swatches."""
    domains = erd_data.get("domains")
    if not isinstance(domains, dict) or not domains:
        erd_data["domain_accent_colors"] = {}
        return erd_data
    erd_data["domain_accent_colors"] = {
        k: _domain_accent_from_payload_dict(v) for k, v in domains.items()
    }
    return erd_data


def _with_domain_legend_icons(erd_data: dict) -> dict:
    """Attach ``domain_legend_icons`` (data: URLs, Lucide Domain glyph per accent color)."""
    accents = erd_data.get("domain_accent_colors")
    if not isinstance(accents, dict) or not accents:
        erd_data["domain_legend_icons"] = {}
        return erd_data
    erd_data["domain_legend_icons"] = {
        str(k): svg_data_uri_for_interchange_domain_legend(str(v)) for k, v in accents.items()
    }
    return erd_data


# ── Python API ────────────────────────────────────────────────────────────────


def _make_bootstrap(erd_data: dict) -> str:
    return _ERD_BOOTSTRAP_TEMPLATE.format(
        MERMAID_URL=MERMAID_MODULE_URL,
        GRAPHVIZ_URL=GRAPHVIZ_MODULE_URL,
        DAGRE_UMD_URL=_DAGRE_UMD_URL,
        CYTOSCAPE_URL=_CYTOSCAPE_URL,
        CYTOSCAPE_DAGRE_URL=_CYTOSCAPE_DAGRE_URL,
        ERD_DATA_JSON=json.dumps(erd_data, ensure_ascii=False),
    )


def _template_raw() -> str:
    css = read_interchange_chrome_css()
    return _TEMPLATE_HTML.read_text(encoding="utf-8").replace(
        "@@INTERCHANGE_CHROME_CSS@@",
        css,
    )


def _load_coord_export_helpers():
    """Load graph-data helpers for package and direct directory execution."""
    try:
        from .erd_graph_data import (
            domain_classes_from_coordinator,
            erd_payload_from_coordinator_for_domain,
        )
    except ImportError:
        from erd_graph_data import (
            domain_classes_from_coordinator,
            erd_payload_from_coordinator_for_domain,
        )

    return domain_classes_from_coordinator, erd_payload_from_coordinator_for_domain


def write_erd_html(
    erd_data: dict,
    output_path: str | Path,
    title: str = "ERD Viewer",
    width: int = 1400,
    height: int = 900,
) -> Path:
    """Write a standalone ERD HTML viewer."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    _with_domain_accent_colors(erd_data)
    _with_domain_legend_icons(erd_data)
    bootstrap = _make_bootstrap(erd_data)
    tpl = _template_raw()

    result = (
        tpl.replace("@@HTML_ESCAPED_TITLE@@", html.escape(title))
        .replace("@@CONTAINER_WIDTH@@", str(width))
        .replace("@@CONTAINER_HEIGHT@@", str(height))
        .replace("@@INLINE_ERD_SCRIPT@@", bootstrap)
    )
    out.write_text(result, encoding="utf-8")
    return out


def write_erd_html_from_coordinator(
    coordinator,
    domain_cls=None,
    output_path: str | Path | None = None,
    title: str = "ERD Viewer",
    width: int = 1400,
    height: int = 900,
) -> Path:
    """Generate an ERD HTML file from a NodeGraphCoordinator."""
    domain_classes_from_coordinator, erd_payload_from_coordinator_for_domain = _load_coord_export_helpers()

    if output_path is None:
        output_path = DEFAULT_ERD_HTML_PATH

    if domain_cls is None:
        # One JS domain tab per Domain vertex in the interchange graph.
        domains_map: dict[str, dict] = {}
        domain_qualifiers: dict[str, str] = {}
        for dc in domain_classes_from_coordinator(coordinator):
            try:
                payload = erd_payload_from_coordinator_for_domain(coordinator, dc)
            except Exception:
                continue
            base = getattr(dc, "name", None) or dc.__name__
            domain_key = base
            n = 2
            while domain_key in domains_map:
                domain_key = f"{base} ({n})"
                n += 1
            domains_map[domain_key] = _payload_to_domain_dict(payload)
            domain_qualifiers[domain_key] = TypeIntrospection.full_qualname(dc)
        if not domains_map:
            msg = "No domain ERD payloads could be built from the coordinator graph."
            raise LookupError(msg)
        erd_data = {"domains": domains_map, "domain_qualifiers": domain_qualifiers}
    else:
        payload = erd_payload_from_coordinator_for_domain(coordinator, domain_cls)
        domain_name = getattr(domain_cls, "name", None) or domain_cls.__name__
        erd_data = {
            "domains": {domain_name: _payload_to_domain_dict(payload)},
            "domain_qualifiers": {domain_name: TypeIntrospection.full_qualname(domain_cls)},
        }

    return write_erd_html(erd_data, output_path, title=title, width=width, height=height)
