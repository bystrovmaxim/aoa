// src/api/compare.ts
/**
 * The two comparison reads (spec 038, its contract of the server): what changed from A to B,
 * and how one element changed. B is the tab's active source, A the base it compares with; both versions travel
 * with the history's key in the header, never in the address.
 */
import { getActiveBase, getActiveSource, graphFetch, type GraphRead } from "@/api/client";

/** What happened to an element between A and B. */
export type DiffStatus = "added" | "removed" | "changed" | "unchanged";

/** Per kind, how many were added, removed and changed. */
export type DiffCounts = { added: number; removed: number; changed: number };

/** The changed elements of a pair: an element left out is unchanged. */
export type CompareResult = {
  counts: { nodes: DiffCounts; edges: DiffCounts };
  nodes: Record<string, Exclude<DiffStatus, "unchanged">>;
  edges: Record<string, Exclude<DiffStatus, "unchanged">>;
  sha_a?: string;
  sha_b?: string;
};

let pairDigest = "";

/** The sha256 of A and of B as last read: a room's check takes in what is compared (spec 044). */
export function comparedDigest(): string {
  return pairDigest;
}

/** One changed property of an element: its path from the element's top, and its values in A and B. */
export type ElementDifference = { path: string[]; change: "added" | "removed" | "changed"; before?: unknown; after?: unknown };

/** One element as it compares. */
export type CompareElementResult = { status: DiffStatus; differences: ElementDifference[] };

/** A comparison read for B with A named as ``a``, sent with A's key — B may be Live, which needs none. */
async function compareFetch(path: string, query: URLSearchParams): Promise<Response> {
  const base = getActiveBase();
  const source = getActiveSource();
  if (!base || !source) throw new Error("No two versions to compare.");
  query.set("a", base.source);
  const read: GraphRead = { source, key: base.key };
  const response = await graphFetch(path, query, read);
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  return response;
}

/** The statuses and counts of the pair being compared. */
export async function compareVersions(): Promise<CompareResult> {
  const compared = (await (await compareFetch("/api/v1/compare", new URLSearchParams())).json()) as CompareResult;
  pairDigest = compared.sha_a && compared.sha_b ? `${compared.sha_a}.${compared.sha_b}` : "";
  return compared;
}

/** How one node or edge changed. */
export async function compareElement(kind: "node" | "edge", id: string): Promise<CompareElementResult> {
  return (await (await compareFetch("/api/v1/compare-element", new URLSearchParams({ kind, id }))).json()) as CompareElementResult;
}

/** One changed thing inside an action, which a use-case diagram does not draw. */
export type ChangedPart = {
  kind: "node" | "edge";
  id: string;
  label: string;
  type: string;
  /** What of the action it belongs to: ``Params``, ``Result``, an aspect, or ``Links``. */
  group: string;
  status: Exclude<DiffStatus, "unchanged">;
  differences: ElementDifference[];
};

/** Each action's changed parts by its id; an action with none is left out. */
export type ChangedInside = Record<string, ChangedPart[]>;

/** What changed inside the actions of the pair being compared. */
export async function compareChangedInside(): Promise<ChangedInside> {
  return ((await (await compareFetch("/api/v1/compare/changed-inside", new URLSearchParams())).json()) as { actions: ChangedInside }).actions;
}
