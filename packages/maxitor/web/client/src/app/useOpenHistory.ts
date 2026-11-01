// src/app/useOpenHistory.ts
/**
 * The history a tab shows (spec 037): what was opened, the version chosen, and the source its graph
 * is read from. The mode follows the list (FR-009a); a history opens on its default version (FR-021);
 * a ``b`` the history does not offer falls back to that default; outside a room the list is polled
 * every 30 seconds with its ``ETag`` (FR-006a), and a version that disappears, or Live that goes,
 * moves the tab to the default with a notice. In Diff (spec 038) the tab holds two versions, A before B on
 * the track; an end that leaves the list moves toward the other, and when the two would meet one is left.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { historyVersions, type HistoryVersion, type OpenedHistory } from "@/api/history";
import { modeOf, type HistoryMode } from "@/model/historyMode";
import { defaultVersion, nameOf } from "@/lib/versionNames";
import { afterListChange, normalise, trackKeys, type Range } from "@/lib/versionRange";

/** How often a tab outside a room asks whether its history's list changed. */
export const HISTORY_POLL_MS = 30_000;

export type OpenHistory = {
  name: string;
  title: string;
  host: string;
  repository: string;
  key: string;
  versions: HistoryVersion[];
  live: string | null;
  /** The newest version's full sha when Live runs exactly its graph, else ``null``. */
  liveSameAs: string | null;
  /** Pull requests still open that change the graph: looked at, never opened on by default. */
  proposals: HistoryVersion[];
  etag: string | null;
  /** The chosen version: a short sha, ``live``, or ``null`` in M7. In Diff it is B, the newer one. */
  b: string | null;
  /** In Diff, A — the older version, before ``b`` on the track; ``null`` while one version is shown. */
  a: string | null;
  /** Whether the two compared stand side by side (spec 044); only with an ``a``. */
  split: boolean;
};

/** The history's track points in order: what A and B are ordered by. */
export function keysOf(history: Pick<OpenHistory, "versions" | "live" | "liveSameAs" | "proposals">): string[] {
  return trackKeys(history.versions, history.live, history.liveSameAs, history.proposals);
}

/** Whether ``b`` can be shown: listed and not refused, or Live where there is Live. A refused one may still be chosen to read its reason. */
export function offers(history: Pick<OpenHistory, "versions" | "live"> & { proposals?: HistoryVersion[] }, b: string | null): boolean {
  if (b === "live") return Boolean(history.live);
  return Boolean(b) && [...history.versions, ...(history.proposals ?? [])].some((version) => version.sha.startsWith(b ?? "\u0000"));
}

/** The version a short sha names, or ``null``. */
export function versionOf(history: Pick<OpenHistory, "versions"> & { proposals?: HistoryVersion[] }, b: string | null): HistoryVersion | null {
  if (!b || b === "live") return null;
  return [...history.versions, ...(history.proposals ?? [])].find((version) => version.sha.startsWith(b)) ?? null;
}

/** ``b`` as shown: the newest version is ``live`` while Live runs exactly its graph — they are one point. */
function asLive(b: string | null, liveSameAs: string | null): string | null {
  return b && b !== "live" && liveSameAs?.startsWith(b) ? "live" : b;
}

/** The graph source of the chosen version: Live's address, or the version's source; ``null`` for a refused one or M7. */
export function sourceOf(history: OpenHistory): string | null {
  if (history.b === "live") return history.live;
  const version = versionOf(history, history.b);
  return version && !version.refused ? version.source : null;
}

/** The track key a short sha from an address names — the address may carry a longer or a shorter sha. */
function fullKey(keys: readonly string[], b: string): string {
  return keys.find((key) => key === b || (b !== "live" && key !== "live" && (key.startsWith(b) || b.startsWith(key)))) ?? b;
}

