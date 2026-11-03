// src/api/client.ts
const configuredApiBaseUrl = import.meta.env.VITE_MAXITOR_API_BASE_URL?.trim() ?? "";

/**
 * The graph-json URL this tab shows.
 *
 * One tab shows one source, so "the active source" is the tab's, not the process's; unlike the
 * server of #214, nothing here is shared between users.
 */
let activeSource: string | null = null;

/** Set the source every later graph read is for; ``null`` clears it. */
export function setActiveSource(url: string | null): void {
  activeSource = url;
}

/**
 * The read key of the private history whose version this tab shows, or ``""``. It travels on every
 * graph read only in the header ``X-Maxitor-History-Key``, never in the address (spec 037, FR-010b).
 */
let activeHistoryKey = "";

/** Set the key every later graph read sends; ``""`` sends none. */
export function setActiveHistoryKey(key: string): void {
  activeHistoryKey = key;
}

/** The source every later graph read is for, or ``null`` when no source is open. */
export function getActiveSource(): string | null {
  return activeSource;
}

/** One graph read's own source and key, in place of the tab's: how the older version of a comparison is read. */
export type GraphRead = { source: string; key: string };

/**
 * In Diff (spec 038), the older version A — its source and the history's key —, or ``null``: the tab's active
 * source is B, and the diagrams read A as well, to draw the two together.
 */
let activeBase: GraphRead | null = null;

/** Set the older version the diagrams compare with, or ``null`` to show one version. */
export function setActiveBase(base: GraphRead | null): void {
  activeBase = base;
}

/** The older version the diagrams compare with, or ``null``. */
export function getActiveBase(): GraphRead | null {
  return activeBase;
}

/** A graph read answered with a refusal; ``status`` tells a failure of the source from a busy server. */
export class GraphReadError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "GraphReadError";
  }
}

/** The pause the page asks for when the server does not say how long to wait, in seconds. */
const BUSY_FALLBACK_SECONDS = 5;
const BUSY_MAX_SECONDS = 30;

let busyWait: Promise<void> | null = null;
let nextBusySeconds = BUSY_FALLBACK_SECONDS;
const busyListeners = new Set<() => void>();

/** Subscribe to "the server is busy, this page is waiting to retry"; returns the unsubscribe. */
export function onGraphBusy(listener: () => void): () => void {
  busyListeners.add(listener);
  return () => {
    busyListeners.delete(listener);
  };
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

/** How long this 503 asks the page to wait: at least Retry-After, doubling, never over 30 s. */
function busyDelaySeconds(response: Response): number {
  const header = response.headers.get("Retry-After");
  const requested = header === null ? Number.NaN : Number(header);
  const wanted = Number.isFinite(requested) && requested > 0 ? Math.max(requested, nextBusySeconds) : nextBusySeconds;
  const delay = Math.min(wanted, BUSY_MAX_SECONDS);
  nextBusySeconds = Math.min(delay * 2, BUSY_MAX_SECONDS);
  return delay;
}

/** One retry loop for the whole page: every busy read waits on the same pause, not its own. */
function waitForBusyRetry(response: Response): Promise<void> {
  if (busyWait === null) {
    const delay = busyDelaySeconds(response);
    busyWait = sleep(delay * 1000);
    void busyWait.then(() => {
      busyWait = null;
    });
  }
  return busyWait;
}

/**
 * Read a graph endpoint for the active source — or for ``read``'s, with its key —, waiting out a busy server and retrying.
 *
 * A 503 means "no build slot right now": the source is fine, so the read keeps asking after the
 * pause the server named. Every other answer is returned as is, refusal included.
 */
export async function graphFetch(path: string, query?: URLSearchParams, read?: GraphRead): Promise<Response> {
  const key = read ? read.key : activeHistoryKey;
  for (;;) {
    const response = await fetch(graphApiUrl(path, query, read?.source), key ? { headers: { "X-Maxitor-History-Key": key } } : undefined);
    if (response.status !== 503) {
      nextBusySeconds = BUSY_FALLBACK_SECONDS;
      return response;
    }
    for (const listener of busyListeners) listener();
    await waitForBusyRetry(response);
  }
}

/** Absolute address of ``path``, honouring ``VITE_MAXITOR_API_BASE_URL`` when the client is built elsewhere. */
export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (!configuredApiBaseUrl) {
    return normalizedPath;
  }
  return `${configuredApiBaseUrl.replace(/\/$/, "")}${normalizedPath}`;
}

/**
 * Address of a graph read for the active source, with the route's own query parameters kept.
 *
 * ``URLSearchParams`` encodes the source, so a literal ``+`` travels as ``%2B`` and a space as
 * ``+`` — the server reads the source back unchanged and every read of one source names one key.
 */
/**
 * A read asked for before the tab knows its source — a history still opening, say. Not a failure: the read is asked
 * again once the source is named, so the page waits rather than reports it.
 */
export class NoSourceYetError extends Error {
  constructor() {
    super("No active source: name the AOA service graph-json URL before reading its graph.");
    this.name = "NoSourceYetError";
  }
}

export function graphApiUrl(path: string, query?: URLSearchParams, source?: string): string {
  const named = source ?? activeSource;
  if (named === null) {
    throw new NoSourceYetError();
  }
  const params = query === undefined ? new URLSearchParams() : new URLSearchParams(query);
  params.set("source", named);
  return `${apiUrl(path)}?${params.toString()}`;
}
