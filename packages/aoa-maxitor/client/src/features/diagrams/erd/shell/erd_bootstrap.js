// ════════════════════════════════════════════════════════════════════════════
//  ERD viewer bootstrap — bundled by the Maxitor React app (`build_erd_html_document.ts`).
//  The next line assigns ERD_DATA from JSON injected at build time (see MAXITOR placeholder).
// ════════════════════════════════════════════════════════════════════════════

const __MERMAID_URL__ = "https://esm.sh/mermaid@11.12.0";
const __GRAPHVIZ_URL__ = "https://esm.sh/@hpcc-js/wasm-graphviz@1.21.5";

const ERD_DATA = __MAXITOR_ERD_DATA_JSON__;

/** After one-hop patch from host: restore pan/zoom instead of fit (set before ``switchRenderer``). */
let pendingViewportRestore = null;

// ── helpers ──────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escAttr(s) {
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}

function mergeDomainPayloads(parts) {
  const nodeById = new Map();
  const edgeSig = e =>
    String(e.source) +
    '\u001f' +
    String(e.target) +
    '\u001f' +
    String(e.label || '');
  const seenRelations = new Set();
  const relationsOut = [];
  for (const part of parts) {
    for (const n of (part.entities || [])) nodeById.set(n.id, n);
    for (const e of (part.relations || [])) {
      const sig = edgeSig(e);
      if (seenRelations.has(sig)) continue;
      seenRelations.add(sig);
      relationsOut.push(e);
    }
  }
  return { entities: [...nodeById.values()], relations: relationsOut };
}

function loadScript(url, id) {
  return new Promise((resolve, reject) => {
    if (document.getElementById(id)) { resolve(); return; }
    const s = document.createElement('script');
    s.id  = id;
    s.src = url;
    s.type = 'text/javascript';
    s.onload  = resolve;
    s.onerror = () => reject(new Error('Failed to load: ' + url));
    document.head.appendChild(s);
  });
}

// ── state ────────────────────────────────────────────────────────────────────
let activeRenderer = 'd3gv';
let activeLayout   = 'gv-dot-lr';
/** @type {Set<string>} Domain keys toggled on (subset of ``ERD_DATA.domains``). */
let enabledDomains = new Set();
let cyInstance     = null;
let currentEntities = [];
let currentRelations = [];

let gvApi = null;
let nhFilterWired = false;
let domainPickerWired = false;

// ── Zoom / pan (same mechanics as erd: rAF wheel + exp factor, 1.25 / 0.8)
const MIN_SCALE = 0.005;
const MAX_SCALE = 2.5;
const WHEEL_ZOOM_SENSITIVITY = 0.0045;

let svgPan = { vpid: '', pnid: '', scale: 1, tx: 0, ty: 0 };
let svgWheelAccum = 0;
let svgWheelRaf = null;
let cyInteract = null;
let cyWheelAccum = 0;
let cyWheelRaf = null;
let svgPanDrag = null;

function clampUserScale(scale) {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
}

function svgApplyTransform() {
  const panner = document.getElementById(svgPan.pnid);
  if (!panner) return;
  panner.style.transform =
    'translate(' + svgPan.tx + 'px,' + svgPan.ty + 'px) scale(' + svgPan.scale + ')';
}

