// src/rooms/pointerStore.ts
/**
 * Other participants' pointers and screens, as they arrive.
 *
 * They change up to twenty times a second per person, so they live outside React state: the pointer
 * layer subscribes and redraws on the next animation frame. Only the newest position of each person
 * is kept (FR-043).
 */
import type { DiagramViewport, Point } from "@/rooms/coordinates";

/**
 * ``frame: "screen"`` — over a panel, the version picker or the left panel: the position is in screen pixels from the
 * diagram's top-left corner, where those panels stand, not in the diagram's coordinates (spec 038).
 */
export type PointerFrame = { frame?: "screen" };

export type RemotePointer = Point & PointerFrame & { kind: "mouse" | "touch"; at: number };

/** A click someone made, where and when: it shows as a ripple for a moment (spec 038). */
export type RemoteClick = Point & PointerFrame & { at: number };

const pointers = new Map<string, RemotePointer>();
const clicks = new Map<string, RemoteClick>();
const viewports = new Map<string, DiagramViewport>();
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
export function putViewport(participant: string, viewport: DiagramViewport): void {
  viewports.set(participant, viewport);
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

/** What ``participant``'s screen shows, when known. */
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
