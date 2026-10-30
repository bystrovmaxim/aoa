// src/lib/versionRange.ts
/**
 * The rules of two versions picked on one track (spec 038, FR-010 – FR-013): A is always the older and B the
 * newer, roles follow position — the left handle is A, the right one B — so a handle dragged past the other
 * swaps the two; the two never stand on one point, and a handle dropped on the other's point goes one point
 * further in the direction it was moving; Live, the track's last point, can only be B. Pure: the track's
 * points are given as their keys in track order (a short sha, or ``live``).
 */

import type { HistoryVersion } from "@/api/history";
import { shortSha } from "@/lib/versionNames";

/** Two picked points, A before B on the track. */
export type Range = { a: string; b: string };

/** Which of the two a handle is now. */
export type Side = "a" | "b";

/** A range after a move, and which side the moved handle ended on: focus follows it. */
export type Moved = { range: Range; side: Side };

/**
 * The track's points in order, as the track draws them: the versions oldest first — the newest left out while
 * Live runs exactly its graph, the two being one point — then the open pull requests, then Live.
 */
export function trackKeys(versions: readonly HistoryVersion[], live: string | null, liveIs: string | null = null, proposals: readonly HistoryVersion[] = []): string[] {
  const merged = Boolean(live && liveIs && versions.at(-1)?.sha === liveIs);
  const own = merged ? versions.slice(0, -1) : versions;
  return [...own.map(shortSha), ...proposals.map(shortSha), ...(live ? ["live"] : [])];
}

/** Whether a range can be picked at all: two points or more. */
export function diffOffered(points: readonly string[]): boolean {
  return points.length >= 2;
}

/**
 * ``a`` and ``b`` as a range, or ``{a: null, b}`` for one version: a reversed pair is swapped — so Live, the last
 * point, is never A —, the same point twice or an ``a`` the track lacks is one version; ``null`` when ``b`` is not on the track.
 */
export function normalise(points: readonly string[], a: string | null, b: string | null): { a: string | null; b: string } | null {
  if (b === null || !points.includes(b)) return null;
  if (a === null || a === b || !points.includes(a)) return { a: null, b };
  return points.indexOf(a) < points.indexOf(b) ? { a, b } : { a: b, b: a };
}

/** Going from One on ``v`` to Diff: ``v`` stays as B and A is the point before it; on the oldest point, B moves to the next one. */
export function oneToDiff(points: readonly string[], v: string): Range | null {
  if (!diffOffered(points)) return null;
  const at = Math.max(points.indexOf(v), 0);
  return at > 0 ? { a: points[at - 1], b: points[at] } : { a: points[0], b: points[1] };
}

/**
 * Put ``handle`` on point ``target``, moving in ``direction`` (−1 left, +1 right): on the other handle's point it
 * goes one further that way — or, at the track's end, stays on this side of it —, and the two are ordered again.
 */
export function moveTo(points: readonly string[], range: Range, handle: Side, target: number, direction: number): Moved {
  const own = points.indexOf(range[handle]);
  const other = points.indexOf(range[handle === "a" ? "b" : "a"]);
  let at = Math.min(Math.max(target, 0), points.length - 1);
  if (at === other) at = at + direction >= 0 && at + direction < points.length ? at + direction : at - direction;
  if (at === other || at < 0 || at >= points.length) at = own;
  return at < other ? { range: { a: points[at], b: points[other] }, side: "a" } : { range: { a: points[other], b: points[at] }, side: "b" };
}

/** ← or → on a handle: one point that way, past the other handle too; nothing past the track's ends. */
export function stepHandle(points: readonly string[], range: Range, handle: Side, delta: -1 | 1): Moved {
  const target = points.indexOf(range[handle]) + delta;
  if (target < 0 || target >= points.length) return { range, side: handle };
  return moveTo(points, range, handle, target, delta);
}

/** Shift + ← →: both handles one point that way, keeping the distance; nothing when either would leave the track. */
export function shiftBoth(points: readonly string[], range: Range, delta: -1 | 1): Range {
  const a = points.indexOf(range.a) + delta;
  const b = points.indexOf(range.b) + delta;
  return a < 0 || b >= points.length ? range : { a: points[a], b: points[b] };
}

/** Home or End on a handle: to that end of the track, by the rules of a move. */
export function homeEnd(points: readonly string[], range: Range, handle: Side, end: "home" | "end"): Moved {
  return end === "home" ? moveTo(points, range, handle, 0, -1) : moveTo(points, range, handle, points.length - 1, 1);
}

/**
 * The range after the track's list changed: a point that left moves toward the other one — A to the next newer
 * point, B to the next older one, both looked up in the old order —; when they would meet, one version is left.
 */
export function afterListChange(before: readonly string[], after: readonly string[], range: Range): { a: string | null; b: string } | null {
  const survivor = (key: string, step: 1 | -1, stop: string): string | null => {
    for (let at = before.indexOf(key); at >= 0 && at < before.length; at += step) {
      const candidate = before[at];
      if (candidate === stop) return null;
      if (after.includes(candidate)) return candidate;
    }
    return null;
  };
  const a = after.includes(range.a) ? range.a : survivor(range.a, 1, range.b);
  const b = after.includes(range.b) ? range.b : survivor(range.b, -1, range.a);
  if (b === null) return a === null ? null : { a: null, b: a };
  return normalise(after, a, b);
}