function fitSvgPanorama() {
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
  if (vb && Number(vb.width) > 0 && Number(vb.height) > 0) {
    w = vb.width;
    h = vb.height;
    bx = vb.x || 0;
    by = vb.y || 0;
  } else {
    try {
      const bbox = svg.getBBox();
      w = bbox.width || 1;
      h = bbox.height || 1;
      bx = bbox.x || 0;
      by = bbox.y || 0;
    } catch (_) {
      w = 800;
      h = 600;
    }
  }
  if (!Number.isFinite(w) || w < 1) w = 1;
  if (!Number.isFinite(h) || h < 1) h = 1;

  // Ensure the SVG has a real layout box (required after stripping width/height).
  if (vb && Number(vb.width) > 0) {
    svg.setAttribute('width', String(vb.width));
    svg.setAttribute('height', String(vb.height));
  } else {
    svg.setAttribute('width', String(w));
    svg.setAttribute('height', String(h));
  }

  const cw = vp.clientWidth || 1;
  const ch = vp.clientHeight || 1;
  let s = Math.min(cw / w, ch / h) * 0.92;
  s = Math.max(0.05, Math.min(s, MAX_SCALE));
  svgPan.scale = s;
  svgPan.tx = (cw - w * s) / 2 - bx * s;
  svgPan.ty = (ch - h * s) / 2 - by * s;
  svgApplyTransform();
  syncZoomPct();
}

function centerSvgPanoramaAtScale(scale) {
  const vp = document.getElementById(svgPan.vpid);
  const panner = document.getElementById(svgPan.pnid);
  if (!vp || !panner) return false;
  const svg = panner.querySelector('svg');
  if (!svg) return false;

  const vb = svg.viewBox && svg.viewBox.baseVal;
  let w;
  let h;
  let bx = 0;
  let by = 0;
  if (vb && Number(vb.width) > 0 && Number(vb.height) > 0) {
    w = vb.width;
    h = vb.height;
    bx = vb.x || 0;
    by = vb.y || 0;
    svg.setAttribute('width', String(vb.width));
    svg.setAttribute('height', String(vb.height));
  } else {
    try {
      const bbox = svg.getBBox();
      w = bbox.width || 1;
      h = bbox.height || 1;
      bx = bbox.x || 0;
      by = bbox.y || 0;
      svg.setAttribute('width', String(w));
      svg.setAttribute('height', String(h));
    } catch (_) {
      return false;
    }
  }

  const cw = vp.clientWidth || 1;
  const ch = vp.clientHeight || 1;
  const s = clampUserScale(Number(scale) || 1);
  svgPan.scale = s;
  svgPan.tx = (cw - w * s) / 2 - bx * s;
  svgPan.ty = (ch - h * s) / 2 - by * s;
  svgApplyTransform();
  syncZoomPct();
  return true;
}

function zoomSvgFromViewportCenter(factor) {
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
}

let svgPanInteract = null;

function flushSvgWheelZoom() {
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
}

function attachSvgViewportInteraction() {
  const vp = document.getElementById(svgPan.vpid);
  if (!vp) return;
  if (svgPanInteract) svgPanInteract.abort();
  svgPanInteract = new AbortController();
  const sig = svgPanInteract.signal;

  vp.addEventListener(
    'wheel',
    (evt) => {
      evt.preventDefault();
      svgPan.wheelClientX = evt.clientX;
      svgPan.wheelClientY = evt.clientY;
      svgWheelAccum += evt.deltaY;
      if (svgWheelRaf == null) svgWheelRaf = requestAnimationFrame(flushSvgWheelZoom);
    },
    { passive: false, signal: sig },
  );
  vp.addEventListener('mousedown', (evt) => {
    if (evt.button !== 0) return;
    evt.preventDefault();
    svgPanDrag = { x: evt.clientX, y: evt.clientY, tx: svgPan.tx, ty: svgPan.ty };
    vp.classList.add('erd-panning');
  }, { signal: sig });
  window.addEventListener('mousemove', (evt) => {
    if (!svgPanDrag) return;
    svgPan.tx = svgPanDrag.tx + (evt.clientX - svgPanDrag.x);
    svgPan.ty = svgPanDrag.ty + (evt.clientY - svgPanDrag.y);
    svgApplyTransform();
  }, { signal: sig });
  window.addEventListener('mouseup', () => {
    if (svgPanDrag) {
      svgPanDrag = null;
      vp.classList.remove('erd-panning');
    }
  }, { signal: sig });
}

