// src/lib/hoverCardsOn.ts
/**
 * Whether cards open at all (spec 043): on at first, and the person's own choice from then on, in this browser. A browser that
 * refuses storage keeps the choice for the life of the tab.
 */
import { useSyncExternalStore } from "react";

const KEY = "maxitor:hoverCards";
const listeners = new Set<() => void>();

function stored(): boolean {
  try {
    return globalThis.localStorage?.getItem(KEY) !== "0";
  } catch {
    return true;
  }
}

let on = stored();

export function setHoverCardsOn(next: boolean): void {
  on = next;
  try {
    globalThis.localStorage?.setItem(KEY, next ? "1" : "0");
  } catch {
    // Nowhere to keep it: it lasts as long as the tab.
  }
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useHoverCardsOn(): boolean {
  return useSyncExternalStore(subscribe, () => on);
}
