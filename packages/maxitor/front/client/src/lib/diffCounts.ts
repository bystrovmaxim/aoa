// src/lib/diffCounts.ts
/**
 * The counts of the diagram on screen in Diff (spec 038, FR-025): the ERD writes them once it has drawn, the version
 * button in the top row reads them. ``null`` while no diagram counts — one version, or a diagram that does not yet
 * mark a comparison. Beside them, the two versions' names, which a changed element's card says.
 */
import { useSyncExternalStore } from "react";
import type { DiagramCounts } from "@/lib/erdDiff";

let current: DiagramCounts | null = null;
const listeners = new Set<() => void>();

/** Say what the diagram on screen counts, or ``null`` when it counts nothing. */
export function setDiffCounts(counts: DiagramCounts | null): void {
  const same = counts === current || (counts && current && counts.added === current.added && counts.removed === current.removed && counts.changed === current.changed);
  if (same) return;
  current = counts;
  for (const listener of listeners) listener();
}

/** The counts of the diagram on screen, followed as they change. */
export function useDiffCounts(): DiagramCounts | null {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => current,
  );
}

let names: { a: string; b: string } | null = null;
const nameListeners = new Set<() => void>();

/** Say the names of the two versions compared — what a card says an element was added or removed in. */
export function setDiffNames(next: { a: string; b: string } | null): void {
  if (next?.a === names?.a && next?.b === names?.b) return;
  names = next;
  for (const listener of nameListeners) listener();
}

/** The names of the two versions compared, or ``null`` outside Diff. */
export function useDiffNames(): { a: string; b: string } | null {
  return useSyncExternalStore(
    (listener) => {
      nameListeners.add(listener);
      return () => nameListeners.delete(listener);
    },
    () => names,
  );
}
