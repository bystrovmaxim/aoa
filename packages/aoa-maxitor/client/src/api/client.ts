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

/** The source every later graph read is for, or ``null`` when no source is open. */
export function getActiveSource(): string | null {
  return activeSource;
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
export function graphApiUrl(path: string, query?: URLSearchParams): string {
  if (activeSource === null) {
    throw new Error("No active source: name the AOA service graph-json URL before reading its graph.");
  }
  const params = query === undefined ? new URLSearchParams() : new URLSearchParams(query);
  params.set("source", activeSource);
  return `${apiUrl(path)}?${params.toString()}`;
}
