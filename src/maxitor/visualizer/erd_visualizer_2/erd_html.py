# src/maxitor/visualizer/erd_visualizer_2/erd_html.py
# mypy: ignore-errors
# pylint: disable=import-outside-toplevel

from __future__ import annotations

import html
import json
from pathlib import Path

from action_machine.system_core.type_introspection import TypeIntrospection

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
    cont.innerHTML = svg;
    const svgEl = cont.querySelector('svg');
    if (svgEl) {{
      svgEl.removeAttribute('width');
      svgEl.removeAttribute('height');
      svgEl.style.width = '100%';
      svgEl.style.height = '100%';
      svgEl.style.display = 'block';
    }}
    onGvRendered();
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

  try {{
    await loadScript('{DAGRE_UMD_URL}',       'dagre-umd');
    await loadScript('{CYTOSCAPE_URL}',       'cytoscape-script');
    await loadScript('{CYTOSCAPE_DAGRE_URL}', 'cy-dagre');
  }} catch(e) {{
    cont.innerHTML = '<div class="erd-error">Cytoscape loading error:\\n' + e + '</div>';
    return;
  }}

  cont.innerHTML = '<div id="cy-graph" style="width:100%;height:100%;background:#f8fafc;"></div>';

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
    minZoom: 0.05, maxZoom: 4, wheelSensitivity: 0.3,
  }});

  cyInstance.on('tap', 'node', evt => {{
    const nd = currentNodes.find(n => n.id === evt.target.id());
    if (nd) showNodeDetail(nd);
  }});

  setupZoomButtons(
    () => cyInstance.zoom(cyInstance.zoom() * 1.2),
    () => cyInstance.zoom(cyInstance.zoom() * 0.8),
    () => cyInstance.fit(undefined, 40),
  );
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
    cont.innerHTML = svg;
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
      '  graph [fontname="Helvetica" bgcolor="#f8fafc" pad="0.5" '
        + 'overlap=false splines=false sep="+40"]',
    );
  }} else {{
    lines.push(
      '  graph [rankdir=' + (isLR ? 'LR' : 'TB') +
        ' fontname="Helvetica" bgcolor="#f8fafc" pad="0.5" nodesep="0.8" ranksep="1.2"]',
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
           '<span style="color:#94a3b8;font-size:10px">' + escHtml(e.label || '') + '</span>' +
           '</div>';
    for (const e of relIn)
      h += '<div class="rel-row">' +
           '<span class="rel-arrow">←</span>' +
           '<span class="rel-target">' + escHtml(e.source) + '</span>' +
           '<span style="color:#94a3b8;font-size:10px">' + escHtml(e.label || '') + '</span>' +
           '</div>';
    h += '</div>';
  }}

  body.innerHTML = h;
  shell.classList.add('open');
}}

document.getElementById('node-detail-close')
  ?.addEventListener('click', () =>
    document.getElementById('node-detail-shell')?.classList.remove('open'));

// ════════════════════════════════════════════════════════════════════════════
//  Utilities
// ════════════════════════════════════════════════════════════════════════════
function setupZoomButtons(zIn, zOut, zFit) {{
  [['btn-zoom-in', zIn], ['btn-zoom-out', zOut], ['btn-zoom-fit', zFit]]
    .forEach(([id, fn]) => {{
      const el = document.getElementById(id);
      if (!el) return;
      const clone = el.cloneNode(true);
      el.parentNode.replaceChild(clone, el);
      if (fn) clone.addEventListener('click', fn);
    }});
}}

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
const HAS_LAYOUT = new Set(['d3gv', 'cytoscape']);
const LAYOUT_GROUPS = {{
  d3gv: [
    {{ id: 'gv-dot-lr', label: 'Dot LR', recommended: true }},
    {{ id: 'gv-dot-tb', label: 'Dot TB' }},
    {{ id: 'gv-neato',  label: 'Neato' }},
    {{ id: 'gv-fdp',    label: 'FDP' }},
    {{ id: 'gv-circo',  label: 'Circo' }},
  ],
  cytoscape: [
    {{ id: 'cy-dagre-lr', label: 'Dagre LR', recommended: true }},
    {{ id: 'cy-dagre-tb', label: 'Dagre TB' }},
  ],
}};
const RENDERERS = [
  {{ id: 'd3gv',      label: 'Graphviz \u2756', recommended: true }},
  {{ id: 'cytoscape', label: 'Cytoscape' }},
  {{ id: 'mermaid',   label: 'Mermaid' }},
];

