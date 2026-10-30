// src/lib/liveLine.ts
/**
 * Live's closing line under the track (spec 037, FR-030), after the word Live the page sets in bold: Live
 * has no message, so the line says when it was last read and which version is newest — without that last part when there is none (M6) —
 * or, while it cannot be read, since when.
 */

import type { HistoryVersion } from "@/api/history";
import { nameOf } from "@/lib/versionNames";

/** How Live was last read: fine, or not, and when. */
export type LiveState = { ok: boolean; at: number };

/** How long ago ``at`` was, in words. */
export function ago(at: number, now: number = Date.now()): string {
  const seconds = Math.max(0, Math.round((now - at) / 1000));
  return seconds < 60 ? `${seconds} s` : `${Math.round(seconds / 60)} min`;
}

/** Live's closing line for a history of ``versions``. */
export function liveLine(versions: readonly HistoryVersion[], state: LiveState | null, now: number = Date.now()): string {
  if (state && !state.ok) return `cannot be reached since ${new Date(state.at).toLocaleTimeString()}`;
  const checked = state ? `checked ${ago(state.at, now)} ago` : "not checked yet";
  const newest = versions.at(-1);
  if (!newest) return checked;
  return `${checked} · newest version ${nameOf(versions, newest.sha)}, ${newest.date.slice(0, 10)}`;
}
