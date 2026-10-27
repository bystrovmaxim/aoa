// src/lib/wheelGesture.ts
/**
 * What a wheel event over a diagram means, the way design tools read it (spec 029, FR-053): a
 * trackpad's two-finger swipe or a mouse wheel moves the picture; a pinch or a wheel with Ctrl / ⌘
 * zooms it. Browsers report a trackpad pinch as a wheel event with ``ctrlKey`` set, so the pinch and
 * the swipe are told apart without guessing which device sent them.
 */

/** Pixels per line when a browser counts a mouse wheel in lines (Firefox does). */
const LINE_PX = 16;

/** True when the wheel event zooms: a pinch on a trackpad, or the wheel with Ctrl or ⌘ held. */
export function isZoomWheel(event: Pick<WheelEvent, "ctrlKey" | "metaKey">): boolean {
  return event.ctrlKey || event.metaKey;
}

/**
 * How far a moving wheel event moves the view, in screen pixels: ``dx`` right, ``dy`` down. A wheel
 * counted in lines or pages is turned into pixels; Shift with a vertical wheel moves sideways, for a
 * mouse that has no horizontal wheel and a browser that does not turn it for us.
 */
export function wheelPan(
  event: Pick<WheelEvent, "deltaX" | "deltaY" | "deltaMode" | "shiftKey">,
  pagePx: number,
): { dx: number; dy: number } {
  const unit = event.deltaMode === 1 ? LINE_PX : event.deltaMode === 2 ? pagePx : 1;
  const dx = event.deltaX * unit;
  const dy = event.deltaY * unit;
  return event.shiftKey && dx === 0 ? { dx: dy, dy: 0 } : { dx, dy };
}
