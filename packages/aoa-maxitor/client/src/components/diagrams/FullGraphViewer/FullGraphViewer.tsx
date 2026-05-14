// src/components/diagrams/FullGraphViewer/FullGraphViewer.tsx
import Box from "@mui/material/Box";
import type { EdgeData, Graph as G6Graph, GraphData, NodeData } from "@antv/g6";
import { useCallback, useLayoutEffect, useRef, useState } from "react";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { fullGraph } from "@/api/fullGraph";
import { svgDataUriForGraphNodeGlyphOnly } from "@/lib/icons";
import type { InterchangeGraphG6Payload } from "@/model/fullGraph";
import { NodeTypeLegend } from "@/components/ui/NodeTypeLegend";

const NODE_BASE_RING_LINE_WIDTH = 0.75;

const GRAPH_HOVER_LABEL_SX = {
  "& .graph-hover-label": {
    position: "absolute",
    zIndex: 1,
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    color: "#0f172a",
    fontSize: "10px",
    fontWeight: 400,
    letterSpacing: "0.01em",
    maxWidth: 168,
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
    lineHeight: 1.3,
    transform: "translate(-50%, 0)",
    py: "3px",
    pl: "7px",
    pr: "8px",
    borderRadius: 0,
    bgcolor: "rgba(255,255,255,0.96)",
    border: "1px solid rgba(0,0,0,0.08)",
    borderLeft: "3px solid #95a5a6",
    boxShadow: "0 2px 10px rgba(0,0,0,0.07)",
  },
} as const;

/** Canvas shell — dot grid surface under G6 (MUI ``sx``, no global CSS import). */
const CANVAS_SHELL_SX = {
  position: "absolute" as const,
  inset: 0,
  zIndex: 0,
  bgcolor: "var(--ix-surface)",
  backgroundImage: "radial-gradient(var(--ix-grid-dot) 1px, transparent 1px)",
  backgroundSize: "20px 20px",
  boxShadow: "inset 0 1px 0 rgba(255, 255, 255, 0.65)",
};

function buildGraphDataAndAdjacency(payload: InterchangeGraphG6Payload): {
  graphData: GraphData;
  adjIndex: Record<string, { edges: Set<string>; neighbors: Set<string> }>;
  nodeById: Map<string, NodeData>;
} {
  const nodeById = new Map<string, NodeData>();
  const adjIndex: Record<string, { edges: Set<string>; neighbors: Set<string> }> = {};
  const initAdj = (nid: string) => {
    if (!adjIndex[nid]) adjIndex[nid] = { edges: new Set(), neighbors: new Set() };
  };

  const nodes: NodeData[] = payload.nodes.map((n) => {
    const row = { ...n } as NodeData & { x?: number; y?: number };
    const style = row.style as { x?: number; y?: number } | undefined;
    if (style && typeof style.x === "number" && typeof style.y === "number") {
      row.x = style.x;
      row.y = style.y;
    }
    const nodeId = String(row.id);
    nodeById.set(nodeId, row);
    initAdj(nodeId);
    return row;
  });

  const edges = (payload.edges as GraphData["edges"]) ?? [];
  for (const edge of edges) {
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

  return { graphData: { nodes, edges }, adjIndex, nodeById };
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
      iterations: 220,
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
      alphaDecay: 0.012,
      alphaMin: 0.0015,
      velocityDecay: 0.42,
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
 * Interchange graph viewer — G6 circle + glyph icons, d3-force, bubble plugins, MUI-positioned
 * legend / zoom chrome, neighbor glow, and hover labels in ``#graph-hover-labels`` (sibling layer
 * above the G6 container so cards are not covered by the graph canvas).
 *
 * G6 is lazy-loaded on first open; chrome uses MUI ``sx`` (no raw CSS import).
 */
export function FullGraphViewer() {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  /** HTML overlay for hover cards — must sit above G6’s internal canvas/WebGL stack, not inside it. */
  const hoverOverlayRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<G6Graph | null>(null);

  const loadInterchange = useCallback(
    () =>
      Promise.all([fullGraph(), import("@antv/g6")]).then(([p, mod]) => ({
        payload: p,
        mod,
      })),
    [],
  );
  const { data, loading, error } = useDiagramLoader(loadInterchange);
  const payload = data?.payload ?? null;
  const graphModule = data?.mod ?? null;

  const [zoomPct, setZoomPct] = useState(100);
  const [graphError, setGraphError] = useState<string | null>(null);

  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    const hoverLayer = hoverOverlayRef.current;
    const mod = graphModule;
    if (!canvas || !hoverLayer || !payload || !mod) return undefined;

    setGraphError(null);

    const { graphData, adjIndex, nodeById } = buildGraphDataAndAdjacency(payload);

    const graph = buildGraph(mod.Graph, canvas, payload, graphData);
    graphRef.current = graph;

    const syncZoom = () => {
      try {
        const z = graph.getZoom();
        setZoomPct(Math.round(z * 100));
      } catch {
        setZoomPct(0);
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
      if (hoverLabelNodeId == null) {
        if (hoverLayer.firstChild) hoverLayer.innerHTML = "";
        return;
      }
      hoverLayer.innerHTML = "";
      const adj = adjIndex[hoverLabelNodeId];
      const labelIds = [String(hoverLabelNodeId)];
      if (adj) {
        for (const nid of adj.neighbors) {
          if (labelIds.length >= 9) break;
          labelIds.push(String(nid));
        }
      }
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
      if (sid === hoverLabelNodeId) return;
      hoverLabelNodeId = sid;
      syncHoverLabels();
      applyNeighborGlow(sid);
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
      if (hoverLabelNodeId != null) scheduleHoverOverlaySync();
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
      if (hoverLabelNodeId != null) scheduleHoverOverlaySync();
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
        setGraphError(err instanceof Error ? err.message : String(err));
      });

    return () => {
      ro.disconnect();
      canvas.removeEventListener("wheel", onWheel);
      graph.off("node:pointerenter", onNodeOver);
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
      setZoomPct(Math.round(g.getZoom() * 100));
    } catch {
      setZoomPct(0);
    }
  };

  const doFit = () => {
    const g = graphRef.current;
    if (!g) return;
    void g.fitView().then(() => {
      try {
        setZoomPct(Math.round(g.getZoom() * 100));
      } catch {
        setZoomPct(0);
      }
    });
  };

  return (
    <DiagramShell loading={loading} error={error ?? graphError}>
      {payload && graphModule && !graphError && (
        <Box
          ref={rootRef}
          className="ix-interchange-viewport"
          sx={{
            flex: 1,
            minHeight: 0,
            minWidth: 0,
            position: "relative",
            overflow: "hidden",
            ...GRAPH_HOVER_LABEL_SX,
          }}
        >
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

          <NodeTypeLegend items={payload.legend_items} />

          <ZoomToolbar
            zoomPct={zoomPct}
            onZoomIn={() => void doZoom(1.25)}
            onZoomOut={() => void doZoom(0.8)}
            onFit={doFit}
          />
        </Box>
      )}
    </DiagramShell>
  );
}
