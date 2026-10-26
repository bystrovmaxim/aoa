// src/components/diagrams/FullGraphViewer/arrangementStore.ts
/**
 * The remembered arrangement: one graph's node positions, kept in IndexedDB under its fingerprint.
 *
 * A fingerprint covers the graph's node ids and types, its edges and the layout settings, so a
 * changed graph or changed settings give a different key and are laid out afresh. Every failure
 * (no IndexedDB, no `crypto.subtle`, a full quota, a damaged entry) means "not remembered" and
 * never throws: the page then simply runs the layout.
 *
 * The store is a development-time contract with `data-model.md` "Fingerprint" and "Remembered
 * arrangement". The two decisions that must hold without IndexedDB — does the map cover every
 * node, which entries to evict — are exported as pure functions so the tests can pin them.
 */

import { LAYOUT_SETTINGS } from "./layoutSettings";

/** A node id mapped to its position. */
export type Positions = Record<string, [number, number]>;

/** One stored arrangement: the positions of a graph and when they were last used. */
export type ArrangementEntry = {
  fingerprint: string;
  positions: Positions;
  lastUsed: number;
};

type FingerprintPayload = {
  nodes: { id: unknown; data?: { node_type?: unknown } }[];
  edges: { source: unknown; target: unknown; data?: { edge_type?: unknown } }[];
};

const DATABASE = "maxitor-full-graph";
const STORE = "arrangements";
const LIMIT = 20;

/** True when every requested node has a finite position. */
export function coversEveryNode(positions: Positions, nodeIds: string[]): boolean {
  return nodeIds.every((id) => {
    const position = positions[id];
    return (
      Array.isArray(position) &&
      position.length === 2 &&
      Number.isFinite(position[0]) &&
      Number.isFinite(position[1])
    );
  });
}

/** The fingerprints to delete so that no more than ``limit`` entries remain, oldest first. */
export function entriesToEvict(entries: ArrangementEntry[], limit = LIMIT): string[] {
  if (entries.length <= limit) return [];
  return [...entries]
    .sort((left, right) => left.lastUsed - right.lastUsed)
    .slice(0, entries.length - limit)
    .map((entry) => entry.fingerprint);
}

/** The canonical JSON a fingerprint is taken over: rows sorted, labels and colours left out. */
function canonicalJson(payload: FingerprintPayload): string {
  const nodes = payload.nodes
    .map((node) => [String(node.id), String(node.data?.node_type ?? "")])
    .sort((left, right) => (left[0] < right[0] ? -1 : left[0] > right[0] ? 1 : 0));
  const edges = payload.edges
    .map((edge) => [String(edge.source), String(edge.target), String(edge.data?.edge_type ?? "")])
    .sort((left, right) => (left.join("\u0000") < right.join("\u0000") ? -1 : 1));
  return JSON.stringify({ settings: LAYOUT_SETTINGS, nodes, edges });
}

/** The graph's fingerprint, or ``null`` where ``crypto.subtle`` is unavailable (an insecure origin). */
export async function fingerprintGraph(payload: FingerprintPayload): Promise<string | null> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) return null;
  try {
    const bytes = new TextEncoder().encode(canonicalJson(payload));
    const digest = await subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest))
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
  } catch {
    return null;
  }
}

/** Open the store, creating it on first use. Throws where IndexedDB cannot be used. */
function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolvePromise, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("this browser has no IndexedDB"));
      return;
    }
    const request = indexedDB.open(DATABASE, 1);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE)) {
        const store = database.createObjectStore(STORE, { keyPath: "fingerprint" });
        store.createIndex("lastUsed", "lastUsed");
      }
    };
    request.onsuccess = () => resolvePromise(request.result);
    request.onerror = () => reject(request.error ?? new Error("IndexedDB refused to open"));
  });
}

/** The remembered positions of that graph, or ``null`` when there is nothing usable. */
export async function readArrangement(fingerprint: string, nodeIds: string[]): Promise<Positions | null> {
  try {
    const database = await openDatabase();
    try {
      const entry = await new Promise<ArrangementEntry | undefined>((resolvePromise, reject) => {
        const request = database.transaction(STORE, "readwrite").objectStore(STORE).get(fingerprint);
        request.onsuccess = () => resolvePromise(request.result as ArrangementEntry | undefined);
        request.onerror = () => reject(request.error);
      });
      if (!entry || !coversEveryNode(entry.positions, nodeIds)) return null;
      entry.lastUsed = Date.now();
      await new Promise<void>((resolvePromise) => {
        const request = database.transaction(STORE, "readwrite").objectStore(STORE).put(entry);
        request.onsuccess = () => resolvePromise();
        request.onerror = () => resolvePromise();
      });
      return entry.positions;
    } finally {
      database.close();
    }
  } catch {
    return null;
  }
}

/** Remember this graph's positions, dropping the least recently used beyond the bound. */
export async function writeArrangement(fingerprint: string, positions: Positions): Promise<void> {
  try {
    const database = await openDatabase();
    try {
      const store = database.transaction(STORE, "readwrite").objectStore(STORE);
      await new Promise<void>((resolvePromise, reject) => {
        const request = store.put({ fingerprint, positions, lastUsed: Date.now() });
        request.onsuccess = () => resolvePromise();
        request.onerror = () => reject(request.error);
      });
      const entries = await new Promise<ArrangementEntry[]>((resolvePromise, reject) => {
        const request = database.transaction(STORE, "readonly").objectStore(STORE).getAll();
        request.onsuccess = () => resolvePromise(request.result as ArrangementEntry[]);
        request.onerror = () => reject(request.error);
      });
      for (const key of entriesToEvict(entries)) {
        database.transaction(STORE, "readwrite").objectStore(STORE).delete(key);
      }
    } finally {
      database.close();
    }
  } catch {
    /* not remembered */
  }
}
