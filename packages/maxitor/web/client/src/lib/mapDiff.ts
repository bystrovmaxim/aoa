// src/lib/mapDiff.ts
/**
 * What a comparison says of the map as a whole (spec 040): every count comes from the server's list of changes, never
 * from what the browser has loaded, so the same counts read at every zoom.
 */
import type { MapChange } from "@/api/map";
import type { DiagramCounts } from "@/lib/erdDiff";
import { drawnOn, type Side } from "@/lib/half";

/** How many changes a list holds, by status: nodes and links alike, so the counts add up to the steps. */
export function countChanges(changes: readonly Pick<MapChange, "status">[]): DiagramCounts {
  const counts: DiagramCounts = { added: 0, removed: 0, changed: 0 };
  for (const change of changes) counts[change.status] += 1;
  return counts;
}

/** The same per area: an area named here holds a change, and every other is drawn grey. */
export function changesByArea(changes: readonly MapChange[]): Map<string, DiagramCounts> {
  const areas = new Map<string, DiagramCounts>();
  for (const change of changes) {
    const counts = areas.get(change.area) ?? { added: 0, removed: 0, changed: 0 };
    counts[change.status] += 1;
    areas.set(change.area, counts);
  }
  return areas;
}

/** The change one step from ``position`` in a list of ``total``, wrapping around; from no position, the first or the last. */
export function nextChange(position: number | null, by: -1 | 1, total: number): number {
  return ((position ?? (by > 0 ? -1 : 0)) + by + total) % total;
}

/** The first change of an area, in the stepping order. */
export function firstChangeOf(changes: readonly MapChange[], area: string): number {
  return changes.findIndex((change) => change.area === area);
}

/**
 * The areas ``node`` stands in in the version of ``side``, by the changed links to its domain that version has: an area is
 * its domain. The pair's drawing gives every end the newer version's area, so a table that moved to another domain is
 * found in the older one only this way.
 */
export function domainAreasOf(changes: readonly MapChange[], node: string, side: Side): string[] {
  const links = changes.filter((change) => change.type === "domain" && change.ends[0]?.[0] === node && drawnOn(side, change.status));
  return [...new Set(links.map((change) => change.ends[1]?.[0]).filter((id): id is string => Boolean(id)))];
}