function currentZoomRatio() {
  if (activeRenderer === 'cytoscape' && cyInstance)
    return cyInstance.zoom();
  if ((activeRenderer === 'd3gv' || activeRenderer === 'mermaid') && svgPan.pnid)
    return svgPan.scale;
  return 1;
}

function syncZoomPct() {
  const lab = document.getElementById('zoom-pct');
  if (lab) lab.textContent = Math.round(Number(currentZoomRatio()) * 100) + '%';
}

function captureActiveViewportForRestore() {
  if (activeRenderer === 'd3gv' || activeRenderer === 'mermaid') {
    return {
      kind: 'svg-scale',
      which: activeRenderer,
      scale: svgPan.scale,
    };
  }
  if (activeRenderer === 'cytoscape' && cyInstance) {
    return { kind: 'cy', zoom: cyInstance.zoom(), pan: cyInstance.pan() };
  }
  return null;
}

function consumePendingSvgPan(whichRenderer) {
  const p = pendingViewportRestore;
  if (!p || p.which !== whichRenderer || activeRenderer !== whichRenderer) {
    return false;
  }
  if (p.kind === 'svg-scale') {
    const ok = centerSvgPanoramaAtScale(p.scale);
    pendingViewportRestore = null;
    return ok;
  }
  pendingViewportRestore = null;
  return false;
}

function applyDomainsPatchFromHost(patch) {
  if (!patch || typeof patch !== 'object') return;
  if (patch.domains && typeof patch.domains === 'object' && ERD_DATA.domains) {
    Object.assign(ERD_DATA.domains, patch.domains);
  }
  if (patch.domain_accent_colors && typeof patch.domain_accent_colors === 'object') {
    ERD_DATA.domain_accent_colors = Object.assign(
      ERD_DATA.domain_accent_colors || {},
      patch.domain_accent_colors,
    );
  }
  pendingViewportRestore = captureActiveViewportForRestore();
  switchRenderer(activeRenderer);
}

let hostPatchWired = false;

function wireHostDomainPatchListener() {
  if (hostPatchWired) return;
  hostPatchWired = true;
  window.addEventListener('message', (ev) => {
    const d = ev.data;
    if (!d || d.source !== 'maxitor-erd') return;
    if (d.type === 'domains-patch') {
      applyDomainsPatchFromHost(d.patch);
      return;
    }
    if (d.type === 'domains-patch-error') {
      const cb = document.getElementById('neighborhood-expand');
      if (cb && typeof d.revertTo === 'boolean') cb.checked = d.revertTo;
      console.error(d.message || 'domains-patch-error');
    }
  });
}

function flushCyWheelZoom() {
  cyWheelRaf = null;
  if (!cyInstance) return;
  const dy = Math.max(-120, Math.min(120, cyWheelAccum));
  cyWheelAccum = 0;
  const factor = Math.exp(-dy * WHEEL_ZOOM_SENSITIVITY);
  const z0 = cyInstance.zoom();
  const z1 = clampUserScale(z0 * factor);
  cyInstance.zoom(z1);
  syncZoomPct();
}

function zoomCyRelative(factor) {
  if (!cyInstance) return;
  cyInstance.zoom(clampUserScale(cyInstance.zoom() * factor));
  syncZoomPct();
}

function installZoomChrome() {
  document.getElementById('btn-zoom-in')?.addEventListener('click', () => {
    if (activeRenderer === 'cytoscape') zoomCyRelative(1.25);
    else if (activeRenderer === 'd3gv' || activeRenderer === 'mermaid')
      zoomSvgFromViewportCenter(1.25);
  });
  document.getElementById('btn-zoom-out')?.addEventListener('click', () => {
    if (activeRenderer === 'cytoscape') zoomCyRelative(0.8);
    else if (activeRenderer === 'd3gv' || activeRenderer === 'mermaid')
      zoomSvgFromViewportCenter(0.8);
  });
  document.getElementById('btn-zoom-fit')?.addEventListener('click', () => {
    if (activeRenderer === 'cytoscape' && cyInstance) {
      cyInstance.fit(undefined, 40);
      syncZoomPct();
      return;
    }
    if (activeRenderer === 'd3gv' || activeRenderer === 'mermaid') fitSvgPanorama();
  });
}