export function useOpenHistory(polling: boolean) {
  const [history, setHistory] = useState<OpenHistory | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const historyRef = useRef(history);
  historyRef.current = history;

  /**
   * Show ``opened`` on ``wanted`` when it offers it, else on its default version; with ``wantedA`` too, in Diff —
   * a reversed pair swapped, the same version twice or an ``a`` it lacks shown as one version (spec 038, FR-014).
   */
  const show = useCallback((opened: OpenedHistory, key: string, wanted: string | null, wantedA: string | null = null, wantedSplit = false) => {
    const liveSameAs = opened.live_same_as ?? null;
    const proposals = opened.proposals ?? [];
    let b = asLive(offers({ ...opened, proposals }, wanted) ? wanted : defaultVersion(opened.versions, opened.live), liveSameAs);
    let a: string | null = null;
    if (wantedA && b) {
      const keys = trackKeys(opened.versions, opened.live, liveSameAs, proposals);
      const range = normalise(keys, asLive(fullKey(keys, wantedA), liveSameAs), fullKey(keys, b));
      if (range) ({ a, b } = range);
    }
    setNotice(null);
    setHistory({ name: opened.name, title: opened.title, host: opened.host, repository: opened.repository, key, versions: opened.versions, live: opened.live, liveSameAs, proposals, etag: null, b, a, split: wantedSplit && a !== null });
  }, []);

  /** Show one version: in a room or not, a pick in One leaves Diff. */
  const pick = useCallback((b: string) => {
    setHistory((current) => (current && offers(current, b) ? { ...current, b: asLive(b, current.liveSameAs), a: null, split: false } : current));
  }, []);

  /** Show two versions, A before B on the track (spec 038, FR-010); a pair the track does not hold is ignored. */
  const pickRange = useCallback((range: Range) => {
    setHistory((current) => {
      if (!current) return current;
      const keys = keysOf(current);
      const next = normalise(keys, asLive(range.a, current.liveSameAs), asLive(range.b, current.liveSameAs));
      return next && next.a ? { ...current, a: next.a, b: next.b } : current;
    });
  }, []);

  /** Stand the two compared side by side, or draw them together again; with no ``a`` there is nothing to split. */
  const pickSplit = useCallback((split: boolean) => {
    setHistory((current) => (current?.a ? { ...current, split } : current));
  }, []);

  const close = useCallback(() => {
    setHistory(null);
    setNotice(null);
  }, []);

  /** Take a new list: keep the version when it is still offered, else move to the default and say why. */
  const takeList = useCallback((versions: HistoryVersion[], live: string | null, etag: string | null, more: { liveSameAs?: string | null; proposals?: HistoryVersion[] } = {}) => {
    const current = historyRef.current;
    if (!current) return;
    const liveSameAs = more.liveSameAs ?? null;
    const next = { ...current, versions, live, liveSameAs, proposals: more.proposals ?? [], etag, b: asLive(current.b, liveSameAs), a: current.a ? asLive(current.a, liveSameAs) : null };
    if (current.a && current.b) {
      // In Diff an end that left moves toward the other; when they would meet, one version is left.
      const range = afterListChange(keysOf(current), keysOf(next), { a: current.a, b: current.b });
      if (range && (range.a !== current.a || range.b !== current.b)) setNotice("A version of the comparison is no longer in the history");
      if (range) {
        setHistory({ ...next, a: range.a, b: range.b });
        return;
      }
      next.a = null;
      next.split = false;
    }
    if (!offers(next, current.b)) {
      const gone = current.b === "live" ? "Live is no longer part of this history" : `${nameOf(current.versions, current.b) ?? current.b} is no longer in the history`;
      next.b = defaultVersion(versions, live);
      if (current.b) setNotice(gone);
    }
    setHistory(next);
  }, []);

  useEffect(() => {
    if (!polling || !history) return;
    const timer = window.setInterval(() => {
      const current = historyRef.current;
      if (!current) return;
      void historyVersions(current.name, current.key, current.etag ?? undefined)
        .then((answer) => {
          if (answer) takeList(answer.versions, answer.live, answer.etag, { liveSameAs: answer.live_same_as, proposals: answer.proposals });
        })
        .catch(() => undefined);
    }, HISTORY_POLL_MS);
    return () => window.clearInterval(timer);
  }, [polling, history?.name, takeList]); // eslint-disable-line react-hooks/exhaustive-deps

  const mode: HistoryMode = modeOf(history);
  return { history, mode, notice, setNotice, show, pick, pickRange, pickSplit, close, takeList };
}
