// src/components/diagrams/ErdViewer/hooks/useSvgPanZoom.ts
/**
 * Minimal pan / zoom / fit for Graphviz SVG.
 *
 * Keep transform imperative on the panner element. React only renders SVG markup; it does not own
 * the transform. Fit is measured at identity transform in screen pixels, then applied as a single
 * CSS matrix ``matrix(s, 0, 0, s, tx, ty)``.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { WHEEL_CHUNK_PX, WHEEL_ZOOM_SENSITIVITY, isZoomWheel, wheelPan } from "@/lib/wheelGesture";
import { followedScreen } from "@/rooms/follow";

const MIN_SCALE = 0.005;
const MAX_SCALE = 2.5;

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
   * Pixels kept free at the viewport's left when fitting, for a panel over the canvas; ignored on a narrow screen,
   * where the panel folds into a pill.
   */
  fitLeftInset?: number;
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
  /**
   * Fit the SVG's own box — Graphviz's bounding box, labels included by its own estimate — instead of the drawn
   * elements. Text is measured by each browser a little differently, so two screens fitting the elements of one
   * drawing differ by a few pixels and a follower glides them after the new picture; the box is the same everywhere
   * (spec 038). For drawings whose bounding box hugs the content, as a use case's does.
   */
  fitToViewBox?: boolean;
};

/** Below this width a filter panel is a pill and needs no room beside the drawing. */
const MIN_WIDTH_FOR_LEFT_INSET = 600;

/** How long after the last move the picture stops being a moving layer. */
const MOVING_HINT_MS = 200;