// ── domain data ──────────────────────────────────────────────────────────────
function mergeSelectedDomainPayloads() {
  const domains = ERD_DATA && ERD_DATA.domains;
  if (!domains) return { entities: [], relations: [] };
  const keys = Object.keys(domains);
  if (!keys.length) return { entities: [], relations: [] };
  const on = keys.filter(k => enabledDomains.has(k));
  if (!on.length) return { entities: [], relations: [] };
  if (on.length === 1) return domains[on[0]];
  return mergeDomainPayloads(on.map(k => domains[k]));
}

function applyNeighborhoodScope(raw) {
  const entities = raw.entities || [];
  const relations = raw.relations || [];
  if (!entities.length) return { entities, relations };
  return { entities, relations };
}

function getDomainData() {
  return applyNeighborhoodScope(mergeSelectedDomainPayloads());
}

// ════════════════════════════════════════════════════════════════════════════
//  Renderer 1 — Graphviz SVG via @hpcc-js/wasm-graphviz
// ════════════════════════════════════════════════════════════════════════════

async function ensureGraphvizApi() {
  if (gvApi) return gvApi;
  const mod = await import(__GRAPHVIZ_URL__);
  const Cls = mod.Graphviz || mod.default?.Graphviz || mod.default;
  if (!Cls || typeof Cls.load !== 'function') {
    throw new Error('Graphviz.load() was not found in @hpcc-js/wasm-graphviz');
  }
  gvApi = await Cls.load();
  return gvApi;
}

async function initD3Graphviz() {
  const cont = document.getElementById('d3gv-container');
  if (!cont) return;
  cont.innerHTML = '<div class="erd-loading">&#x23F3; Loading Graphviz…</div>';

  const { entities, relations } = getDomainData();
  currentEntities = entities || [];
  currentRelations = relations || [];

  const dot = buildDotSource();
  const engine = getGvEngine();
  try {
    const api = await ensureGraphvizApi();
    const svg = api.layout(dot, 'svg', engine);
    cont.innerHTML =
      '<div class="erd-svg-viewport" id="gv-viewport">' +
        '<div class="erd-svg-panner" id="gv-panner">' + svg + '</div></div>';
    const svgEl = cont.querySelector('#gv-panner svg');
    if (svgEl) {
      svgEl.removeAttribute('width');
      svgEl.removeAttribute('height');
      const gg = svgEl.querySelector('g.graph');
      const bgPoly = gg && gg.querySelector('polygon');
      if (bgPoly) {
        const fill = String(bgPoly.getAttribute('fill') || '').toLowerCase();
        if (fill === '#f8fafc' || fill === '#f4f5f7' || fill === 'lightgray' || fill === 'lightgrey')
          bgPoly.setAttribute('fill', 'none');
      }
    }
    svgPan.vpid = 'gv-viewport';
    svgPan.pnid = 'gv-panner';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (!consumePendingSvgPan('d3gv')) {
          fitSvgPanorama();
        }
        attachSvgViewportInteraction();
      });
    });
    onGvRendered();
    syncZoomPct();
  } catch(e) {
    cont.innerHTML = '<div class="erd-error">Graphviz render error:\n' + e + '</div>';
  }
}

function onGvRendered() {
  const root = document.getElementById('d3gv-container');
  if (!root) return;
  const nodes = root.querySelectorAll('g.node');
  const edges = root.querySelectorAll('g.edge');
  nodes.forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('mouseenter', () => {
      const title = el.querySelector('title')?.textContent?.trim() || '';
      nodes.forEach(n => {
        n.style.opacity = n.querySelector('title')?.textContent?.trim() === title ? '1' : '0.35';
      });
      edges.forEach(e => {
        const edgeTitle = e.querySelector('title')?.textContent?.trim() || '';
        e.style.opacity = edgeTitle.includes(title) ? '1' : '0.2';
      });
    });
    el.addEventListener('mouseleave', () => {
      nodes.forEach(n => n.style.opacity = '1');
      edges.forEach(e => e.style.opacity = '1');
    });
  });
}

