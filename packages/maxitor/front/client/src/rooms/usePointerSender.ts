// src/rooms/usePointerSender.ts
/**
 * Send this tab's pointer and screen to the room, in diagram coordinates (FR-040, FR-043).
 *
 * Pointer Events anywhere on the page give mouse and touch alike — over the filter panel, the version picker or the
 * left panel too, mapped into the diagram's coordinates —, a click as well; a pan or zoom gives the screen (spec 038).
 * Nothing goes out from a hidden tab, while pointers are off on this page, or outside a room.
 */
import { useEffect } from "react";
import { surfaceOfHalf, type DiagramSurface } from "@/rooms/diagramSurface";
import { viewportOf, type DiagramViewport, type Point } from "@/rooms/coordinates";
import { inFrame } from "@/rooms/pointerFrames";
import type { ClientMessage } from "@/rooms/protocol";
import { POINTER_RATE, VIEWPORT_RATE, throttle } from "@/rooms/throttle";

type Position = Point & { frame?: string; half?: "a" | "b" };
type PointerMessage = Position & { kind: "mouse" | "touch" };

const samePointer = (a: PointerMessage, b: PointerMessage) => a.x === b.x && a.y === b.y && a.kind === b.kind && a.frame === b.frame && a.half === b.half;
const sameViewport = (a: DiagramViewport, b: DiagramViewport) => a.cx === b.cx && a.cy === b.cy && a.w === b.w && a.h === b.h && a.pw === b.pw && a.ph === b.ph;

/** Start sending for ``surface``; returns the call that stops. */
export function startPointerSender(surface: DiagramSurface, send: (message: ClientMessage) => void): () => void {
  const sideOfScreen = surfaceOfHalf("b") === surface ? "b" : undefined;
  const pointer = throttle<PointerMessage>(POINTER_RATE, (p) => send({ type: "pointer", ...p }), samePointer);
  const viewport = throttle<DiagramViewport>(VIEWPORT_RATE, (v) => send({ type: "viewport", ...v }), sameViewport);
  const hidden = () => document.visibilityState === "hidden";

  // Over the diagram a position is the diagram's own; over a panel that names its frame — the version picker — it is
  // that panel's; over anything else — a panel fixed to the screen — it is the screen's, from the diagram's top-left
  // corner, so it lands on the same control for someone whose window differs.
  const positionOf = (event: PointerEvent): Position | null => {
    // In Side by side each half has its own coordinates, and the position says which (spec 044).
    const side = event.target instanceof Element ? event.target.closest("[data-half]")?.getAttribute("data-half") : null;
    const half = side === "a" || side === "b" ? surfaceOfHalf(side) : null;
    if (half && (side === "a" || side === "b") && event.target instanceof Node && half.element.contains(event.target)) {
      const point = half.toDiagram({ x: event.clientX, y: event.clientY });
      return point ? { ...point, half: side } : null;
    }
    if (event.target instanceof Node && surface.element.contains(event.target)) return surface.toDiagram({ x: event.clientX, y: event.clientY });
    const framed = inFrame(event.target, { x: event.clientX, y: event.clientY });
    if (framed) return framed;
    const rect = surface.element.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top, frame: "screen" };
  };
  const onPointer = (event: PointerEvent) => {
    if (hidden()) return;
    const position = positionOf(event);
    if (position) pointer.push({ ...position, kind: event.pointerType === "touch" ? "touch" : "mouse" });
  };
  // A click goes out at once, unthrottled: the ripple shows where and when it happened.
  const onPress = (event: PointerEvent) => {
    onPointer(event);
    if (hidden() || event.pointerType === "touch" || event.button !== 0) return;
    const position = positionOf(event);
    if (position) send({ type: "click", ...position });
  };
  const onTransform = () => {
    if (hidden()) return;
    const rect = surface.element.getBoundingClientRect();
    const v = viewportOf(rect, surface.toDiagram);
    // With the screen's size in pixels a follower takes the same zoom and the same top-left corner (spec 038).
    if (v) viewport.push({ ...v, pw: rect.width, ph: rect.height, ...(sideOfScreen && { half: sideOfScreen }) });
  };

  // The whole page, captured before a panel or a picker can stop the event.
  window.addEventListener("pointermove", onPointer, { passive: true, capture: true });
  window.addEventListener("pointerdown", onPress, { passive: true, capture: true });
  const unsubscribe = surface.subscribe(onTransform);
  onTransform();
  return () => {
    window.removeEventListener("pointermove", onPointer, { capture: true });
    window.removeEventListener("pointerdown", onPress, { capture: true });
    unsubscribe();
    pointer.cancel();
    viewport.cancel();
  };
}

/** Send while ``enabled`` and a diagram is on screen. */
/** Send half A's screen: B's goes with the pointer sender, and a follower's half A follows this (spec 044). */
export function useHalfScreenSender(surface: DiagramSurface | null, send: (message: ClientMessage) => void, enabled: boolean): void {
  useEffect(() => {
    if (!surface || !enabled) return undefined;
    const viewport = throttle<DiagramViewport>(VIEWPORT_RATE, (v) => send({ type: "viewport", ...v, half: "a" }), sameViewport);
    const report = () => {
      const v = viewportOf(surface.element.getBoundingClientRect(), surface.toDiagram);
      if (v && document.visibilityState !== "hidden") viewport.push(v);
    };
    const stop = surface.subscribe(report);
    report();
    return () => {
      stop();
      viewport.cancel();
    };
  }, [surface, send, enabled]);
}

export function usePointerSender(surface: DiagramSurface | null, send: (message: ClientMessage) => void, enabled: boolean): void {
  useEffect(() => {
    if (!surface || !enabled) return undefined;
    return startPointerSender(surface, send);
  }, [surface, send, enabled]);
}
