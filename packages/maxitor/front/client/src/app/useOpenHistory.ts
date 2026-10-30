// src/app/useOpenHistory.ts
/**
 * The history a tab shows (spec 037): what was opened, the version chosen, and the source its graph
 * is read from. The mode follows the list (FR-009a); a history opens on its default version (FR-021);
 * a ``b`` the history does not offer falls back to that default; outside a room the list is polled
 * every 30 seconds with its ``ETag`` (FR-006a), and a version that disappears, or Live that goes,
 * moves the tab to the default with a notice.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { historyVersions, type HistoryVersion, type OpenedHistory } from "@/api/history";
import { modeOf, type HistoryMode } from "@/model/historyMode";
import { defaultVersion, nameOf } from "@/lib/versionNames";

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
  /** The chosen version: a short sha, ``live``, or ``null`` in M7. */
  b: string | null;
};

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

export function useOpenHistory(polling: boolean) {
  const [history, setHistory] = useState<OpenHistory | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const historyRef = useRef(history);
  historyRef.current = history;

  /** Show ``opened`` on ``wanted`` when it offers it, else on its default version. */
  const show = useCallback((opened: OpenedHistory, key: string, wanted: string | null) => {
    const liveSameAs = opened.live_same_as ?? null;
    const proposals = opened.proposals ?? [];
    const b = asLive(offers({ ...opened, proposals }, wanted) ? wanted : defaultVersion(opened.versions, opened.live), liveSameAs);
    setNotice(null);
    setHistory({ name: opened.name, title: opened.title, host: opened.host, repository: opened.repository, key, versions: opened.versions, live: opened.live, liveSameAs, proposals, etag: null, b });
  }, []);

  const pick = useCallback((b: string) => {
    setHistory((current) => (current && offers(current, b) ? { ...current, b: asLive(b, current.liveSameAs) } : current));
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
    const next = { ...current, versions, live, liveSameAs, proposals: more.proposals ?? [], etag, b: asLive(current.b, liveSameAs) };
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
  return { history, mode, notice, setNotice, show, pick, close, takeList };
}
