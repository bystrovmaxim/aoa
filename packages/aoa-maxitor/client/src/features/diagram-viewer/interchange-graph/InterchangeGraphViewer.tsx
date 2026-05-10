// packages/aoa-maxitor/client/src/features/diagram-viewer/interchange-graph/InterchangeGraphViewer.tsx
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import type { EdgeData, Graph as G6Graph, GraphData, NodeData } from "@antv/g6";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import interchangeChromeCss from "../erd/shell/interchange_chrome.css?raw";
import { svgDataUriForGraphNodeGlyphOnly, svgDataUriForGraphNodeIcon } from "../../../shared/icons";
import { fetchInterchangeGraphPayload } from "./fetchInterchangeGraphPayload";
import type { InterchangeGraphG6Payload } from "./types";

const NODE_BASE_RING_LINE_WIDTH = 0.75;

/** Canvas shell copied from the archived ``template.html`` (not in ``interchange_chrome.css``). */
const CANVAS_SHELL_SX = {
  position: "absolute" as const,
  inset: 0,
  zIndex: 0,
  bgcolor: "var(--ix-surface)",
  backgroundImage: "radial-gradient(var(--ix-grid-dot) 1px, transparent 1px)",
  backgroundSize: "20px 20px",
  boxShadow: "inset 0 1px 0 rgba(255, 255, 255, 0.65)",
};

function graphDataFromPayload(payload: InterchangeGraphG6Payload): GraphData {
  const nodes: NodeData[] = payload.nodes.map((n) => {
    const row = { ...n } as NodeData & { x?: number; y?: number };
    const style = row.style as { x?: number; y?: number } | undefined;
    if (style && typeof style.x === "number" && typeof style.y === "number") {
      row.x = style.x;
      row.y = style.y;
    }
    return row;
  });
  return { nodes, edges: payload.edges as GraphData["edges"] };
}

function buildAdjacency(graphData: GraphData): {
  adjIndex: Record<string, { edges: Set<string>; neighbors: Set<string> }>;
  nodeById: Map<string, NodeData>;
} {
  const adjIndex: Record<string, { edges: Set<string>; neighbors: Set<string> }> = {};
  const initAdj = (nid: string) => {
    if (!adjIndex[nid]) adjIndex[nid] = { edges: new Set(), neighbors: new Set() };
  };
  for (const edge of graphData.edges ?? []) {
    const s = String(edge.source);
    const t = String(edge.target);
    initAdj(s);
    initAdj(t);
    if (edge.id != null) {
      adjIndex[s].edges.add(String(edge.id));
      adjIndex[t].edges.add(String(edge.id));
    }
    adjIndex[s].neighbors.add(t);
    adjIndex[t].neighbors.add(s);
  }
  for (const node of graphData.nodes ?? []) initAdj(String(node.id));
  const nodeById = new Map<string, NodeData>();
  for (const node of graphData.nodes ?? []) nodeById.set(String(node.id), node);
  return { adjIndex, nodeById };
}

function nodeIdFromPointerEvt(evt: unknown): string | null {
  const e = evt as {
    target?: { id?: string };
    originalTarget?: { id?: string; parentElement?: unknown };
    targetType?: string;
    itemId?: string;
    items?: { id?: string }[];
  };
  if (e.targetType === "node" && e.target?.id != null) return String(e.target.id);
  let id: string | undefined = e.target?.id ?? e.originalTarget?.id ?? e.itemId;
  if (id == null && Array.isArray(e.items) && e.items[0]?.id != null) id = e.items[0].id;
  return id != null ? String(id) : null;
}

/**
 * Bubble-sets hulls are drawn after the first full render and sit on top of the graph.
 * Without ``pointerEvents: 'none'`` they steal hover from nodes/edges (no neighbor glow, no tooltips).
 */
function normalizeBubblePluginsForInterchange(raw: unknown[]): Record<string, unknown>[] {
  return raw.map((p) => {
    const o = p as Record<string, unknown>;
    if (o.type !== "bubble-sets") return o as Record<string, unknown>;
    const next: Record<string, unknown> = { ...o };
    if (next.pointerEvents == null) next.pointerEvents = "none";
    if (next.strokeOpacity == null) next.strokeOpacity = 0.55;
    if (next.fillOpacity == null) next.fillOpacity = 0.14;
    return next;
  });
}

