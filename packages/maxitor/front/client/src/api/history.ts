// src/api/history.ts
/**
 * Maxitor's history routes (spec 037, the history routes' contract): open a history, poll its versions.
 *
 * A history is named by its address without its key; the key, when there is one, travels only in the
 * header ``X-Maxitor-History-Key`` (FR-010b). A refusal comes back with the server's own words.
 */

import { apiUrl } from "@/api/client";

/** A version as the port lists it. */
export type HistoryVersion = {
  sha: string;
  date: string;
  pr?: { number: number; title: string; body: string; url: string };
  message?: string;
  tags: { name: string; release: { title: string; url: string } | null }[];
  nodes: number;
  edges: number;
  refused?: string;
  /** The source this version's graph is read under (the server's, keyless). */
  source: string;
};

/** An opened history, as the server answers it. */
export type OpenedHistory = {
  name: string;
  title: string;
  host: string;
  repository: string;
  live: string | null;
  versions: HistoryVersion[];
  count: number;
  room_ticket: string | null;
};

/** A refused history request: its status and the server's words. */
export class HistoryRequestError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

function headers(key: string, etag?: string): HeadersInit {
  const sent: Record<string, string> = {};
  if (key) sent["X-Maxitor-History-Key"] = key;
  if (etag) sent["If-None-Match"] = etag;
  return sent;
}

async function refusal(response: Response): Promise<HistoryRequestError> {
  let detail = `HTTP ${response.status}`;
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") detail = body.detail;
  } catch {
    // no JSON body: keep the status
  }
  return new HistoryRequestError(response.status, detail);
}

/** Open the history named ``name`` with ``key``; throws ``HistoryRequestError`` on a refusal. */
export async function openHistory(name: string, key: string): Promise<OpenedHistory> {
  const response = await fetch(`${apiUrl("/api/history/open")}?${new URLSearchParams({ history: name })}`, { headers: headers(key) });
  if (!response.ok) throw await refusal(response);
  return (await response.json()) as OpenedHistory;
}

/** The history's versions and Live, or ``null`` when ``etag`` is still current (``304``). */
export async function historyVersions(
  name: string,
  key: string,
  etag?: string,
): Promise<{ versions: HistoryVersion[]; live: string | null; etag: string | null } | null> {
  const response = await fetch(`${apiUrl("/api/history/versions")}?${new URLSearchParams({ history: name })}`, { headers: headers(key, etag) });
  if (response.status === 304) return null;
  if (!response.ok) throw await refusal(response);
  const body = (await response.json()) as { versions: HistoryVersion[]; live: string | null };
  return { ...body, etag: response.headers.get("etag") };
}
