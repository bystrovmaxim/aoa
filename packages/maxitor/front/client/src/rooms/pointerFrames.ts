// src/rooms/pointerFrames.ts
/**
 * Pointer frames — where a pointer over a panel stands, in the panel's own terms (spec 038).
 *
 * A panel that may sit elsewhere on another person's screen — the version picker, opened under a button that moves
 * with the window — marks itself ``data-pointer-frame="<name>"``. A pointer over it is sent as the offset from that
 * element's top-left corner, plus its scroll, so over a scrolled track it names the same version however far each
 * person scrolled. The receiver finds its own element of that name and puts the pointer at the same offset; without
 * one the pointer is not drawn.
 */
import type { Point } from "@/rooms/coordinates";

/** The attribute that names a panel's frame. */
export const POINTER_FRAME_ATTR = "data-pointer-frame";

/** A frame's name: short, lowercase, as the server accepts it. */
const FRAME_NAME = /^[a-z][a-z0-9-]{0,31}$/;

/** ``target``'s nearest named frame and the client point in it, or ``null`` outside every frame. */
export function inFrame(target: EventTarget | null, client: Point): (Point & { frame: string }) | null {
  const element = target instanceof Element ? target.closest<HTMLElement>(`[${POINTER_FRAME_ATTR}]`) : null;
  const frame = element?.getAttribute(POINTER_FRAME_ATTR) ?? "";
  if (!element || !FRAME_NAME.test(frame)) return null;
  const box = element.getBoundingClientRect();
  return { x: client.x - box.left + element.scrollLeft, y: client.y - box.top + element.scrollTop, frame };
}

/** Where a point in frame ``frame`` stands on this screen, or ``null`` while no element of that name is shown. */
export function clientInFrame(frame: string, point: Point): Point | null {
  const element = [...document.querySelectorAll<HTMLElement>(`[${POINTER_FRAME_ATTR}]`)].find((each) => each.getAttribute(POINTER_FRAME_ATTR) === frame);
  if (!element) return null;
  const box = element.getBoundingClientRect();
  return { x: box.left + point.x - element.scrollLeft, y: box.top + point.y - element.scrollTop };
}
