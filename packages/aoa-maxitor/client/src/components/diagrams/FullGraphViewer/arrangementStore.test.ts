// src/components/diagrams/FullGraphViewer/arrangementStore.test.ts
/**
 * The remembered arrangement keeps the right entries and never breaks the page.
 *
 * The store runs in the check run (jsdom has no IndexedDB), so the tests pin the decisions that
 * must hold without a database — the fingerprint's coverage and the eviction order — and confirm
 * that every storage failure reads as "not remembered" rather than as an error.
 */

import { describe, expect, it } from "vitest";

import type { ArrangementEntry } from "./arrangementStore";
import { coversEveryNode, entriesToEvict, fingerprintGraph, readArrangement, writeArrangement } from "./arrangementStore";
import { LAYOUT_SETTINGS } from "./layoutSettings";

const NODES = [
  { id: "b", data: { node_type: "Entity", label: "b", fill: "#111" } },
  { id: "a", data: { node_type: "Domain", label: "a", fill: "#222" } },
];
const EDGES = [
  { source: "a", target: "b", data: { edge_type: "summary_aspect_edges", label: "x" } },
];
const PAYLOAD = { nodes: NODES, edges: EDGES };
const NODE_IDS = ["a", "b"];

function entry(fingerprint: string, lastUsed: number): ArrangementEntry {
  return { fingerprint, positions: {}, lastUsed };
}

describe("the fingerprint", () => {
  it("ignores row order, labels and colours", async () => {
    const reordered = {
      nodes: [
        { id: "b", data: { node_type: "Entity", label: "other", fill: "#fff" } },
        { id: "a", data: { node_type: "Domain", label: "other", fill: "#000" } },
      ],
      edges: [...EDGES].reverse().map((edge) => ({ ...edge, data: { ...edge.data, label: "other" } })),
    };
    expect(await fingerprintGraph(reordered)).toBe(await fingerprintGraph(PAYLOAD));
  });

  it("changes when a node is added, retyped or an edge is retyped", async () => {
    const base = await fingerprintGraph(PAYLOAD);
    expect(await fingerprintGraph({ nodes: [...NODES, { id: "c", data: { node_type: "Role" } }], edges: EDGES })).not.toBe(base);
    expect(
      await fingerprintGraph({
        nodes: [NODES[0], { id: "a", data: { node_type: "Entity" } }],
        edges: EDGES,
      }),
    ).not.toBe(base);
    expect(
      await fingerprintGraph({
        nodes: NODES,
        edges: [{ ...EDGES[0], data: { edge_type: "composition_edges" } }],
      }),
    ).not.toBe(base);
  });

  it("changes when the layout settings change", async () => {
    const base = await fingerprintGraph(PAYLOAD);
    const before = LAYOUT_SETTINGS.alphaDecay;
    LAYOUT_SETTINGS.alphaDecay = before + 0.01;
    try {
      expect(await fingerprintGraph(PAYLOAD)).not.toBe(base);
    } finally {
      LAYOUT_SETTINGS.alphaDecay = before;
    }
  });

  it("is null where crypto.subtle is missing", async () => {
    const original = globalThis.crypto;
    Object.defineProperty(globalThis, "crypto", { value: {}, configurable: true });
    try {
      expect(await fingerprintGraph(PAYLOAD)).toBeNull();
    } finally {
      Object.defineProperty(globalThis, "crypto", { value: original, configurable: true });
    }
  });
});

describe("a position map", () => {
  it("must cover every node with finite coordinates", () => {
    expect(coversEveryNode({ a: [1, 2], b: [3, 4] }, NODE_IDS)).toBe(true);
    expect(coversEveryNode({ a: [1, 2] }, NODE_IDS)).toBe(false);
    expect(coversEveryNode({ a: [1, 2], b: [Number.NaN, 4] }, NODE_IDS)).toBe(false);
  });
});

describe("eviction", () => {
  it("keeps twenty and drops the oldest first", () => {
    const twenty = Array.from({ length: 20 }, (_, index) => entry(`f${index}`, index));
    expect(entriesToEvict(twenty)).toEqual([]);

    const twentyOne = [...twenty, entry("newest", 20)];
    expect(entriesToEvict(twentyOne)).toEqual(["f0"]);

    const shuffled = [entry("old", 1), entry("new", 9), entry("middle", 5)];
    expect(entriesToEvict(shuffled, 2)).toEqual(["old"]);
  });
});

describe("without a database", () => {
  it("reads as not remembered and writes without throwing", async () => {
    await expect(readArrangement("fingerprint", NODE_IDS)).resolves.toBeNull();
    await expect(writeArrangement("fingerprint", { a: [1, 2], b: [3, 4] })).resolves.toBeUndefined();
  });
});
