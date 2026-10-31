// src/lib/mapVisibility.ts
/**
 * What the filters leave on the map (spec 040, FR-027 – FR-029a): a type switched off takes its nodes and everything
 * below them; a domain switched off takes its nodes unless another of their domains is on, and never what is outside
 * domains; a kind of change takes the nodes of that glance. All of it is read from the overview, so it holds at every
 * zoom with no node in the browser. Nothing here moves anything.
 */
import type { MapArea, MapBundle, MapChange, MapOverview, MapSketchCell } from "@/api/map";

/** The area of what belongs to no domain: no filter row, never hidden by one. */
export const OUTSIDE_AREA = "(outside)";

/** What a sketch's status index counts in. */
export const SKETCH_STATUSES = ["unchanged", "added", "removed", "changed"] as const;

/** What is switched off. */
export type MapFilters = { types: ReadonlySet<string>; domains: ReadonlySet<string>; changes: ReadonlySet<string> };

/** What the overview says once, for every question a filter asks. */
export type MapFacts = { types: readonly string[]; chains: readonly (readonly string[])[]; domainsOf: ReadonlyMap<string, readonly string[]> };

/** What keeps a row off the screen: a filter switched off. */
export type HiddenBy = { section: "types" | "domains" | "changes"; key: string };

/** How much of a row is left, and what took the rest. */
export type RowLeft = { left: number; total: number; hiddenBy: HiddenBy[] };

/** Every filter row's presence: each row is measured under the other filters, its own left out. */
export type MapPresence = { types: Map<string, RowLeft>; domains: Map<string, RowLeft>; changes: Map<string, RowLeft> };

export function mapFacts(overview: Pick<MapOverview, "types" | "chains" | "shared">): MapFacts {
  return { types: overview.types, chains: overview.chains, domainsOf: new Map(overview.shared.map(({ id, domains }) => [id, domains])) };
}

function typeOn(filters: MapFilters, type: string, chain: readonly string[]): boolean {
  return !filters.types.has(type) && !chain.some((above) => filters.types.has(above));
}

function domainOn(filters: MapFilters, facts: MapFacts, id: string, area: string): boolean {
  if (area === OUTSIDE_AREA) return true;
  return (facts.domainsOf.get(id) ?? [area]).some((domain) => !filters.domains.has(domain));
}

/** Whether one node stays on the map. */
export function nodeLeft(filters: MapFilters, facts: MapFacts, id: string, area: string, type: string, chain: number, status: string): boolean {
  return typeOn(filters, type, facts.chains[chain] ?? []) && !filters.changes.has(status) && domainOn(filters, facts, id, area);
}

/** The cells of an area's sketch that stay; none of a domain switched off. */
export function cellsLeft(area: MapArea, filters: MapFilters, facts: MapFacts): MapSketchCell[] {
  if (filters.domains.has(area.id)) return [];
  return (area.sketch?.cells ?? []).filter(([, , type, , chain, status]) => typeOn(filters, facts.types[type], facts.chains[chain]) && !filters.changes.has(SKETCH_STATUSES[status]));
}

/** What is left of an area, and where its name stands: with what is left, and at its own place when nothing is cut. */
export type AreaLeft = { left: number; total: number; x: number; y: number; radius: number };

/** How far past what is left an area's name and reach stand, in map units. */
const LEFT_MARGIN = 80;
const LEAST_LEFT_REACH = 120;

