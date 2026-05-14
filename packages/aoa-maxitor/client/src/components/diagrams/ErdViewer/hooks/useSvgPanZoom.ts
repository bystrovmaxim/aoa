// src/components/diagrams/ErdViewer/hooks/useSvgPanZoom.ts
/**
 * Pan / zoom / wheel zoom for a viewport wrapping an SVG panner (same mechanics as the legacy HTML viewer).
 */

import { useCallback, useEffect, useRef, useState } from "react";

const MIN_SCALE = 0.005;
const MAX_SCALE = 2.5;
const WHEEL_ZOOM_SENSITIVITY = 0.0045;

function clampUserScale(scale: number): number {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
}

export function useSvgPanZoom() {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const pannerRef = useRef<HTMLDivElement | null>(null);
  const panRef = useRef({ scale: 1, tx: 0, ty: 0 });
  const dragRef = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const wheelAccumRef = useRef(0);
  const wheelRafRef = useRef<number | null>(null);
  const wheelClientRef = useRef<{ x?: number; y?: number }>({});
  const interactAbortRef = useRef<AbortController | null>(null);
  const resizeFitRafRef = useRef<number | null>(null);
  const [zoomPct, setZoomPct] = useState(100);

  const applyTransform = useCallback(() => {
    const panner = pannerRef.current;
    if (!panner) return;
    const { scale, tx, ty } = panRef.current;
    panner.style.transform = `translate(${tx}px,${ty}px) scale(${scale})`;
    setZoomPct(Math.round(scale * 100));
  }, []);

  const fitToContainer = useCallback(() => {
    const vp = viewportRef.current;
    const panner = pannerRef.current;
    if (!vp || !panner) return;
    const svg = panner.querySelector("svg");
    if (!svg) return;

    const cw = vp.clientWidth;
    const ch = vp.clientHeight;
    /** Flex/layout often reports 0×0 for one frame — scaling then overflows once real size appears. */
    if (cw < 8 || ch < 8) return;

    svg.removeAttribute("width");
    svg.removeAttribute("height");

    const vb = svg.viewBox?.baseVal;
    const hasVb = !!(vb && vb.width > 0 && vb.height > 0);

    let w: number;
    let h: number;

    /**
     * Graphviz wraps drawable content in ``g.graph``. Prefer that bbox — the root SVG
     * ``viewBox`` often includes large margins; merging viewBox ∪ bbox (old behaviour)
     * inflated ``w``/``h``, shrinking the fit scale (~20% zoom with empty canvas).
     */
    const tryBBox = (el: SVGGraphicsElement): DOMRect | null => {
      try {
        const b = el.getBBox();
        if (
          Number.isFinite(b.width) &&
          b.width > 1 &&
          Number.isFinite(b.height) &&
          b.height > 1
        ) {
          return b;
        }
      } catch {
        /* detached or not yet laid out */
      }
      return null;
    };

    const graphG = svg.querySelector("g.graph");
    let box: DOMRect | null =
      graphG instanceof SVGGraphicsElement ? tryBBox(graphG) : null;
    if (!box && svg instanceof SVGGraphicsElement) {
      box = tryBBox(svg);
    }

    if (box) {
      w = box.width;
      h = box.height;
    } else if (hasVb && vb) {
      w = vb.width;
      h = vb.height;
    } else {
      w = 800;
      h = 600;
    }

    if (!Number.isFinite(w) || w < 1) w = 1;
    if (!Number.isFinite(h) || h < 1) h = 1;

    if (hasVb && vb && vb.width > 0) {
      svg.setAttribute("width", String(vb.width));
      svg.setAttribute("height", String(vb.height));
    } else {
      svg.setAttribute("width", String(w));
      svg.setAttribute("height", String(h));
    }

    /** Padding inside viewport so the graph does not touch edges (toolbar-safe). */
    const pad = 0.88;
    let s = Math.min((cw * pad) / w, (ch * pad) / h);
    s = Math.max(0.05, Math.min(s, MAX_SCALE));

    /**
     * Center using layout rects (matches wheel-zoom convention). Apply scale first, force a single
     * synchronous layout read, then set ``tx``/``ty`` and commit once — avoids visible multi-step
     * “online” fitting from async RAF / delayed refits.
     */
    panRef.current.scale = s;
    panRef.current.tx = 0;
    panRef.current.ty = 0;
    panner.style.transform = `translate(0px,0px) scale(${s})`;

    void panner.offsetHeight;

    const graphEl = svg.querySelector("g.graph") ?? svg;
    const vr = vp.getBoundingClientRect();
    const gr = graphEl.getBoundingClientRect();
    if (gr.width >= 2 && gr.height >= 2) {
      const gcx = gr.left - vr.left + gr.width / 2;
      const gcy = gr.top - vr.top + gr.height / 2;
      panRef.current.tx = vp.clientWidth / 2 - gcx;
      panRef.current.ty = vp.clientHeight / 2 - gcy;
    }

    applyTransform();
  }, [applyTransform]);

  useEffect(() => {
    const vp = viewportRef.current;
    if (!vp || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      if (resizeFitRafRef.current !== null) return;
      resizeFitRafRef.current = requestAnimationFrame(() => {
        resizeFitRafRef.current = null;
        fitToContainer();
      });
    });
    ro.observe(vp);
    return () => {
      ro.disconnect();
      if (resizeFitRafRef.current !== null) {
        cancelAnimationFrame(resizeFitRafRef.current);
        resizeFitRafRef.current = null;
      }
    };
  }, [fitToContainer]);

  const zoomFromViewportCenter = useCallback(
    (factor: number) => {
      const vp = viewportRef.current;
      if (!vp) return;
      const cx = vp.clientWidth / 2;
      const cy = vp.clientHeight / 2;
      const s0 = panRef.current.scale;
      const s1 = clampUserScale(s0 * factor);
      if (s1 === s0) return;
      panRef.current.tx = cx - (cx - panRef.current.tx) * (s1 / s0);
      panRef.current.ty = cy - (cy - panRef.current.ty) * (s1 / s0);
      panRef.current.scale = s1;
      applyTransform();
    },
    [applyTransform],
  );

  const flushWheelZoom = useCallback(() => {
    wheelRafRef.current = null;
    const vp = viewportRef.current;
    if (!vp) return;
    const dy = Math.max(-120, Math.min(120, wheelAccumRef.current));
    wheelAccumRef.current = 0;
    const factor = Math.exp(-dy * WHEEL_ZOOM_SENSITIVITY);
    const rect = vp.getBoundingClientRect();
    const wx =
      typeof wheelClientRef.current.x === "number"
        ? wheelClientRef.current.x
        : rect.left + rect.width / 2;
    const wy =
      typeof wheelClientRef.current.y === "number"
        ? wheelClientRef.current.y
        : rect.top + rect.height / 2;
    wheelClientRef.current = {};
    const ox = wx - rect.left;
    const oy = wy - rect.top;
    const s0 = panRef.current.scale;
    const s1 = clampUserScale(s0 * factor);
    if (s1 === s0) return;
    panRef.current.tx = ox - (ox - panRef.current.tx) * (s1 / s0);
    panRef.current.ty = oy - (oy - panRef.current.ty) * (s1 / s0);
    panRef.current.scale = s1;
    applyTransform();
  }, [applyTransform]);

  const bindInteractions = useCallback(() => {
    interactAbortRef.current?.abort();
    const ac = new AbortController();
    interactAbortRef.current = ac;
    const vp = viewportRef.current;
    if (!vp) return () => {};
    const sig = ac.signal;

    const onWheel = (evt: WheelEvent) => {
      evt.preventDefault();
      wheelClientRef.current = { x: evt.clientX, y: evt.clientY };
      wheelAccumRef.current += evt.deltaY;
      if (wheelRafRef.current == null) {
        wheelRafRef.current = requestAnimationFrame(() => {
          wheelRafRef.current = null;
          flushWheelZoom();
        });
      }
    };

    const onMouseDown = (evt: MouseEvent) => {
      if (evt.button !== 0) return;
      evt.preventDefault();
      dragRef.current = {
        x: evt.clientX,
        y: evt.clientY,
        tx: panRef.current.tx,
        ty: panRef.current.ty,
      };
      vp.classList.add("erd-panning");
    };

    const onMouseMove = (evt: MouseEvent) => {
      if (!dragRef.current) return;
      panRef.current.tx = dragRef.current.tx + (evt.clientX - dragRef.current.x);
      panRef.current.ty = dragRef.current.ty + (evt.clientY - dragRef.current.y);
      applyTransform();
    };

    const onMouseUp = () => {
      if (dragRef.current) {
        dragRef.current = null;
        vp.classList.remove("erd-panning");
      }
    };

    vp.addEventListener("wheel", onWheel, { passive: false, signal: sig });
    vp.addEventListener("mousedown", onMouseDown, { signal: sig });
    window.addEventListener("mousemove", onMouseMove, { signal: sig });
    window.addEventListener("mouseup", onMouseUp, { signal: sig });

    return () => {
      ac.abort();
    };
  }, [applyTransform, flushWheelZoom]);

  const zoomIn = useCallback(() => zoomFromViewportCenter(1.25), [zoomFromViewportCenter]);
  const zoomOut = useCallback(() => zoomFromViewportCenter(0.8), [zoomFromViewportCenter]);

  return {
    viewportRef,
    pannerRef,
    zoomPct,
    fitToContainer,
    zoomIn,
    zoomOut,
    bindInteractions,
  };
}
