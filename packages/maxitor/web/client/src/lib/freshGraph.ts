// src/lib/freshGraph.ts
/**
 * Pages that follow their model (spec 028, FR-076; mockup screen 16).
 *
 * Maxitor rebuilds a held graph when its service changes. A tab outside a room learns it by asking
 * the graph's fingerprint every 30 seconds while it is visible; a tab inside a room is told by the
 * room. Either way the page re-reads the left panel and its diagram in place, keeping the page, its
 * settings and layout mode, the zoom and the centre — and a setting that names something no longer in
 * the model simply stops applying, as ``enabledKeys`` makes it.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { DiagramSurface, SavedView } from "@/rooms/diagramSurface";

/** How often a tab outside a room asks whether its graph changed. */
export const FINGERPRINT_POLL_MS = 30_000;

export type FingerprintPoll = {
  /** Ask Maxitor for the fingerprint it holds now. */
  read: () => Promise<string>;
  /** The fingerprint of the graph the tab drew, or ``null`` before it drew one. */
  known: () => string | null;
  /** The graph changed: Maxitor holds ``fingerprint``. */
  onChanged: (fingerprint: string) => void;
  intervalMs?: number;
};

/** Ask every ``intervalMs`` while the tab is visible, and at once when it comes back; returns the stop. */
export function startFingerprintPoll({ read, known, onChanged, intervalMs = FINGERPRINT_POLL_MS }: FingerprintPoll): () => void {
  const ask = () => {
    if (document.visibilityState !== "visible") return;
    read()
      .then((fingerprint) => {
        const drawn = known();
        if (drawn && fingerprint && fingerprint !== drawn) onChanged(fingerprint);
      })
      .catch(() => {
        // A failed question is asked again on the next tick; the page keeps what it shows.
      });
  };
  const timer = setInterval(ask, intervalMs);
  const onVisibility = () => {
    if (document.visibilityState === "visible") ask();
  };
  document.addEventListener("visibilitychange", onVisibility);
  return () => {
    clearInterval(timer);
    document.removeEventListener("visibilitychange", onVisibility);
  };
}

/** Poll while ``enabled``; ``known`` and ``onChanged`` are read fresh on every tick. */
export function useFingerprintPoll(enabled: boolean, read: () => Promise<string>, known: string | null, onChanged: (fingerprint: string) => void): void {
  const latest = useRef({ known, onChanged });
  latest.current = { known, onChanged };
  useEffect(() => {
    if (!enabled) return undefined;
    return startFingerprintPoll({ read, known: () => latest.current.known, onChanged: (fp) => latest.current.onChanged(fp) });
  }, [enabled, read]);
}

/** How long *The model was updated* stays. */
export const MODEL_UPDATED_MS = 4000;
/**
 * How long after a refresh the kept view is put back on each new diagram surface: a viewer may fit its
 * new diagram more than once while it arrives (a second batch of data, a second render).
 */
export const KEEP_VIEW_MS = 5000;

export type ModelRefreshOptions = {
  /** The diagram on screen. */
  surface: DiagramSurface | null;
  /** Read the left panel again. */
  rereadSidebar: () => void;
  /** Draw the current diagram again from the new graph. */
  redraw: () => void;
};

/**
 * ``refresh`` re-reads the left panel and redraws the diagram, and puts the zoom and centre back on
 * the diagram drawn from the new graph; ``updated`` is true while *The model was updated* shows.
 * Page, settings and layout mode survive by themselves: they live outside the viewer.
 */
export function useModelRefresh({ surface, rereadSidebar, redraw }: ModelRefreshOptions) {
  const surfaceRef = useRef(surface);
  surfaceRef.current = surface;
  const kept = useRef<{ view: SavedView; until: number } | null>(null);
  const [updated, setUpdated] = useState(false);

  const refresh = useCallback(() => {
    const view = surfaceRef.current?.view() ?? null;
    kept.current = view ? { view, until: Date.now() + KEEP_VIEW_MS } : null;
    rereadSidebar();
    redraw();
    setUpdated(true);
  }, [rereadSidebar, redraw]);

  // Each surface of the new diagram registers once it is fitted; the kept view then replaces the fit.
  useEffect(() => {
    const target = kept.current;
    if (!surface || !target) return;
    if (Date.now() > target.until) {
      kept.current = null;
      return;
    }
    surface.restore(target.view);
  }, [surface]);

  useEffect(() => {
    if (!updated) return undefined;
    const timer = setTimeout(() => setUpdated(false), MODEL_UPDATED_MS);
    return () => clearTimeout(timer);
  }, [updated]);

  return { refresh, updated, dismiss: () => setUpdated(false) };
}

/**
 * The keys a filter leaves on: all of ``keys`` while nobody chose (``chosen`` is ``null``), else the
 * chosen ones the model still has. A choice that names none of them — the model changed under it —
 * falls back to all; a choice of nothing stays nothing.
 */
export function enabledKeys(keys: readonly string[], chosen: readonly string[] | null): string[] {
  if (chosen === null) return [...keys];
  const kept = keys.filter((key) => chosen.includes(key));
  return kept.length > 0 || chosen.length === 0 ? kept : [...keys];
}