/** What the filters leave of one area (FR-029a). */
export function areaLeft(area: MapArea, filters: MapFilters, facts: MapFacts): AreaLeft {
  const whole = { x: area.x, y: area.y, radius: area.radius };
  if (!area.sketch) return { left: Number(!filters.domains.has(area.id)), total: 1, ...whole };
  const { cell } = area.sketch;
  const total = area.sketch.cells.reduce((sum, each) => sum + each[3], 0) || 1;
  const cells = cellsLeft(area, filters, facts);
  const left = cells.reduce((sum, each) => sum + each[3], 0);
  if (left === total || left === 0) return { left, total, ...whole };
  const placed = cells.map(([column, row, , count]) => ({ x: area.x + (column + 0.5) * cell, y: area.y + (row + 0.5) * cell, count }));
  const x = placed.reduce((sum, each) => sum + each.x * each.count, 0) / left;
  const y = placed.reduce((sum, each) => sum + each.y * each.count, 0) / left;
  return { left, total, x, y, radius: Math.max(LEAST_LEFT_REACH, ...placed.map((each) => Math.hypot(each.x - x, each.y - y))) + LEFT_MARGIN };
}

/** How many links of a bundle stay. */
export function bundleLeft(bundle: MapBundle, filters: MapFilters): number {
  const [one, other, , ends, changed = {}] = bundle;
  if (filters.domains.has(one) || filters.domains.has(other)) return 0;
  let left = 0;
  for (const [key, count] of Object.entries(ends)) {
    if (key.split("|").every((end) => end.split(">").every((type) => !filters.types.has(type)))) left += count;
  }
  const statuses = Object.entries(changed);
  const marked = statuses.reduce((sum, [, count]) => sum + (count ?? 0), 0);
  const off = statuses.reduce((sum, [status, count]) => sum + (filters.changes.has(status) ? (count ?? 0) : 0), 0);
  return filters.changes.has("unchanged") ? Math.min(left, marked - off) : Math.max(0, left - off);
}

/** The changes the filters leave, in their order: a change needs its own status on and every node it stands on left. */
export function changesLeft(changes: readonly MapChange[], filters: MapFilters, facts: MapFacts): MapChange[] {
  return changes.filter((change) => !filters.changes.has(change.status) && change.ends.every(([id, area, type, chain, status]) => nodeLeft(filters, facts, id, area, type, chain, status)));
}

function rowOf(rows: Map<string, RowLeft>, key: string): RowLeft {
  let row = rows.get(key);
  if (!row) {
    row = { left: 0, total: 0, hiddenBy: [] };
    rows.set(key, row);
  }
  return row;
}

function noteHidden(row: RowLeft, reasons: readonly HiddenBy[]): void {
  for (const reason of reasons) if (!row.hiddenBy.some((each) => each.section === reason.section && each.key === reason.key)) row.hiddenBy.push(reason);
}

/** Count one row's share of a cell: left when nothing else takes it, else what took it. */
function count(row: RowLeft, amount: number, reasons: readonly HiddenBy[]): void {
  row.total += amount;
  if (reasons.length === 0) row.left += amount;
  else noteHidden(row, reasons);
}

/** What is left of every filter row, and what took the rest (FR-028b): a row is measured with its own switch left out, so its state and its dimness stay two axes. */
export function presence(overview: MapOverview, filters: MapFilters, facts: MapFacts): MapPresence {
  const rows: MapPresence = { types: new Map(), domains: new Map(), changes: new Map() };
  for (const area of overview.areas) {
    const domain: HiddenBy[] = filters.domains.has(area.id) ? [{ section: "domains", key: area.id }] : [];
    for (const [, , typeIndex, amount, chainIndex, statusIndex] of area.sketch?.cells ?? []) {
      const type = facts.types[typeIndex];
      const status = SKETCH_STATUSES[statusIndex];
      const own: HiddenBy[] = filters.types.has(type) ? [{ section: "types", key: type }] : [];
      const chain: HiddenBy[] = facts.chains[chainIndex].filter((above) => filters.types.has(above)).map((key) => ({ section: "types", key }));
      const changed: HiddenBy[] = filters.changes.has(status) ? [{ section: "changes", key: status }] : [];
      count(rowOf(rows.types, type), amount, [...domain, ...chain, ...changed]);
      count(rowOf(rows.domains, area.id), amount, [...own, ...chain, ...changed]);
      count(rowOf(rows.changes, status), amount, [...domain, ...own, ...chain]);
    }
  }
  return rows;
}