function getGvEngine() {
  if (activeLayout === 'gv-dot-lr' || activeLayout === 'gv-dot-tb') return 'dot';
  if (activeLayout === 'gv-neato')  return 'neato';
  if (activeLayout === 'gv-fdp')    return 'fdp';
  if (activeLayout === 'gv-circo')  return 'circo';
  return 'dot';
}

// ════════════════════════════════════════════════════════════════════════════
//  Renderer 2 — Cytoscape.js
// ════════════════════════════════════════════════════════════════════════════
async function initCytoscape() {
  const cont = document.getElementById('cy-container');
  if (!cont) return;
  cont.innerHTML = '<div class="erd-loading">&#x23F3; Loading Cytoscape…</div>';

  if (cyInteract) cyInteract.abort();
  cyInteract = new AbortController();
  const cySig = cyInteract.signal;

  try {
    await loadScript('https://unpkg.com/dagre@0.8.5/dist/dagre.min.js',       'dagre-umd');
    await loadScript('https://unpkg.com/cytoscape@3.30.2/dist/cytoscape.min.js',       'cytoscape-script');
    await loadScript('https://unpkg.com/cytoscape-dagre@2.5.0/cytoscape-dagre.js', 'cy-dagre');
  } catch(e) {
    cont.innerHTML = '<div class="erd-error">Cytoscape loading error:\n' + e + '</div>';
    return;
  }

  cont.innerHTML = '<div id="cy-graph" style="width:100%;height:100%;background:transparent;"></div>';

  const { entities, relations } = getDomainData();
  currentEntities = entities || [];
  currentRelations = relations || [];

  const isLR = activeLayout === 'cy-dagre-lr';
  const elements = [
    ...currentEntities.map(nd => ({
      group: 'nodes',
      data:  { id: nd.id, label: nd.label || nd.id,
                fields: nd.fields || [], color: nd.color || '#3b82f6' },
    })),
    ...currentRelations.map(ed => ({
      group: 'edges',
      data:  { id: 'e_' + ed.source + '_' + ed.target,
                source: ed.source, target: ed.target, label: ed.label || '' },
    })),
  ];

  if (cyInstance) { try { cyInstance.destroy(); } catch(_){} }

  const preserveCy = pendingViewportRestore && pendingViewportRestore.kind === 'cy';

  cyInstance = cytoscape({
    container: document.getElementById('cy-graph'),
    elements,
    style:  buildCytoscapeStyle(),
    layout: { name: 'dagre', rankDir: isLR ? 'LR' : 'TB',
               nodeSep: 60, rankSep: 100, padding: 40,
               animate: !preserveCy, animationDuration: preserveCy ? 0 : 400 },
    minZoom: MIN_SCALE,
    maxZoom: MAX_SCALE,
    zoomingEnabled: true,
    userZoomingEnabled: false,
    boxSelectionEnabled: false,
  });

  cyInstance.on('zoom', () => syncZoomPct());

  cyInstance.one('layoutstop', () => {
    const p = pendingViewportRestore;
    if (p && p.kind === 'cy' && activeRenderer === 'cytoscape') {
      cyInstance.zoom(p.zoom);
      cyInstance.pan(p.pan);
      pendingViewportRestore = null;
    }
    syncZoomPct();
  });

  const cyGraph = document.getElementById('cy-graph');
  cyGraph.addEventListener(
    'wheel',
    (e) => {
      e.preventDefault();
      cyWheelAccum += e.deltaY;
      if (cyWheelRaf == null) cyWheelRaf = requestAnimationFrame(flushCyWheelZoom);
    },
    { passive: false, signal: cySig },
  );

  syncZoomPct();
}

