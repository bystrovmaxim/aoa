// src/api/map.ts
/**
 * The map's reads (spec 040): the overview first, one area at a time after it. Each version is laid out once on the
 * server, so a read may answer ``laying-out`` and is asked again.
 */
import { GraphReadError, graphFetch } from "@/api/client";

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
};

/** A version's map, without its nodes. */
export type MapOverview = {
  state: "ready" | "laying-out";
  types: string[];
  areas: MapArea[];
  /** Both areas' ids, how many links join them, and those links by the types of their ends. */
  bundles: [string, string, number, Record<string, number>][];
  shared: { id: string; domains: string[] }[];
};

/** One node of an area, at its place on the map. */
export type MapNode = { id: string; label: string; type: string; level: number; x: number; y: number };

/** One link of an area, with the level from which both its ends show. */
export type MapLink = { id: string; source: string; target: string; type: string; level: number };

/** One area up to a level. */
export type MapDetail = { nodes: MapNode[]; edges: MapLink[]; across: MapLink[] };

/** How long to wait before asking again whether a version is laid out. */
const LAYING_OUT_PAUSE_MS = 700;

/** Read a map path, or throw the server's refusal. */
async function read<T>(path: string, query?: URLSearchParams): Promise<T> {
  const response = await graphFetch(path, query);
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