function switchRenderer(name) {{
  activeRenderer = name;
  for (const id of ALL_CONT_IDS) {{
    const el = document.getElementById(id);
    if (el) {{ el.style.display = 'none'; el.classList.remove('active'); }}
  }}
  const zt = document.getElementById('zoom-toolbar');
  if (zt) zt.style.display = 'none';

  for (const id of (RENDERER_SHOWS[name] || [])) {{
    const el = document.getElementById(id);
    if (el) {{ el.style.display = ''; el.classList.add('active'); }}
  }}
  if (name === 'cytoscape') {{
    if (zt) zt.style.display = '';
  }}

  const lp = document.getElementById('layout-picker');
  if (lp) lp.style.display = HAS_LAYOUT.has(name) ? '' : 'none';
  renderLayoutPills(name);

  document.querySelectorAll('#renderer-pill-bar .pill').forEach(p =>
    p.classList.toggle('active', p.dataset.renderer === name));

  switch (name) {{
    case 'd3gv':      initD3Graphviz(); break;
    case 'cytoscape': initCytoscape();  break;
    case 'mermaid':   initMermaid();    break;
  }}
}}

function renderLayoutPills(renderer) {{
  const bar = document.getElementById('layout-pill-bar');
  if (!bar) return;
  const group = LAYOUT_GROUPS[renderer] || [];
  if (!group.length) {{ bar.innerHTML = ''; return; }}
  if (!group.find(l => l.id === activeLayout)) activeLayout = group[0].id;
  bar.innerHTML = group.map(l =>
    '<button class="pill' + (l.recommended ? ' recommended' : '') +
    (activeLayout === l.id ? ' active' : '') +
    '" data-layout="' + l.id + '">' + l.label + '</button>'
  ).join('');
  bar.querySelectorAll('.pill').forEach(p => {{
    p.addEventListener('click', () => {{
      activeLayout = p.dataset.layout;
      bar.querySelectorAll('.pill').forEach(x => x.classList.remove('active'));
      p.classList.add('active');
      switchRenderer(activeRenderer);
    }});
  }});
}}

function initRendererPills() {{
  const bar = document.getElementById('renderer-pill-bar');
  if (!bar) return;
  bar.innerHTML = RENDERERS.map(r =>
    '<button class="pill' + (r.recommended ? ' recommended' : '') +
    (r.id === activeRenderer ? ' active' : '') +
    '" data-renderer="' + r.id + '">' + r.label + '</button>'
  ).join('');
  bar.querySelectorAll('.pill').forEach(p =>
    p.addEventListener('click', () => switchRenderer(p.dataset.renderer)));
}}

function renderDomainToggleBar() {{
  const domains = ERD_DATA?.domains || {{}};
  const keys = Object.keys(domains);
  const bar = document.getElementById('domain-pill-bar');
  if (!bar) return;

  bar.innerHTML = keys.map(k => {{
    const isOn = enabledDomains.has(k);
    const cls = 'pill domain-toggle' + (isOn ? ' active' : '');
    return (
      '<button type="button" class="' + cls + '" role="switch" aria-checked="' + isOn + '"' +
      ' data-domain="' + escAttr(k) + '" title="Toggle domain in the diagram">' +
      escHtml(k) +
      '</button>'
    );
  }}).join('');

  bar.querySelectorAll('.domain-toggle').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const key = btn.getAttribute('data-domain');
      if (!key || !domains[key]) return;
      if (enabledDomains.has(key)) enabledDomains.delete(key);
      else enabledDomains.add(key);
      renderDomainToggleBar();
      switchRenderer(activeRenderer);
    }});
  }});
}}

function initNeighborhoodFilter() {{
  const grp = document.getElementById('neighborhood-filter');
  if (grp) {{
    const dq = ERD_DATA?.domain_qualifiers;
    grp.style.display = dq && Object.keys(dq).length ? '' : 'none';
  }}
  const cb = document.getElementById('neighborhood-expand');
  if (cb && !nhFilterWired) {{
    cb.addEventListener('change', () => switchRenderer(activeRenderer));
    nhFilterWired = true;
  }}
}}

function initDomainPicker() {{
  const domains = ERD_DATA?.domains || {{}};
  const keys = Object.keys(domains);
  const picker = document.getElementById('domain-picker');
  if (!keys.length || !picker) {{
    initNeighborhoodFilter();
    return;
  }}

  if (keys.length === 1) {{
    enabledDomains = new Set(keys);
    initNeighborhoodFilter();
    return;
  }}

  picker.style.display = '';
  enabledDomains = new Set();
  renderDomainToggleBar();
  initNeighborhoodFilter();
}}

// ════════════════════════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════════════════════════
(function boot() {{
  initDomainPicker();
  initRendererPills();
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
    return _TEMPLATE_HTML.read_text(encoding="utf-8")


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
        erd_data: dict = {"domains": domains_map, "domain_qualifiers": domain_qualifiers}
    else:
        payload = erd_payload_from_coordinator_for_domain(coordinator, domain_cls)
        domain_name = getattr(domain_cls, "name", None) or domain_cls.__name__
        erd_data = {
            "domains": {domain_name: _payload_to_domain_dict(payload)},
            "domain_qualifiers": {domain_name: TypeIntrospection.full_qualname(domain_cls)},
        }

    return write_erd_html(erd_data, output_path, title=title, width=width, height=height)