function buildCytoscapeStyle() {
  return [
    { selector: 'node', style: {
        shape: 'roundrectangle', 'background-color': 'data(color)',
        label: 'data(label)', color: '#fff', 'font-size': '13px',
        'font-weight': 'bold', 'text-valign': 'center', 'text-halign': 'center',
        padding: '14px', 'text-wrap': 'wrap', 'text-max-width': '180px',
        'min-width': '160px', 'border-width': 0,
    } },
    { selector: 'edge', style: {
        width: 1.5, 'line-color': '#94a3b8',
        'target-arrow-color': '#94a3b8', 'target-arrow-shape': 'triangle',
        'curve-style': 'bezier', label: 'data(label)',
        'font-size': '10px', color: '#64748b',
        'text-background-color': '#fff', 'text-background-opacity': 0.8,
        'text-background-padding': '2px',
    } },
    { selector: 'node:selected', style: {
        'border-width': 3, 'border-color': '#1d4ed8', 'background-color': '#2563eb',
    } },
    { selector: 'edge:selected', style: {
        'line-color': '#2563eb', 'target-arrow-color': '#2563eb', width: 2.5,
    } },
  ];
}

// ════════════════════════════════════════════════════════════════════════════
//  Renderer 3 — Mermaid
// ════════════════════════════════════════════════════════════════════════════
async function initMermaid() {
  const cont = document.getElementById('mermaid-container');
  if (!cont) return;
  cont.innerHTML = '<div class="erd-loading">&#x23F3; Loading Mermaid…</div>';
  try {
    const m = await import(__MERMAID_URL__);
    const mermaid = m.default || m;
    mermaid.initialize({ startOnLoad: false, theme: 'default',
                          er: { useMaxWidth: false } });
    const { svg } = await mermaid.render('mermaid-erd-svg', buildMermaidSource());
    cont.innerHTML =
      '<div class="erd-svg-viewport" id="mm-viewport">' +
        '<div class="erd-svg-panner" id="mm-panner">' + svg + '</div></div>';
    const svgEl = cont.querySelector('#mm-panner svg');
    if (svgEl) {
      svgEl.removeAttribute('width');
      svgEl.removeAttribute('height');
    }
    svgPan.vpid = 'mm-viewport';
    svgPan.pnid = 'mm-panner';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (!consumePendingSvgPan('mermaid')) {
          fitSvgPanorama();
        }
        attachSvgViewportInteraction();
      });
    });
    syncZoomPct();
  } catch(e) {
    cont.innerHTML = '<div class="erd-error">Mermaid error:\n' + e + '</div>';
  }
}

// ════════════════════════════════════════════════════════════════════════════
//  DOT / Mermaid source builders
// ════════════════════════════════════════════════════════════════════════════
function buildDotSource() {
  const { entities, relations } = getDomainData();
  const isLR = activeLayout === 'gv-dot-lr' || activeLayout === 'cy-dagre-lr';
  const lines = ['digraph ERD {'];
  // Neato ignores rankdir / nodesep / ranksep; those attrs produce a poor spring layout. Use
  // spring-specific spacing (see graphviz attrs: overlap, sep) without changing dot/fdp/circo.
  if (activeLayout === 'gv-neato') {
    lines.push(
      '  graph [fontname="Helvetica" bgcolor=transparent pad="0.5" '
        + 'overlap=false splines=false sep="+40"]',
    );
  } else {
    lines.push(
      '  graph [rankdir=' + (isLR ? 'LR' : 'TB') +
        ' fontname="Helvetica" bgcolor=transparent pad="0.5" nodesep="0.8" ranksep="1.2"]',
    );
  }
  lines.push(
    '  node  [shape=none fontname="Helvetica" fontsize=11 margin="0"]',
    '  edge  [fontname="Helvetica" fontsize=9 color="#94a3b8" arrowsize=0.7]',
    '',
  );

  for (const nd of (entities || [])) {
    const color = nd.color || '#3b82f6';
    const rows  = (nd.fields || []).map(f => {
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
    }).join('\n      ');

    lines.push(
      '  "' + nd.id + '" [label=<<TABLE BGCOLOR="white" BORDER="1" CELLBORDER="0" ' +
      'CELLSPACING="0" CELLPADDING="4" STYLE="ROUNDED" COLOR="' + color + '">' +
      '<TR><TD COLSPAN="3" BGCOLOR="' + color + '" ALIGN="CENTER">' +
      '<FONT COLOR="white" POINT-SIZE="12"><B>' + escHtml(nd.label || nd.id) + '</B></FONT>' +
      '</TD></TR>' + rows + '</TABLE>>]'
    );
  }

  lines.push('');
  for (const ed of (relations || [])) {
    const lbl = ed.label ? ' [label="' + escHtml(ed.label) + '" fontsize=9]' : '';
    lines.push('  "' + ed.source + '" -> "' + ed.target + '"' + lbl);
  }
  lines.push('}');
  return lines.join('\n');
}

