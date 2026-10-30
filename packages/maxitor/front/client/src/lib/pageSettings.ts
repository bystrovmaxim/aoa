// src/lib/pageSettings.ts
/**
 * A page's filters and layout mode: the person's own outside a room, the room's inside one
 * (spec 028, FR-030 … FR-033).
 *
 * Viewers read and set them through ``usePageSetting``. Outside a room a value is kept per page for
 * the life of the tab, as the viewers' own maps kept it before. Inside a room the page shows the
 * room's value, else the default — never the person's own (spec 029) — and a change is sent as the
 * new value — "set to", never "toggle" — so the last change wins for everyone; it shows at once and
 * the room's echo confirms it. A tab that opens a room first seeds it with its own values. Zoom, scroll, hover and
 * collapsed panels are not page settings and stay personal (FR-032).
 */
import { createContext, createElement, useCallback, useContext, useRef, useSyncExternalStore, type ReactNode } from "react";
import type { PageSettings } from "@/rooms/protocol";

/** What the page settings need from the room the tab is in. */
export type RoomSettings = {
  settings: PageSettings;
  /** Send ``name = value`` for ``page`` to the room. */
  set(page: string, name: string, value: unknown): void;
};

type PageSettingsContextValue = {
  /** The key of the page on screen (``rooms/pageKey.ts``), or ``null`` before one is chosen. */
  page: string | null;
  room: RoomSettings | null;
};

const PageSettingsContext = createContext<PageSettingsContextValue>({ page: null, room: null });

export function PageSettingsProvider({ page, room, children }: PageSettingsContextValue & { children: ReactNode }) {
  return createElement(PageSettingsContext.Provider, { value: { page, room } }, children);
}

/** The key of the page on screen, or ``null`` before one is chosen (what a viewer's focus names). */
export function useCurrentPage(): string | null {
  return useContext(PageSettingsContext).page;
}

/** Page key → setting name → value, for this tab outside a room. */
const local = new Map<string, Map<string, unknown>>();
const listeners = new Set<() => void>();
let version = 0;

function writeLocal(page: string, name: string, value: unknown): void {
  let settings = local.get(page);
  if (!settings) {
    settings = new Map();
    local.set(page, settings);
  }
  settings.set(name, value);
  version += 1;
  for (const listener of listeners) listener();
}

/** Keep a room's settings as this tab's own: leaving a room keeps every page as it was (FR-019). */
export function keepRoomSettings(settings: PageSettings): void {
  for (const [page, values] of Object.entries(settings)) {
    for (const [name, value] of Object.entries(values)) writeLocal(page, name, value);
  }
}

/** This tab's own values, page key → setting name → value: what it brings into a room it opens (spec 029, FR-001). */
export function ownSettingsByPage(): Record<string, Record<string, unknown>> {
  return Object.fromEntries([...local].map(([page, values]) => [page, Object.fromEntries(values)]));
}

/** Take ``values`` as this tab's own for ``page`` — the view an address names, read when the page opens (spec 038). */
export function seedPageSettings(page: string, values: Readonly<Record<string, unknown>>): void {
  for (const [name, value] of Object.entries(values)) writeLocal(page, name, value);
}

/** The settings ``page`` shows: the room's inside one, this tab's own outside. */
export function shownPageSettings(page: string, room: RoomSettings | null): Record<string, unknown> {
  return room ? { ...(room.settings[page] ?? {}) } : Object.fromEntries(local.get(page) ?? []);
}

/** A number that changes whenever a setting kept outside a room does: what an address that follows them listens to. */
export function usePageSettingsVersion(): number {
  return useSyncExternalStore(subscribe, () => version);
}

/** Forget every value kept outside a room (tests). */
export function clearLocalPageSettings(): void {
  local.clear();
  version += 1;
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/**
 * The value of setting ``name`` on the page on screen, and the call that sets it. ``fallback`` is the
 * value when nobody has set it: the viewer's default, taken from the first render so that a literal
 * ``[]`` is the same array on every render and never re-runs an effect that depends on it.
 */
export function usePageSetting<T>(name: string, fallback: T): [T, (value: T) => void] {
  const { page, room } = useContext(PageSettingsContext);
  const fallbackRef = useRef(fallback);
  useSyncExternalStore(subscribe, () => version);
  // Inside a room only the room's value counts, so everyone sees one picture (spec 029, FR-002).
  const held = page ? (room ? room.settings[page]?.[name] : local.get(page)?.get(name)) : undefined;
  const value = (held !== undefined ? held : fallbackRef.current) as T;

  const set = useCallback(
    (next: T) => {
      if (!page) return;
      writeLocal(page, name, next);
      room?.set(page, name, next);
    },
    [page, room, name],
  );
  return [value, set];
}
