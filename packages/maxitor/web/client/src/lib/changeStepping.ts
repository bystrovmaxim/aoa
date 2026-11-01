// src/lib/changeStepping.ts
/**
 * The steps through a comparison's changes (spec 040, FR-025b, FR-025e): a diagram that marks a comparison says what
 * its changes are and where it stands, and the control beside the version button reads that and asks it to go to one.
 * ``null`` while no diagram steps.
 */
import { useSyncExternalStore } from "react";
import type { MapMark } from "@/api/map";

/** One change as the list names it. */
export type ChangeEntry = { key: string; title: string; detail: string; status: MapMark; group: string };

/** What a diagram offers the control. */
export type ChangeStepping = {
  entries: readonly ChangeEntry[];
  position: number | null;
  /** Whether the change it stands on has its card open. */
  card: boolean;
  go: (position: number) => void;
  /** Show what a followed person stands on, moving nothing: following moves the view. */
  mirror: (position: number | null, card: boolean) => void;
};

/** One row of the list: a group's name, or a change at its place in the steps. */
export type ChangeLine = { group: string } | { entry: ChangeEntry; position: number };

/** The list's rows: each group's name above its changes, in the order of the steps. */
export function changeLines(entries: readonly ChangeEntry[]): ChangeLine[] {
  const lines: ChangeLine[] = [];
  entries.forEach((entry, position) => {
    if (position === 0 || entries[position - 1].group !== entry.group) lines.push({ group: entry.group });
    lines.push({ entry, position });
  });
  return lines;
}

let current: ChangeStepping | null = null;
const listeners = new Set<() => void>();

/** Say what the diagram on screen steps through, or ``null`` when it does not step. */
export function setChangeStepping(next: ChangeStepping | null): void {
  current = next;
  for (const listener of listeners) listener();
}

/** What the diagram on screen steps through, followed as it moves. */
export function useChangeStepping(): ChangeStepping | null {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => current,
  );
}