function buildGraph(
  Graph: typeof import("@antv/g6").Graph,
  container: HTMLElement,
  payload: InterchangeGraphG6Payload,
  graphData: GraphData,
): G6Graph {
  const px = payload.constants.node_visual_px;
  const dagColor = payload.constants.dag_cycle_violation_color;
  const defaultEdge = "#95a5a6";
  const defaultColor = payload.constants.default_color;
  const nodeTypeMap = payload.node_type_map;

  const bubblePlugins = normalizeBubblePluginsForInterchange(payload.bubble_plugins ?? []);
  const plugins = bubblePlugins as never[];

  return new Graph({
    container,
    autoResize: true,
    animation: false,
    data: graphData,
    node: {
      type: "circle",
      style: (data: NodeData) => {
        const d = (data.data ?? {}) as Record<string, unknown>;
        const fillRaw = d.fill;
        const fill =
          fillRaw != null && String(fillRaw).trim() !== "" ? String(fillRaw).trim() : defaultColor;
        const nodeTypeRaw = d.node_type;
        const nodeType =
          nodeTypeRaw != null && String(nodeTypeRaw).trim() !== ""
            ? String(nodeTypeRaw).trim()
            : "unknown";
        const glyph = svgDataUriForGraphNodeGlyphOnly(nodeType);
        return {
          label: false,
          size: px,
          fill,
          iconSrc: glyph,
          stroke: "rgba(15, 23, 42, 0.14)",
          lineWidth: NODE_BASE_RING_LINE_WIDTH,
          opacity: 1,
          cursor: "grab",
          halo: false,
          shadowBlur: 0,
        };
      },
      state: {
        hub: {
          opacity: 1,
          halo: false,
          stroke: "#000000",
          lineWidth: NODE_BASE_RING_LINE_WIDTH,
          shadowBlur: 0,
        },
        nb: {
          opacity: 1,
          halo: false,
          stroke: "#000000",
          lineWidth: NODE_BASE_RING_LINE_WIDTH,
          shadowBlur: 0,
        },
      },
    },
    edge: {
      type: "line",
      style: (data: EdgeData) => {
        const d = (data.data ?? {}) as Record<string, unknown>;
        const viol = Boolean(d.isForbiddenDagCycle);
        const stroke = viol ? dagColor : defaultEdge;
        return {
          stroke,
          lineWidth: viol ? 2.4 : 1.2,
          opacity: 1,
          endArrow: true,
          label: false,
        };
      },
      state: {
        active: {
          lineWidth: 3.2,
          opacity: 1,
        },
      },
    },
    layout: {
      type: "d3-force",
      iterations: 320,
      animation: false,
      link: {
        distance: (edge: EdgeData) => {
          const st = nodeTypeMap[String(edge.source)] ?? "";
          const tt = nodeTypeMap[String(edge.target)] ?? "";
          return st === tt ? 72 : 200;
        },
        strength: (edge: EdgeData) => {
          const st = nodeTypeMap[String(edge.source)] ?? "";
          const tt = nodeTypeMap[String(edge.target)] ?? "";
          return st === tt ? 0.82 : 0.11;
        },
      },
      manyBody: { strength: -360, distanceMax: 1200 },
      collide: { radius: px * 0.5 + 7, strength: 0.95, iterations: 4 },
      center: { strength: 0.012 },
      alphaDecay: 0.008,
      alphaMin: 0.0008,
      velocityDecay: 0.36,
    },
    behaviors: [
      { type: "zoom-canvas", key: "zoom-canvas", enable: true },
      { type: "drag-element", key: "drag-element", dropEffect: "move" },
      "drag-canvas",
    ],
    plugins,
  });
}

