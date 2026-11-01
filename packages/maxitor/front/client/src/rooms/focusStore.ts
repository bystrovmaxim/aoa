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

/** A diagram element, named by the id every viewer already uses for it — or a version on the picker's track. */
export type ElementRef = { kind: "node" | "row" | "edge" | "table" | "version"; id: string };

/** The version picker's track as its person moves it: the range a dragged handle or stretch would leave, and its scroll. */
export type TrackState = { a: string | null; b: string | null; offset: number };

/** The steps through a comparison's changes as their person moves them: the list open or not, the change they stand on, its card, the list's scroll (spec 040). */
export type ChangeListState = { open: boolean; at: string | null; card: boolean; offset: number; hot?: string | null };

/**
 * An open card, as its person holds it (spec 043, FR-010): the element it is about, the field list open or not, the row
 * pointed at, the scroll, and its place on the diagram. It is said outright, not read from the hover: on the card itself the pointer hovers nothing.
 */
export type CardPanel = { ref: ElementRef; fields: boolean; field: number | null; scroll: number; at: { x: number; y: number } | null };

/**
 * The open panels: the open left-panel branches; the filter panel — closed (``null``), open with no
 * section (``"open"``) or open on a section; whether the legend is expanded; whether the version
 * picker is open, and its track while it is (spec 038); the steps through a comparison's changes; the filter row
 * whose card says what keeps it hidden.
 */
export type Panels = {
  sidebar: string[];
  filter: "open" | "domains" | "kinds" | "changes" | null;
  legend: boolean;
  versions: boolean;
  track: TrackState | null;
  changes: ChangeListState | null;
  why: string | null;
  card?: CardPanel | null;
  /** The left panel narrowed to what changed (spec 044). */
  narrow?: boolean;
};

export type FocusState = {
  page: string;
  hover: ElementRef | null;
  tooltip: ElementRef | null;
  selection: ElementRef | null;
  panels: Panels;
};

type OwnFocus = Omit<FocusState, "page">;

const EMPTY: OwnFocus = { hover: null, tooltip: null, selection: null, panels: { sidebar: [], filter: null, legend: false, versions: false, track: null, changes: null, why: null } };

let own: OwnFocus = EMPTY;
/** The last focus each participant sent; only the followed person's is shown. */
const byParticipant = new Map<string, FocusState>();
/** The participant this tab follows, or ``null``. */
let target: string | null = null;
let version = 0;
const listeners = new Set<() => void>();

function sameCard(a: CardPanel | null | undefined, b: CardPanel | null | undefined): boolean {
  return sameRef(a?.ref ?? null, b?.ref ?? null) && a?.fields === b?.fields && a?.field === b?.field && a?.scroll === b?.scroll && a?.at?.x === b?.at?.x && a?.at?.y === b?.at?.y;
}

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

/** The participant this tab follows, or ``null``. */
export function followedParticipant(): string | null {
  return target;
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

function sameTrack(a: TrackState | null, b: TrackState | null): boolean {
  return a === b || (a !== null && b !== null && a.a === b.a && a.b === b.b && a.offset === b.offset);
}

function sameChanges(a: ChangeListState | null | undefined, b: ChangeListState | null | undefined): boolean {
  return a?.open === b?.open && a?.at === b?.at && a?.card === b?.card && a?.offset === b?.offset && (a?.hot ?? null) === (b?.hot ?? null);
}

function samePanels(a: Panels, b: Panels): boolean {
  return sameChanges(a.changes, b.changes) && (a.why ?? null) === (b.why ?? null) && sameCard(a.card, b.card) && a.filter === b.filter && a.legend === b.legend && a.versions === b.versions && (a.narrow ?? false) === (b.narrow ?? false) && sameTrack(a.track, b.track) && a.sidebar.length === b.sidebar.length && a.sidebar.every((id, i) => id === b.sidebar[i]);
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
