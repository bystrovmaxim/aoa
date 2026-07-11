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
/** One wheel chunk (device pixels) applied per animation frame — avoids huge jumps when delta batches. */
const WHEEL_CHUNK_PX = 56;

function clampUserScale(scale: number): number {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
}

function touchDistance(a: Touch, b: Touch): number {
  return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
}

function touchMidpoint(a: Touch, b: Touch, rect: DOMRect): { x: number; y: number } {
  return { x: (a.clientX + b.clientX) / 2 - rect.left, y: (a.clientY + b.clientY) / 2 - rect.top };
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
      b.width < 0.25 ||
      !Number.isFinite(b.height) ||
      b.height < 0.25
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

/** Tight bounds of the whole Graphviz drawing (nodes + splines + labels), viewport-local px. */
function graphGroupBoxInViewport(svg: SVGSVGElement, viewport: HTMLElement): Rect | null {
  const gg = svg.querySelector("g.graph");
  if (!gg) return null;
  const b = gg.getBoundingClientRect();
  const vr = viewport.getBoundingClientRect();
  if (
    !Number.isFinite(b.width) ||
    b.width < 1 ||
    !Number.isFinite(b.height) ||
    b.height < 1
  ) {
    return null;
  }
  return {
    x: b.left - vr.left,
    y: b.top - vr.top,
    width: b.width,
    height: b.height,
  };
}

export type UseSvgPanZoomOptions = {
  /**
   * Pixels subtracted from viewport height when computing fit scale / vertical centering
   * (e.g. floating zoom toolbar over the canvas bottom).
   */
  fitBottomInset?: number;
  /**
   * Uniform margin (pixels) subtracted from usable width/height so titles/cluster labels
   * are not flush against the viewport edge after fit.
   */
  fitMarginPx?: number;
  /**
   * Elements whose union ``getBoundingClientRect`` defines the fitted region.
   * Default: Graphviz node + edge groups. Use-case / cluster-heavy DOT output should also
   * include ``g.cluster`` so subgraph titles and frames participate in the bounds.
   */
  fitBoundsSelector?: string;
  /** Maximum scale used by automatic fit; user zoom still uses MAX_SCALE. */
  fitMaxScale?: number;
};

export function useSvgPanZoom(options?: UseSvgPanZoomOptions) {
  const fitBottomInset = options?.fitBottomInset ?? 0;
  const fitMarginPx = options?.fitMarginPx ?? 0;
  const fitBoundsSelector = options?.fitBoundsSelector ?? "g.graph g.node, g.graph g.edge";
  const fitMaxScale = options?.fitMaxScale ?? MAX_SCALE;
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const pannerRef = useRef<HTMLDivElement | null>(null);
  const panRef = useRef({ scale: 1, tx: 0, ty: 0 });
  const dragRef = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const touchDragRef = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const pinchRef = useRef<{ startDist: number; startScale: number } | null>(null);
  const wheelAccumRef = useRef(0);
  const wheelRafRef = useRef<number | null>(null);
  const wheelFocalRef = useRef<{ ox: number; oy: number } | null>(null);
  const wheelIdleTimeoutRef = useRef<number | null>(null);
  const interactAbortRef = useRef<AbortController | null>(null);
  const resizeFitRafRef = useRef<number | null>(null);
  const hasFittedRef = useRef(false);
  const lastVpSizeRef = useRef({ w: 0, h: 0 });
  const [zoomPct, setZoomPct] = useState(100);

  const applyTransform = useCallback((publishZoom = true) => {
    const panner = pannerRef.current;
    if (!panner) return;
    const { scale, tx, ty } = panRef.current;
    panner.style.transform = `matrix(${scale}, 0, 0, ${scale}, ${tx}, ${ty})`;
    if (publishZoom) setZoomPct(Math.round(scale * 100));
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

    const chFit = Math.max(8, ch - fitBottomInset);
    const availW = Math.max(8, cw - 2 * fitMarginPx);
    const availH = Math.max(8, chFit - 2 * fitMarginPx);

    stripGraphvizBackdropPolygons(svg);

    // Measure real painted SVG content at identity panner transform.
    panRef.current.scale = 1;
    panRef.current.tx = 0;
    panRef.current.ty = 0;
    applyTransform(false);
    void panner.offsetHeight;

    // Prefer union of node + edge rects: ``g.graph`` bounds can balloon from off-canvas spline
    // control points (notably TB back-edges in lifecycle FSMs), shrinking ``s`` too much and
    // leaving huge empty margins. Fall back to ``g.graph`` only if the union is empty.
    let box = unionClientRects(svg.querySelectorAll(fitBoundsSelector), vp);
    if (!box) {
      box = graphGroupBoxInViewport(svg, vp);
    }
    if (!box) {
      const graphEl = svg.querySelector("g.graph") ?? svg;
      box = unionClientRects([graphEl], vp);
    }
    if (!box) return;

    const pad = 0.92;
    let s = Math.min((availW * pad) / box.width, (availH * pad) / box.height);
    s = Math.max(MIN_SCALE, Math.min(s, fitMaxScale));

    panRef.current.scale = s;
    const tx = fitMarginPx + (availW - box.width * s) / 2 - box.x * s;
    const ty = fitMarginPx + (availH - box.height * s) / 2 - box.y * s;
    panRef.current.tx = tx;
    panRef.current.ty = ty;
    applyTransform();
    hasFittedRef.current = true;
  }, [applyTransform, fitBottomInset, fitMarginPx, fitBoundsSelector, fitMaxScale]);

  useEffect(() => {
    const vp = viewportRef.current;
    if (!vp || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      if (resizeFitRafRef.current !== null) return;
      resizeFitRafRef.current = requestAnimationFrame(() => {
        resizeFitRafRef.current = null;
        const w = vp.clientWidth;
        const h = vp.clientHeight;
        const prev = lastVpSizeRef.current;
        const sizeChanged = Math.abs(w - prev.w) > 1 || Math.abs(h - prev.h) > 1;
        if (sizeChanged) {
          lastVpSizeRef.current = { w, h };
        }
        if (!hasFittedRef.current || sizeChanged) {
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

    const rect = vp.getBoundingClientRect();
    const focal = wheelFocalRef.current ?? { ox: rect.width / 2, oy: rect.height / 2 };
    const { ox, oy } = focal;

    const chunk = Math.max(-WHEEL_CHUNK_PX, Math.min(WHEEL_CHUNK_PX, wheelAccumRef.current));
    wheelAccumRef.current -= chunk;

    const s0 = panRef.current.scale;
    const sens = WHEEL_ZOOM_SENSITIVITY / Math.max(1, Math.pow(s0, 0.45));
    const factor = Math.exp(-chunk * sens);
    const s1 = clampUserScale(s0 * factor);
    if (s1 !== s0) {
      panRef.current.tx = ox - (ox - panRef.current.tx) * (s1 / s0);
      panRef.current.ty = oy - (oy - panRef.current.ty) * (s1 / s0);
      panRef.current.scale = s1;
    }

    applyTransform(false);

    if (Math.abs(wheelAccumRef.current) > 0.5) {
      wheelRafRef.current = requestAnimationFrame(() => {
        wheelRafRef.current = null;
        flushWheelZoom();
      });
    } else {
      wheelFocalRef.current = null;
      setZoomPct(Math.round(panRef.current.scale * 100));
    }
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
      vp.classList.add("erd-wheel-zooming");
      if (wheelIdleTimeoutRef.current !== null) {
        window.clearTimeout(wheelIdleTimeoutRef.current);
      }
      wheelIdleTimeoutRef.current = window.setTimeout(() => {
        wheelIdleTimeoutRef.current = null;
        vp.classList.remove("erd-wheel-zooming");
        wheelFocalRef.current = null;
        setZoomPct(Math.round(panRef.current.scale * 100));
      }, 120);

      const r = vp.getBoundingClientRect();
      wheelFocalRef.current = { ox: evt.clientX - r.left, oy: evt.clientY - r.top };
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

    // Single finger pans, two fingers pinch-zoom (and may pan too, tracking the midpoint each
    // frame) — reuses the same focal-point scale math as wheel zoom. touch-action:"none" on the
    // viewport already blocks the browser's native scroll/pinch; preventDefault is defense-in-depth.
    const onTouchStart = (evt: TouchEvent) => {
      if (evt.touches.length === 1) {
        pinchRef.current = null;
        const t = evt.touches[0];
        touchDragRef.current = { x: t.clientX, y: t.clientY, tx: panRef.current.tx, ty: panRef.current.ty };
        vp.classList.add("erd-panning");
      } else if (evt.touches.length === 2) {
        touchDragRef.current = null;
        vp.classList.remove("erd-panning");
        pinchRef.current = {
          startDist: touchDistance(evt.touches[0], evt.touches[1]),
          startScale: panRef.current.scale,
        };
      }
    };

    const onTouchMove = (evt: TouchEvent) => {
      if (evt.touches.length === 2 && pinchRef.current) {
        evt.preventDefault();
        const [t0, t1] = [evt.touches[0], evt.touches[1]];
        const { startDist, startScale } = pinchRef.current;
        if (startDist > 0) {
          const dist = touchDistance(t0, t1);
          const mid = touchMidpoint(t0, t1, vp.getBoundingClientRect());
          const s0 = panRef.current.scale;
          const s1 = clampUserScale(startScale * (dist / startDist));
          if (s1 !== s0) {
            panRef.current.tx = mid.x - (mid.x - panRef.current.tx) * (s1 / s0);
            panRef.current.ty = mid.y - (mid.y - panRef.current.ty) * (s1 / s0);
            panRef.current.scale = s1;
            applyTransform();
          }
        }
      } else if (evt.touches.length === 1 && touchDragRef.current) {
        evt.preventDefault();
        const t = evt.touches[0];
        panRef.current.tx = touchDragRef.current.tx + (t.clientX - touchDragRef.current.x);
        panRef.current.ty = touchDragRef.current.ty + (t.clientY - touchDragRef.current.y);
        applyTransform();
      }
    };

    const onTouchEnd = (evt: TouchEvent) => {
      if (evt.touches.length === 0) {
        touchDragRef.current = null;
        pinchRef.current = null;
        vp.classList.remove("erd-panning");
        setZoomPct(Math.round(panRef.current.scale * 100));
      } else if (evt.touches.length === 1) {
        // Dropped from two touches to one — restart single-finger pan from here, no jump.
        pinchRef.current = null;
        const t = evt.touches[0];
        touchDragRef.current = { x: t.clientX, y: t.clientY, tx: panRef.current.tx, ty: panRef.current.ty };
        vp.classList.add("erd-panning");
      }
    };

    vp.addEventListener("wheel", onWheel, { passive: false, signal: sig });
    vp.addEventListener("mousedown", onMouseDown, { signal: sig });
    window.addEventListener("mousemove", onMouseMove, { signal: sig });
    window.addEventListener("mouseup", onMouseUp, { signal: sig });
    vp.addEventListener("touchstart", onTouchStart, { passive: false, signal: sig });
    vp.addEventListener("touchmove", onTouchMove, { passive: false, signal: sig });
    vp.addEventListener("touchend", onTouchEnd, { signal: sig });
    vp.addEventListener("touchcancel", onTouchEnd, { signal: sig });

    return () => {
      ac.abort();
      if (wheelIdleTimeoutRef.current !== null) {
        window.clearTimeout(wheelIdleTimeoutRef.current);
        wheelIdleTimeoutRef.current = null;
      }
    };
  }, [applyTransform, flushWheelZoom]);

  const zoomIn = useCallback(() => zoomFromViewportCenter(1.25), [zoomFromViewportCenter]);
  const zoomOut = useCallback(() => zoomFromViewportCenter(0.8), [zoomFromViewportCenter]);

  const resetFitFlag = useCallback(() => {
    hasFittedRef.current = false;
    panRef.current = { scale: 1, tx: 0, ty: 0 };
    applyTransform(false);
    setZoomPct(100);
  }, [applyTransform]);

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
