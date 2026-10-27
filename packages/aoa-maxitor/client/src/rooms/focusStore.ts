// src/rooms/focusStore.ts
/**
 * What a person is looking at — the hovered element, the tooltip, the selection, the open panels — and
 * what the person they follow is looking at (spec 029, FR-010 … FR-013).
 *
 * Kept outside React, like the pointers: hover changes many times a second. Viewers and panels report
 * their own state here from real mouse and click events; while this tab follows someone, they show the
 * followed person's state instead and ignore the follower's own mouse. What this tab sends as its
 * focus is what it shows: its own state, or — while following — the followed person's, so a chain of
 * followers sees the same thing.
 */
import { useEffect, useRef, useSyncExternalStore } from "react";

/** A diagram element, named by the id every viewer already uses for it. */
export type ElementRef = { kind: "node" | "row" | "edge" | "table"; id: string };

/**
 * The open panels: the open left-panel branches; the filter panel — closed (``null``), open with no
 * section (``"open"``) or open on a section; and whether the legend is expanded.
 */
export type Panels = { sidebar: string[]; filter: "open" | "domains" | "kinds" | null; legend: boolean };

export type FocusState = {
  page: string;
  hover: ElementRef | null;
  tooltip: ElementRef | null;
  selection: ElementRef | null;
  panels: Panels;
};

type OwnFocus = Omit<FocusState, "page">;

const EMPTY: OwnFocus = { hover: null, tooltip: null, selection: null, panels: { sidebar: [], filter: null, legend: false } };

let own: OwnFocus = EMPTY;
/** The last focus each participant sent; only the followed person's is shown. */
const byParticipant = new Map<string, FocusState>();
/** The participant this tab follows, or ``null``. */
let target: string | null = null;
let version = 0;
const listeners = new Set<() => void>();

function changed(): void {
  version += 1;
  for (const listener of listeners) listener();
}

/** Report this tab's own hover; a hover is also the tooltip a browser shows for it. */
export function reportHover(hover: ElementRef | null): void {
  if (sameRef(own.hover, hover)) return;
  own = { ...own, hover, tooltip: hover };
  changed();
}

/** Report this tab's own selection. */
export function reportSelection(selection: ElementRef | null): void {
  if (sameRef(own.selection, selection)) return;
  own = { ...own, selection };
  changed();
}

/** Report part of this tab's own open panels. */
export function reportPanels(panels: Partial<Panels>): void {
  const next = { ...own.panels, ...panels };
  if (samePanels(own.panels, next)) return;
  own = { ...own, panels: next };
  changed();
}

/** This tab follows ``participant`` now, or nobody; while it follows, its own mouse does not change what shows. */
export function setFollowTarget(participant: string | null): void {
  if (target === participant) return;
  target = participant;
  changed();
}

/** A participant's focus arrived (the server sends only the followed person's). */
export function putFocus(participant: string, focus: FocusState): void {
  byParticipant.set(participant, focus);
  if (participant === target) changed();
}

/** Whether this tab follows someone now: viewers then ignore the follower's own mouse. */
export function isFollowing(): boolean {
  return target !== null;
}

/** The followed person's focus, while following and once they sent one; ``null`` otherwise. */
export function mirroredFocus(): FocusState | null {
  return target === null ? null : (byParticipant.get(target) ?? null);
}

/** What this tab sends as its focus on ``page``: what it shows. */
export function focusToSend(page: string): FocusState {
  const shown = mirroredFocus();
  return shown ? { ...shown, page } : { ...own, page };
}

/** Forget everything (leaving a room, tests). */
export function clearFocus(): void {
  own = EMPTY;
  byParticipant.clear();
  target = null;
  changed();
}

export function subscribeFocus(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** The followed person's focus for React: re-renders when it changes. */
export function useMirroredFocus(): FocusState | null {
  useSyncExternalStore(subscribeFocus, () => version);
  return mirroredFocus();
}

/**
 * A panel's state for React: this tab's own value, or — while following — the followed person's.
 * The own value is reported for followers (``report``); when following stops, what was shown becomes
 * the own value, so nothing jumps back (FR-012).
 */
export function useShownPanel<T>(own: T, setOwn: (value: T) => void, pick: (panels: Panels) => T, report: (value: T) => Partial<Panels>): T {
  const mirrored = useMirroredFocus();
  const shown = mirrored ? pick(mirrored.panels) : own;
  const reportRef = useRef(report);
  reportRef.current = report;
  useEffect(() => reportPanels(reportRef.current(own)), [own]);
  const last = useRef<{ value: T } | null>(null);
  useEffect(() => {
    if (mirrored) {
      last.current = { value: shown };
    } else if (last.current) {
      setOwn(last.current.value);
      last.current = null;
    }
  });
  return shown;
}

export function sameRef(a: ElementRef | null, b: ElementRef | null): boolean {
  return a === b || (a !== null && b !== null && a.kind === b.kind && a.id === b.id);
}

function samePanels(a: Panels, b: Panels): boolean {
  return a.filter === b.filter && a.legend === b.legend && a.sidebar.length === b.sidebar.length && a.sidebar.every((id, i) => id === b.sidebar[i]);
}

/** Whether two focus states show the same thing (the sender sends only changes). */
export function sameFocus(a: FocusState, b: FocusState): boolean {
  return (
    a.page === b.page &&
    sameRef(a.hover, b.hover) &&
    sameRef(a.tooltip, b.tooltip) &&
    sameRef(a.selection, b.selection) &&
    samePanels(a.panels, b.panels)
  );
}