export function useSvgPanZoom(options?: UseSvgPanZoomOptions) {
  const fitBottomInset = options?.fitBottomInset ?? 0;
  const fitLeftInset = options?.fitLeftInset ?? 0;
  const fitMarginPx = options?.fitMarginPx ?? 0;
  const fitBoundsSelector = options?.fitBoundsSelector ?? "g.graph g.node, g.graph g.edge";
  const fitMaxScale = options?.fitMaxScale ?? MAX_SCALE;
  const fitToViewBox = options?.fitToViewBox ?? false;
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const pannerRef = useRef<HTMLDivElement | null>(null);
  const panRef = useRef({ scale: 1, tx: 0, ty: 0 });
  const movingTimerRef = useRef(0);
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
  /** Whether the picture has been fitted once; a view placed before that would be undone by the fit. */
  const [fitted, setFitted] = useState(false);
  /** Counts fits: a view placed from outside (going to someone) must be placed again after each. */
  const [fitCount, setFitCount] = useState(0);
  /** Told after every pan, zoom and fit, so overlays drawn in diagram coordinates follow the picture. */
  const transformListenersRef = useRef(new Set<() => void>());

  /** Put the transform on the panner; ``announce`` false for a step nobody may see or hear of, as fitting measures. */
  const applyTransform = useCallback((publishZoom = true, announce = true) => {
    const panner = pannerRef.current;
    if (!panner) return;
    const { scale, tx, ty } = panRef.current;
    panner.style.transform = `matrix(${scale}, 0, 0, ${scale}, ${tx}, ${ty})`;
    // While the picture moves frame after frame — a drag, a follower's glide — it is one layer the browser moves as it
    // is: Safari otherwise paints the whole drawing again on every frame and the move comes in jumps. A moment after
    // it stops, the hint goes, so the drawing is painted sharp at its new zoom (spec 038).
    panner.style.willChange = "transform";
    window.clearTimeout(movingTimerRef.current);
    movingTimerRef.current = window.setTimeout(() => {
      if (pannerRef.current) pannerRef.current.style.willChange = "";
    }, MOVING_HINT_MS);
    if (publishZoom) setZoomPct(Math.round(scale * 100));
    if (!announce) return;
    for (const listener of transformListenersRef.current) listener();
  }, []);

  /** Subscribe to every change of the transform; returns the unsubscribe. */
  const onTransform = useCallback((listener: () => void) => {
    transformListenersRef.current.add(listener);
    return () => {
      transformListenersRef.current.delete(listener);
    };
  }, []);

  /** Pan so the client point ``(x, y)`` sits at the centre of the viewport; the zoom stays. */
  const centreOnClient = useCallback(
    (x: number, y: number) => {
      const vp = viewportRef.current;
      if (!vp) return;
      const rect = vp.getBoundingClientRect();
      panRef.current.tx += rect.left + rect.width / 2 - x;
      panRef.current.ty += rect.top + rect.height / 2 - y;
      applyTransform();
    },
    [applyTransform],
  );

  /** The current zoom factor. */
  const getScale = useCallback(() => panRef.current.scale, []);

  /** Zoom to ``scale`` about the viewport's centre. */
  const setScale = useCallback(
    (scale: number) => {
      const vp = viewportRef.current;
      if (!vp) return;
      const cx = vp.clientWidth / 2;
      const cy = vp.clientHeight / 2;
      const s0 = panRef.current.scale;
      const s1 = clampUserScale(scale);
      panRef.current.tx = cx - (cx - panRef.current.tx) * (s1 / s0);
      panRef.current.ty = cy - (cy - panRef.current.ty) * (s1 / s0);
      panRef.current.scale = s1;
      applyTransform();
    },
    [applyTransform],
  );

  const fitToContainer = useCallback(() => {
    const vp = viewportRef.current;
    const panner = pannerRef.current;
    if (!vp || !panner) return;
    const svg = panner.querySelector("svg");
    if (!svg) return;

    // Following, a drawing is fitted to the followed person's screen: their very view, at once (spec 038).
    const screen = followedScreen();
    const cw = screen?.w ?? vp.clientWidth;
    const ch = screen?.h ?? vp.clientHeight;
    if (cw < 8 || ch < 8) return;

    const chFit = Math.max(8, ch - fitBottomInset);
    const leftInset = cw >= MIN_WIDTH_FOR_LEFT_INSET ? fitLeftInset : 0;
    const availW = Math.max(8, cw - leftInset - 2 * fitMarginPx);
    const availH = Math.max(8, chFit - 2 * fitMarginPx);

    stripGraphvizBackdropPolygons(svg);

    // Measure real painted SVG content at identity panner transform. Nobody hears of it — a room would send it as this
    // screen's view and a follower would glide to it and back (spec 038) — and the measurement that fails puts the
    // transform it found back.
    const before = { ...panRef.current };
    panRef.current.scale = 1;
    panRef.current.tx = 0;
    panRef.current.ty = 0;
    applyTransform(false, false);
    void panner.offsetHeight;

    // Prefer union of node + edge rects: ``g.graph`` bounds can balloon from off-canvas spline
    // control points (notably TB back-edges in lifecycle FSMs), shrinking ``s`` too much and
    // leaving huge empty margins. Fall back to ``g.graph`` only if the union is empty.
    let box = fitToViewBox ? unionClientRects([svg], vp) : unionClientRects(svg.querySelectorAll(fitBoundsSelector), vp);
    if (!box) {
      box = graphGroupBoxInViewport(svg, vp);
    }
    if (!box) {
      const graphEl = svg.querySelector("g.graph") ?? svg;
      box = unionClientRects([graphEl], vp);
    }
    if (!box) {
      panRef.current = before;
      applyTransform(false, false);
      return;
    }

    const pad = 0.92;
    let s = Math.min((availW * pad) / box.width, (availH * pad) / box.height);
    s = Math.max(MIN_SCALE, Math.min(s, fitMaxScale));

    panRef.current.scale = s;
    const tx = leftInset + fitMarginPx + (availW - box.width * s) / 2 - box.x * s;
    const ty = fitMarginPx + (availH - box.height * s) / 2 - box.y * s;
    panRef.current.tx = tx;
    panRef.current.ty = ty;
    applyTransform();
    hasFittedRef.current = true;
    setFitted(true);
    setFitCount((count) => count + 1);
  }, [applyTransform, fitBottomInset, fitLeftInset, fitMarginPx, fitBoundsSelector, fitMaxScale, fitToViewBox]);

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
      // A two-finger swipe or a plain wheel moves the picture; a pinch or Ctrl / ⌘ + wheel zooms it.
      if (!isZoomWheel(evt)) {
        const { dx, dy } = wheelPan(evt, vp.clientHeight);
        panRef.current.tx -= dx;
        panRef.current.ty -= dy;
        applyTransform(false);
        return;
      }
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
      // ``mouseup`` no longer reaches this binding: a drag it held must not stay stuck to the pointer.
      dragRef.current = null;
      vp.classList.remove("erd-panning");
      if (wheelIdleTimeoutRef.current !== null) {
        window.clearTimeout(wheelIdleTimeoutRef.current);
        wheelIdleTimeoutRef.current = null;
      }
    };
  }, [applyTransform, flushWheelZoom]);

  const zoomIn = useCallback(() => zoomFromViewportCenter(1.25), [zoomFromViewportCenter]);
  const zoomOut = useCallback(() => zoomFromViewportCenter(0.8), [zoomFromViewportCenter]);

  /**
   * Ask for a fit of the next drawing placed. The view on screen stays as it is until then: resetting it here showed the
   * old drawing at 100 % for the moment the new one took to come (spec 038).
   */
  const resetFitFlag = useCallback(() => {
    hasFittedRef.current = false;
    setFitted(false);
  }, []);

  /** Whether the drawing placed next is to be fitted. */
  const needsFit = useCallback(() => !hasFittedRef.current, []);

  return {
    viewportRef,
    pannerRef,
    zoomPct,
    fitToContainer: fitToContainerPublic,
    zoomIn,
    zoomOut,
    bindInteractions,
    resetFitFlag,
    needsFit,
    onTransform,
    centreOnClient,
    getScale,
    setScale,
    fitted,
    fitCount,
  };
}