/**
 * Interchange graph viewer — parity with the former Python ``template.html`` + inline G6 script:
 * circle + glyph icons, d3-force, bubble plugins, floating legend / zoom chrome from
 * ``interchange_chrome.css``, neighbor glow, and hover labels in ``#graph-hover-labels``
 * (sibling layer above the G6 container so cards are not covered by the graph canvas).
 *
 * G6 is lazy-loaded; styles are injected once per mount. A future optional path is to fetch
 * pre-built HTML from the API and render it via ``srcDoc`` if we need bit-identical output.
 */
export function InterchangeGraphViewer() {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  /** HTML overlay for hover cards — must sit above G6’s internal canvas/WebGL stack, not inside it. */
  const hoverOverlayRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<G6Graph | null>(null);

  const [payload, setPayload] = useState<InterchangeGraphG6Payload | null>(null);
  const [graphModule, setGraphModule] = useState<typeof import("@antv/g6") | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoomPct, setZoomPct] = useState("100%");

  const chromeStyleTag = useMemo(
    () => ({ __html: `${interchangeChromeCss}\n:root{--ix-surface:#f4f5f7;}` }),
    [],
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([fetchInterchangeGraphPayload(), import("@antv/g6")])
      .then(([p, mod]) => {
        if (cancelled) return;
        setPayload(p);
        setGraphModule(mod);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    const hoverLayer = hoverOverlayRef.current;
    const mod = graphModule;
    if (!canvas || !hoverLayer || !payload || !mod) return undefined;

    const graphData = graphDataFromPayload(payload);
    const { adjIndex, nodeById } = buildAdjacency(graphData);

    const graph = buildGraph(mod.Graph, canvas, payload, graphData);
    graphRef.current = graph;

    const syncZoom = () => {
      try {
        const z = graph.getZoom();
        setZoomPct(`${Math.round(z * 100)}%`);
      } catch {
        setZoomPct("—");
      }
    };

    let zoomRaf: number | null = null;
    const scheduleZoom = () => {
      if (zoomRaf != null) return;
      zoomRaf = requestAnimationFrame(() => {
        zoomRaf = null;
        syncZoom();
      });
    };

    const NODE_VISUAL_PX = payload.constants.node_visual_px;

    const xyFromPoint = (p: unknown): [number, number] | null => {
      if (p == null) return null;
      if (Array.isArray(p) && p.length >= 2) return [Number(p[0]), Number(p[1])];
      if (typeof p === "object" && p !== null && "x" in p && "y" in p) {
        const o = p as { x: number; y: number };
        if (typeof o.x === "number" && typeof o.y === "number") return [o.x, o.y];
      }
      return null;
    };

    /** Node center in canvas space; anchor just below the icon disk (``graph_node.html``). */
    const canvasPointForLabel = (id: string): [number, number] | null => {
      try {
        const pos = graph.getElementPosition(id);
        const xy = xyFromPoint(pos);
        if (xy) return [xy[0], xy[1] + NODE_VISUAL_PX / 2 + 6];
      } catch {
        /* ignore */
      }
      try {
        const b = graph.getElementRenderBounds(id) as {
          min?: unknown;
          max?: unknown;
        } | null;
        if (b?.min != null && b?.max != null) {
          const min = b.min as { x?: number; y?: number } | number[];
          const max = b.max as { x?: number; y?: number } | number[];
          const m0 = Array.isArray(min) ? min[0] : min.x;
          const m1 = Array.isArray(min) ? min[1] : min.y;
          const M0 = Array.isArray(max) ? max[0] : max.x;
          const M1 = Array.isArray(max) ? max[1] : max.y;
          if (
            typeof m0 === "number" &&
            typeof m1 === "number" &&
            typeof M0 === "number" &&
            typeof M1 === "number"
          ) {
            return [(m0 + M0) / 2, M1 + 4];
          }
        }
      } catch {
        /* ignore */
      }
      return null;
    };

    const containerOffsetFromCanvasPoint = (canvasPt: [number, number]): [number, number] | null => {
      const crCanvas = canvas.getBoundingClientRect();
      const crHover = hoverLayer.getBoundingClientRect();
      try {
        const client = graph.getClientByCanvas([canvasPt[0], canvasPt[1]]);
        const cxy = xyFromPoint(client);
        if (!cxy) return null;
        const xInCanvas = cxy[0] - crCanvas.left;
        const yInCanvas = cxy[1] - crCanvas.top;
        return [xInCanvas + (crCanvas.left - crHover.left), yInCanvas + (crCanvas.top - crHover.top)];
      } catch {
        return null;
      }
    };

    let hoverLabelNodeId: string | null = null;
    let glowClearTimer: ReturnType<typeof setTimeout> | null = null;
    let hoverPointerOutPending = false;
    let viewportQuietTimer: ReturnType<typeof setTimeout> | null = null;
    const HOVER_CLEAR_DELAY_MS = 420;

    type GlowSnap = { hubId: string; neighborIds: Set<string>; edgeIds: Set<string> };
    let hoverGlowSnap: GlowSnap | null = null;

    const clearViewportQuietTimer = () => {
      if (viewportQuietTimer != null) {
        clearTimeout(viewportQuietTimer);
        viewportQuietTimer = null;
      }
    };

    const clearNeighborGlow = () => {
      const prev = hoverGlowSnap;
      if (prev == null) return;
      const st: Record<string, string[]> = {};
      st[prev.hubId] = [];
      prev.neighborIds.forEach((nid) => {
        st[String(nid)] = [];
      });
      prev.edgeIds.forEach((eid) => {
        st[eid] = [];
      });
      void graph.setElementState(st, false);
      hoverGlowSnap = null;
    };

    const applyNeighborGlow = (nodeIdStr: string) => {
      const adj = adjIndex[nodeIdStr];
      if (!adj) return;
      const hub = String(nodeIdStr);
      const nbNorm = new Set<string>();
      adj.neighbors.forEach((x) => nbNorm.add(String(x)));
      const eActive = adj.edges;
      const st: Record<string, string[]> = {};
      const prev = hoverGlowSnap;

      if (prev == null) {
        st[hub] = ["hub"];
        nbNorm.forEach((s) => {
          if (s !== hub) st[s] = ["nb"];
        });
        eActive.forEach((eid) => {
          st[eid] = ["active"];
        });
      } else {
        const candNodes = new Set<string>([prev.hubId, hub]);
        prev.neighborIds.forEach((s) => candNodes.add(String(s)));
        nbNorm.forEach((s) => candNodes.add(s));
        for (const nid of candNodes) {
          const s = String(nid);
          if (s === hub) st[s] = ["hub"];
          else if (nbNorm.has(s)) st[s] = ["nb"];
          else st[s] = [];
        }
        const candEdges = new Set<string>();
        prev.edgeIds.forEach((eid) => candEdges.add(eid));
        eActive.forEach((eid) => candEdges.add(eid));
        for (const eid of candEdges) {
          st[eid] = eActive.has(eid) ? ["active"] : [];
        }
      }

      void graph.setElementState(st, false);
      hoverGlowSnap = {
        hubId: hub,
        neighborIds: new Set(nbNorm),
        edgeIds: new Set(eActive),
      };
    };

    let hoverOverlaySyncRaf: number | null = null;
    const syncHoverLabels = () => {
      hoverLayer.innerHTML = "";
      if (hoverLabelNodeId == null) return;
      const adj = adjIndex[hoverLabelNodeId];
      const labelIds = new Set<string>([String(hoverLabelNodeId)]);
      if (adj) adj.neighbors.forEach((nid) => labelIds.add(String(nid)));
      for (const id of labelIds) {
        const n = nodeById.get(id);
        if (!n) continue;
        const d = (n.data ?? {}) as Record<string, unknown>;
        const hoverText =
          d.label != null && String(d.label).trim() !== ""
            ? String(d.label)
            : d.title != null && String(d.title).trim() !== ""
              ? String(d.title)
              : d.graph_key != null && String(d.graph_key).trim() !== ""
                ? String(d.graph_key)
                : id;
        const fillRaw = d.fill;
        const fill =
          fillRaw != null && String(fillRaw).trim() !== "" ? String(fillRaw).trim() : "";
        const stripe = fill !== "" ? fill : "#95a5a6";
        const canvasPt = canvasPointForLabel(id);
        if (canvasPt == null) continue;
        const off = containerOffsetFromCanvasPoint(canvasPt);
        if (off == null) continue;
        const div = document.createElement("div");
        div.className = "graph-hover-label";
        div.textContent = hoverText;
        div.style.borderLeftColor = stripe;
        div.style.left = `${off[0]}px`;
        div.style.top = `${off[1]}px`;
        hoverLayer.appendChild(div);
      }
    };

    const scheduleHoverOverlaySync = () => {
      if (hoverOverlaySyncRaf != null) return;
      hoverOverlaySyncRaf = requestAnimationFrame(() => {
        hoverOverlaySyncRaf = null;
        syncHoverLabels();
      });
    };

    const armHoverClearDeferred = () => {
      if (glowClearTimer != null) {
        clearTimeout(glowClearTimer);
        glowClearTimer = null;
      }
      glowClearTimer = setTimeout(() => {
        clearNeighborGlow();
        hoverLabelNodeId = null;
        hoverPointerOutPending = false;
        scheduleHoverOverlaySync();
        glowClearTimer = null;
        clearViewportQuietTimer();
      }, HOVER_CLEAR_DELAY_MS);
    };

    const onNodeOver = (evt: unknown) => {
      hoverPointerOutPending = false;
      clearViewportQuietTimer();
      if (glowClearTimer) {
        clearTimeout(glowClearTimer);
        glowClearTimer = null;
      }
      const sid = nodeIdFromPointerEvt(evt);
      if (sid == null) return;
      applyNeighborGlow(sid);
      hoverLabelNodeId = sid;
      scheduleHoverOverlaySync();
    };

    const onPointerMove = (evt: unknown) => {
      const sid = nodeIdFromPointerEvt(evt);
      if (sid == null || sid === hoverLabelNodeId) return;
      onNodeOver(evt);
    };

    const onNodeOut = () => {
      hoverPointerOutPending = true;
      armHoverClearDeferred();
    };

    const onCanvasClick = () => {
      hoverPointerOutPending = false;
      clearViewportQuietTimer();
      if (glowClearTimer) {
        clearTimeout(glowClearTimer);
        glowClearTimer = null;
      }
      clearNeighborGlow();
      hoverLabelNodeId = null;
      scheduleHoverOverlaySync();
    };

    const onCanvasLeave = () => {
      hoverPointerOutPending = false;
      clearViewportQuietTimer();
      if (glowClearTimer) {
        clearTimeout(glowClearTimer);
        glowClearTimer = null;
      }
      clearNeighborGlow();
      hoverLabelNodeId = null;
      scheduleHoverOverlaySync();
    };

    const onAfterTransform = () => {
      scheduleZoom();
      scheduleHoverOverlaySync();
      if (hoverPointerOutPending && glowClearTimer != null) {
        clearTimeout(glowClearTimer);
        glowClearTimer = null;
      }
      clearViewportQuietTimer();
      viewportQuietTimer = setTimeout(() => {
        viewportQuietTimer = null;
        if (hoverPointerOutPending && hoverGlowSnap !== null) armHoverClearDeferred();
      }, 170);
    };

    const onWheel = () => {
      scheduleZoom();
      scheduleHoverOverlaySync();
      if (hoverPointerOutPending && glowClearTimer != null) {
        clearTimeout(glowClearTimer);
        glowClearTimer = null;
      }
      clearViewportQuietTimer();
      viewportQuietTimer = setTimeout(() => {
        viewportQuietTimer = null;
        if (hoverPointerOutPending && hoverGlowSnap !== null) armHoverClearDeferred();
      }, 170);
    };

    graph.on("node:pointerenter", onNodeOver);
    graph.on("node:pointerover", onNodeOver);
    graph.on("node:pointermove", onPointerMove);
    graph.on("node:pointerout", onNodeOut);
    graph.on("node:pointerleave", onNodeOut);
    graph.on("canvas:click", onCanvasClick);
    graph.on("canvas:pointerleave", onCanvasLeave);
    graph.on("aftertransform", onAfterTransform);
    graph.on("node:dragend", scheduleHoverOverlaySync);
    canvas.addEventListener("wheel", onWheel, { passive: true });

    const ro = new ResizeObserver(() => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (w > 0 && h > 0) graph.resize(w, h);
      scheduleZoom();
      scheduleHoverOverlaySync();
    });
    ro.observe(canvas);

    void graph
      .render()
      .then(async () => {
        await graph.fitView();
        syncZoom();
        scheduleHoverOverlaySync();
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
      });

    return () => {
      ro.disconnect();
      canvas.removeEventListener("wheel", onWheel);
      graph.off("node:pointerenter", onNodeOver);
      graph.off("node:pointerover", onNodeOver);
      graph.off("node:pointermove", onPointerMove);
      graph.off("node:pointerout", onNodeOut);
      graph.off("node:pointerleave", onNodeOut);
      graph.off("canvas:click", onCanvasClick);
      graph.off("canvas:pointerleave", onCanvasLeave);
      graph.off("aftertransform", onAfterTransform);
      graph.off("node:dragend", scheduleHoverOverlaySync);
      if (glowClearTimer) clearTimeout(glowClearTimer);
      clearViewportQuietTimer();
      hoverLayer.innerHTML = "";
      graph.destroy();
      graphRef.current = null;
    };
  }, [payload, graphModule]);

  const doZoom = async (factor: number) => {
    const g = graphRef.current;
    if (!g) return;
    const cur = g.getZoom();
    const next = Math.min(4, Math.max(0.15, cur * factor));
    await g.zoomTo(next, false);
    try {
      setZoomPct(`${Math.round(g.getZoom() * 100)}%`);
    } catch {
      setZoomPct("—");
    }
  };

  if (loading) {
    return (
      <Box sx={{ flex: 1, display: "grid", placeItems: "center" }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ flex: 1, p: 2 }}>
        <Typography color="error" variant="body2">
          {error}
        </Typography>
      </Box>
    );
  }

  if (!payload) {
    return null;
  }

  return (
    <Box
      ref={rootRef}
      className="ix-interchange-viewport"
      sx={{
        flex: 1,
        minHeight: 0,
        minWidth: 0,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <style dangerouslySetInnerHTML={chromeStyleTag} />

      <Box ref={canvasRef} sx={CANVAS_SHELL_SX} />

      <Box
        ref={hoverOverlayRef}
        id="graph-hover-labels"
        aria-hidden
        sx={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          zIndex: 30,
          overflow: "visible",
        }}
      />

      <div id="color-legend" className="color-legend ix-legend-panel">
        <div className="legend-title">Node types</div>
        {payload.legend_items.map((it) => (
          <div className="row" key={it.type} title={it.type}>
            <img
              className="legend-icon"
              src={svgDataUriForGraphNodeIcon(it.color, it.type)}
              width={20}
              height={20}
              alt=""
            />
            <span>{it.type}</span>
          </div>
        ))}
      </div>

      <div id="zoom-toolbar" className="zoom-toolbar" aria-label="View controls">
        <div className="zoom-cluster">
          <button type="button" className="zoom-btn" id="btn-zoom-in" title="Zoom in" onClick={() => void doZoom(1.25)}>
            +
          </button>
          <button type="button" className="zoom-btn" id="btn-zoom-out" title="Zoom out" onClick={() => void doZoom(0.8)}>
            −
          </button>
          <button
            type="button"
            className="zoom-btn"
            id="btn-zoom-fit"
            title="Fit to window"
            onClick={() => {
              const g = graphRef.current;
              if (!g) return;
              void g.fitView().then(() => {
                try {
                  setZoomPct(`${Math.round(g.getZoom() * 100)}%`);
                } catch {
                  setZoomPct("—");
                }
              });
            }}
          >
            ⊡
          </button>
          <span className="zoom-pct" id="zoom-pct">
            {zoomPct}
          </span>
        </div>
      </div>
    </Box>
  );
}
