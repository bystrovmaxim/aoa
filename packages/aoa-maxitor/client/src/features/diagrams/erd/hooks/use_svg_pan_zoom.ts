// packages/aoa-maxitor/client/src/features/diagrams/erd/hooks/use_svg_pan_zoom.ts
/**
 * Pan / zoom / wheel zoom for a viewport wrapping an SVG panner (same mechanics as the legacy HTML viewer).
 */

import { useCallback, useRef, useState } from "react";

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
    svg.removeAttribute("width");
    svg.removeAttribute("height");

    const vb = svg.viewBox?.baseVal;
    let w: number;
    let h: number;
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
      } catch {
        w = 800;
        h = 600;
      }
    }
    if (!Number.isFinite(w) || w < 1) w = 1;
    if (!Number.isFinite(h) || h < 1) h = 1;

    if (vb && Number(vb.width) > 0) {
      svg.setAttribute("width", String(vb.width));
      svg.setAttribute("height", String(vb.height));
    } else {
      svg.setAttribute("width", String(w));
      svg.setAttribute("height", String(h));
    }

    const cw = vp.clientWidth || 1;
    const ch = vp.clientHeight || 1;
    let s = Math.min(cw / w, ch / h) * 0.92;
    s = Math.max(0.05, Math.min(s, MAX_SCALE));
    panRef.current.scale = s;
    panRef.current.tx = (cw - w * s) / 2 - bx * s;
    panRef.current.ty = (ch - h * s) / 2 - by * s;
    applyTransform();
  }, [applyTransform]);

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
    applyTransform,
  };
}
