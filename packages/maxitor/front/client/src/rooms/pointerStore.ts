// src/rooms/pointerStore.ts
/**
 * Other participants' pointers and screens, as they arrive.
 *
 * They change up to twenty times a second per person, so they live outside React state: the pointer
 * layer subscribes and redraws on the next animation frame. Only the newest position of each person
 * is kept (FR-043).
 */
import type { Side } from "@/lib/half";
import type { DiagramViewport, Point } from "@/rooms/coordinates";

/**
 * ``frame: "screen"`` — over a panel or the left panel: the position is in screen pixels from the diagram's top-left
 * corner, where those panels stand, not in the diagram's coordinates. Any other name — over a panel that names its
 * frame, as the version picker does — is that panel's own frame (``pointerFrames``, spec 038).
 */
export type PointerFrame = { frame?: string };

export type RemotePointer = Point & PointerFrame & { kind: "mouse" | "touch"; at: number; half?: Side };

/** A click someone made, where and when: it shows as a ripple for a moment (spec 038). */
export type RemoteClick = Point & PointerFrame & { at: number; half?: Side };

const pointers = new Map<string, RemotePointer>();
const clicks = new Map<string, RemoteClick>();
const viewports = new Map<string, DiagramViewport>();
/**
 * Each participant's screen in pixels, as they last told it. Unlike what their screen shows, it does not depend on
 * the page, so it is kept when they or this tab change page: a follower fits a new page to it at once (spec 038).
 */
const screens = new Map<string, { w: number; h: number }>();
const listeners = new Set<() => void>();

function changed(): void {
  for (const listener of listeners) listener();
}

/** Record a participant's pointer. */
export function putPointer(participant: string, pointer: RemotePointer): void {
  pointers.set(participant, pointer);
  changed();
}

/** Record what a participant's screen shows. */
export function putViewport(participant: string, viewport: DiagramViewport, half?: Side): void {
  // A's screen stands apart: B's is what a page with one diagram reports, and following reads it the same way.
  viewports.set(half === "a" ? `${participant}|a` : participant, viewport);
  if (viewport.pw && viewport.ph) screens.set(participant, { w: viewport.pw, h: viewport.ph });
  changed();
}

/** Record a participant's click. */
export function putClick(participant: string, click: RemoteClick): void {
  clicks.set(participant, click);
  changed();
}

/** Every participant's last click. */
export function currentClicks(): ReadonlyMap<string, RemoteClick> {
  return clicks;
}

/** Forget a participant's pointer: they left, or went to another page. */
export function dropPointer(participant: string): void {
  if (pointers.delete(participant)) changed();
  viewports.delete(participant);
  clicks.delete(participant);
}

/** Forget everyone: the tab left the room or changed page. */
export function clearPointers(): void {
  pointers.clear();
  viewports.clear();
  clicks.clear();
  changed();
}

/** Every pointer known now. */
export function currentPointers(): ReadonlyMap<string, RemotePointer> {
  return pointers;
}

/** ``participant``'s screen in pixels, when they ever told it — kept across pages. */
export function screenOfParticipant(participant: string): { w: number; h: number } | undefined {
  return screens.get(participant);
}

/** What ``participant``'s screen shows, when known. */
export function viewportOfHalfA(participant: string): DiagramViewport | undefined {
  return viewports.get(`${participant}|a`);
}

/** What a participant's screen shows. */
export function viewportOfParticipant(participant: string): DiagramViewport | undefined {
  return viewports.get(participant);
}

/** Subscribe to every change of the pointers; returns the unsubscribe. */
export function subscribePointers(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
