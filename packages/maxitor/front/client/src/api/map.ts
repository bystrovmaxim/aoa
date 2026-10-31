// src/api/map.ts
/**
 * The map's reads (spec 040): the overview first, one area at a time after it. Each version is laid out once on the
 * server, so a read may answer ``laying-out`` and is asked again.
 */
import { GraphReadError, getActiveBase, getActiveSource, graphFetch } from "@/api/client";
import type { DiffStatus } from "@/api/compare";

/** What a comparison can say of an element: an element it does not name is unchanged. */
export type MapMark = Exclude<DiffStatus, "unchanged">;

/** A coarse grid of an area's nodes around its centre: cells are ``[column, row, type index, count]``. */
export type MapSketch = { cell: number; cells: [number, number, number, number][] };

/** One area of the map, as the overview gives it. */
export type MapArea = {
  id: string;
  name: string;
  colour: string;
  x: number;
  y: number;
  radius: number;
  counts: Record<string, number>;
  sketch?: MapSketch;
  failed?: boolean;
  /** In a comparison, an area only one version has. */
  status?: "added" | "removed";
  /** In a comparison, what changed here: by node type, how many of each status. */
  changes?: Record<string, Partial<Record<MapMark, number>>>;
};

/** A version's map, without its nodes. */
export type MapOverview = {
  state: "ready" | "laying-out";
  types: string[];
  areas: MapArea[];
  /** Both areas' ids, how many links join them, those links by the types of their ends and, in a comparison, how many changed. */
  bundles: [string, string, number, Record<string, number>, number?][];
  shared: { id: string; domains: string[] }[];
  /** In a comparison, how many drawn links changed; absent for one version. */
  links_changed?: number;
};

/** One node of an area, at its place on the map. */
export type MapNode = { id: string; label: string; type: string; level: number; x: number; y: number; diff?: MapMark };

/** One link of an area, with the level from which both its ends show. */
export type MapLink = { id: string; source: string; target: string; type: string; level: number; diff?: MapMark; was?: string };

/** One area up to a level. */
export type MapDetail = { nodes: MapNode[]; edges: MapLink[]; across: MapLink[] };

/** One changed node or link of a pair, in the order the map steps through them; a link stands at its middle, and ``span`` says how far apart its ends are. */
export type MapChange = { id: string; label: string; area: string; type: string; status: MapMark; x: number; y: number; level: number; span?: number };

/** How long to wait before asking again whether a version is laid out. */
const LAYING_OUT_PAUSE_MS = 700;

/** Read a map path, for the version on screen or, in Diff, for the two compared; or throw the server's refusal. */
async function read<T>(path: string, query = new URLSearchParams()): Promise<T> {
  const base = getActiveBase();
  const source = getActiveSource();
  if (base && source) query.set("a", base.source);
  const response = await graphFetch(path, query, base && source ? { source, key: base.key } : undefined);
  if (!response.ok) throw new GraphReadError(response.status, `${path} ${response.status}`);
  return (await response.json()) as T;
}

/** The overview of the version on screen, asking again while it is laid out. */
export async function mapOverview(onLayingOut: () => void): Promise<MapOverview> {
  for (;;) {
    const overview = await read<MapOverview>("/api/v1/map/overview");
    if (overview.state === "ready") return overview;
    onLayingOut();
    await new Promise((done) => setTimeout(done, LAYING_OUT_PAUSE_MS));
  }
}

/** One area, up to level 2 (entities and operations) or 3 (everything). */
export function mapArea(id: string, level: 2 | 3): Promise<MapDetail> {
  return read<MapDetail>("/api/v1/map/area", new URLSearchParams({ id, level: String(level) }));
}

/** Every changed node and link of the pair on screen, in the stepping order. */
export async function mapChanges(): Promise<MapChange[]> {
  return (await read<{ changes: MapChange[] }>("/api/v1/map/changes")).changes;
}