function buildMermaidSource() {
  const { entities, relations } = getDomainData();
  const lines = ['erDiagram'];
  for (const nd of (entities || [])) {
    lines.push('  ' + nd.id.replace(/[^\w]/g,'_') + ' {');
    for (const f of (nd.fields || [])) {
      lines.push('    ' + (f.type || 'string').replace(/[^\w]/g, '_') +
                 ' ' + f.name.replace(/[^\w]/g, '_'));
    }
    lines.push('  }');
  }
  for (const ed of (relations || [])) {
    lines.push('  ' + ed.source.replace(/[^\w]/g,'_') + ' ||--o{ ' +
               ed.target.replace(/[^\w]/g,'_') +
               ' : "' + escHtml(ed.label || 'has') + '"');
  }
  return lines.join('\n');
}

// ════════════════════════════════════════════════════════════════════════════
//  Renderer switching
// ════════════════════════════════════════════════════════════════════════════
const ALL_CONT_IDS = [
  'd3gv-container', 'cy-container',
  'mermaid-container',
];
const RENDERER_SHOWS = {
  d3gv:      ['d3gv-container'],
  cytoscape: ['cy-container'],
  mermaid:   ['mermaid-container'],
};

function buildModeDockHtml() {
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
    .map((r) => {
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
    })
    .join('');
}

let modeDockWired = false;

function syncModeDock() {
  const dock = document.getElementById('mode-dock');
  if (!dock) return;
  dock.querySelectorAll('.mode-btn').forEach((btn) => {
    const key = btn.getAttribute('data-mode');
    let on = false;
    if (key === 'mermaid') on = activeRenderer === 'mermaid';
    else if (key && key.indexOf('cy-') === 0)
      on = activeRenderer === 'cytoscape' && activeLayout === key;
    else if (key) on = activeRenderer === 'd3gv' && activeLayout === key;
    btn.classList.toggle('active', on);
  });
}

function applyModePreset(key) {
  if (key === 'mermaid') {
    activeRenderer = 'mermaid';
  } else if (key === 'cy-dagre-lr' || key === 'cy-dagre-tb') {
    activeRenderer = 'cytoscape';
    activeLayout = key;
  } else {
    activeRenderer = 'd3gv';
    activeLayout = key;
  }
  switchRenderer(activeRenderer);
}

function initModeDock() {
  const dock = document.getElementById('mode-dock');
  if (!dock) return;
  dock.innerHTML = buildModeDockHtml();
  if (modeDockWired) return;
  modeDockWired = true;
  dock.addEventListener('click', (evt) => {
    const b = evt.target.closest('.mode-btn');
    if (!b || !dock.contains(b)) return;
    const k = b.getAttribute('data-mode');
    if (k) applyModePreset(k);
  });
}

