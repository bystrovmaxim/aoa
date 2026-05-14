// src/components/diagrams/ErdViewer/hooks/useSvgPanZoom.ts
/**
 * Minimal pan / zoom / fit for Graphviz SVG.
 *
 * Keep transform imperative on the panner element. React only renders SVG markup; it does not own
 * the transform. Fit is measured at identity transform in screen pixels, then applied as a single
 * CSS matrix ``matrix(s, 0, 0, s, tx, ty)``.
 */

import { useCallback, useEffect, useRef, useState } from "react";

const MIN_SCALE = 0.005;
const MAX_SCALE = 2.5;
const WHEEL_ZOOM_SENSITIVITY = 0.0045;

function clampUserScale(scale: number): number {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
}

function stripGraphvizBackdropPolygons(svg: SVGSVGElement): void {
  const gg = svg.querySelector("g.graph");
  if (!gg) return;
  const vb = svg.viewBox?.baseVal;
  const vbArea =
    vb && Number.isFinite(vb.width) && Number.isFinite(vb.height) && vb.width > 0 && vb.height > 0
      ? Math.abs(vb.width * vb.height)
      : 0;

  const toRemove: SVGPolygonElement[] = [];
  for (const child of gg.children) {
    if (child.tagName.toLowerCase() !== "polygon") continue;
    const poly = child as SVGPolygonElement;
    const fill = String(poly.getAttribute("fill") || "").toLowerCase().trim();
    const knownBackdrop =
      fill === "#f8fafc" ||
      fill === "#f4f5f7" ||
      fill === "#ffffff" ||
      fill === "#fff" ||
      fill === "white" ||
      fill === "lightgray" ||
      fill === "lightgrey" ||
      fill === "transparent";

    let huge = false;
    if (vbArea > 0) {
      try {
        const b = poly.getBBox();
        const a = Math.abs(b.width * b.height);
        if (Number.isFinite(a) && a > vbArea * 0.18) huge = true;
      } catch {
        /* skip */
      }
    }

    if (knownBackdrop || huge) toRemove.push(poly);
  }
  for (const p of toRemove) p.remove();
}

type Rect = { x: number; y: number; width: number; height: number };

function unionClientRects(elements: Iterable<Element>, viewport: HTMLElement): Rect | null {
  const vr = viewport.getBoundingClientRect();
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const el of elements) {
    const b = el.getBoundingClientRect();
    if (
      !Number.isFinite(b.width) ||
      b.width < 1 ||
      !Number.isFinite(b.height) ||
      b.height < 1
    ) {
      continue;
    }
    minX = Math.min(minX, b.left - vr.left);
    minY = Math.min(minY, b.top - vr.top);
    maxX = Math.max(maxX, b.right - vr.left);
    maxY = Math.max(maxY, b.bottom - vr.top);
  }
  if (!Number.isFinite(minX) || !Number.isFinite(minY)) return null;
  const w = maxX - minX;
  const h = maxY - minY;
  if (w < 2 || h < 2) return null;
  return { x: minX, y: minY, width: w, height: h };
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
  const hasFittedRef = useRef(false);
  const [zoomPct, setZoomPct] = useState(100);

  const applyTransform = useCallback(() => {
    const panner = pannerRef.current;
    if (!panner) return;
    const { scale, tx, ty } = panRef.current;
    panner.style.transform = `matrix(${scale}, 0, 0, ${scale}, ${tx}, ${ty})`;
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
    if (cw < 8 || ch < 8) return;

    stripGraphvizBackdropPolygons(svg);

    // Measure real painted SVG content at identity panner transform.
    panRef.current.scale = 1;
    panRef.current.tx = 0;
    panRef.current.ty = 0;
    applyTransform();
    void panner.offsetHeight;

    let box = unionClientRects(svg.querySelectorAll("g.graph g.node"), vp);
    if (!box) {
      const graphEl = svg.querySelector("g.graph") ?? svg;
      box = unionClientRects([graphEl], vp);
    }
    if (!box) return;

    const pad = 0.88;
    let s = Math.min((cw * pad) / box.width, (ch * pad) / box.height);
    s = Math.max(MIN_SCALE, Math.min(s, MAX_SCALE));

    panRef.current.scale = s;
    const tx = (cw - box.width * s) / 2 - box.x * s;
    const ty = (ch - box.height * s) / 2 - box.y * s;
    panRef.current.tx = tx;
    panRef.current.ty = ty;
    applyTransform();
  }, [applyTransform]);

  useEffect(() => {
    const vp = viewportRef.current;
    if (!vp || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      if (resizeFitRafRef.current !== null) return;
      resizeFitRafRef.current = requestAnimationFrame(() => {
        resizeFitRafRef.current = null;
        if (!hasFittedRef.current) {
          fitToContainer();
        }
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

  const fitToContainerPublic = useCallback(() => {
    fitToContainer();
    hasFittedRef.current = true;
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

  const resetFitFlag = useCallback(() => {
    hasFittedRef.current = false;
  }, []);

  return {
    viewportRef,
    pannerRef,
    zoomPct,
    fitToContainer: fitToContainerPublic,
    zoomIn,
    zoomOut,
    bindInteractions,
    resetFitFlag,
  };
}
