// src/lib/smallPointsShown.ts
/**
 * Whether the track shows the versions that did not change the graph (spec 051): shown at first, and the person's own
 * choice from then on, in this browser. It is never part of an address or a room. A browser that refuses storage keeps
 * the choice for the life of the tab.
 */
import { useSyncExternalStore } from "react";

const KEY = "maxitor:smallPoints";
const listeners = new Set<() => void>();

function stored(): boolean {
  try {
    return globalThis.localStorage?.getItem(KEY) !== "0";
  } catch {
    return true;
  }
}

let shown = stored();

/** Show or hide the points that did not change the graph, for this viewer. */
export function setSmallPointsShown(next: boolean): void {
  shown = next;
  try {
    globalThis.localStorage?.setItem(KEY, next ? "1" : "0");
  } catch {
    // Storage refused: the choice lasts as long as the tab.
  }
  listeners.forEach((listener) => listener());
}

/** The viewer's choice, following changes. */
export function useSmallPointsShown(): boolean {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    () => shown,
  );
}