function switchRenderer(name) {
  activeRenderer = name;
  for (const id of ALL_CONT_IDS) {
    const el = document.getElementById(id);
    if (el) { el.style.display = 'none'; el.classList.remove('active'); }
  }
  const zt = document.getElementById('zoom-toolbar');
  if (zt) zt.style.display = '';

  for (const id of (RENDERER_SHOWS[name] || [])) {
    const el = document.getElementById(id);
    if (el) { el.style.display = ''; el.classList.add('active'); }
  }

  syncModeDock();
  switch (name) {
    case 'd3gv':      initD3Graphviz(); break;
    case 'cytoscape': initCytoscape();  break;
    case 'mermaid':   initMermaid();    break;
  }
}

function renderDomainPanel() {
  const domains = ERD_DATA?.domains || {};
  const keys = Object.keys(domains);
  const picker = document.getElementById('domain-picker');
  if (!picker) return;
  if (keys.length <= 1) {
    picker.style.display = 'none';
    return;
  }
  const accents = ERD_DATA.domain_accent_colors || {};
  const legendIcons = ERD_DATA.domain_legend_icons || {};
  picker.style.display = 'flex';
  picker.innerHTML =
    '<div class="legend-title">Domains</div>' +
    keys.map((k) => {
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
    }).join('');
}

function wireDomainPickerOnce() {
  if (domainPickerWired) return;
  const picker = document.getElementById('domain-picker');
  if (!picker) return;
  domainPickerWired = true;
  picker.addEventListener('click', (evt) => {
    const btn = evt.target.closest('.domain-row');
    if (!btn || !picker.contains(btn)) return;
    const key = btn.getAttribute('data-domain');
    const domains = ERD_DATA?.domains || {};
    if (!key || !domains[key]) return;
    if (enabledDomains.has(key)) enabledDomains.delete(key);
    else enabledDomains.add(key);
    renderDomainPanel();
    switchRenderer(activeRenderer);
  });
}

function initNeighborhoodFilter() {
  const grp = document.getElementById('neighborhood-filter');
  const cb = document.getElementById('neighborhood-expand');
  if (!grp || !cb) return;
  grp.style.display = 'flex';
  cb.checked = ERD_DATA.initial_include_one_hop !== false;
  if (nhFilterWired) return;
  nhFilterWired = true;
  cb.addEventListener('change', () => {
    const domains = ERD_DATA?.domains || {};
    const requests = [...enabledDomains]
      .filter((key) => domains[key])
      .map((key) => ({
        key,
        qualname: ERD_DATA.domain_qualifiers && ERD_DATA.domain_qualifiers[key],
      }))
      .filter((row) => row.qualname);
    window.parent.postMessage(
      {
        source: 'maxitor-erd',
        type: 'set-one-hop',
        include: cb.checked,
        domains: requests,
        domain_qualifier_colors: ERD_DATA.domain_qualifier_colors || {},
      },
      '*',
    );
  });
}

function initDomainPicker() {
  wireDomainPickerOnce();
  const domains = ERD_DATA?.domains || {};
  const keys = Object.keys(domains);
  const picker = document.getElementById('domain-picker');
  if (!keys.length) {
    initNeighborhoodFilter();
    return;
  }
  if (!picker) {
    enabledDomains = new Set(keys);
    initNeighborhoodFilter();
    return;
  }

  if (keys.length === 1) {
    enabledDomains = new Set(keys);
    picker.style.display = 'none';
    initNeighborhoodFilter();
    return;
  }

  // Multiple bounded contexts: start with every domain visible (merged diagram).
  enabledDomains = new Set(keys);
  renderDomainPanel();
  initNeighborhoodFilter();
}

// ════════════════════════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════════════════════════
(function boot() {
  wireHostDomainPatchListener();
  initDomainPicker();
  initModeDock();
  installZoomChrome();
  switchRenderer('d3gv');
})();
/* Client-only ERD viewer script (not the former Python html_page module). */
