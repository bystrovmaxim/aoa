// src/components/diagrams/FullGraphViewer/layoutDeterminism.test.ts
/**
 * The full graph is laid out to the same bits on every engine and screen (spec 028, FR-001 … FR-005).
 *
 * Four things are pinned here, on Maxitor's answer for the frozen reference graph:
 * (a) the guard — the layout calls no function an engine may approximate in its own way
 *     (`Math.cos`, `Math.sin`, `Math.random`), and does not depend on how it computes `Math.pow`,
 *     which `d3-force-3d` calls with exact powers of two on every step and once, for a default
 *     that is then overridden, when the simulation is created;
 * (b) the screen does not enter the layout: no width or height in the request, and the same
 *     hash whatever size the window has;
 * (c) the golden hash — any change that moves a node fails here, and is recorded on purpose;
 * (d) the starting spiral, against a table computed independently (Python, the same rotation).
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { afterEach, describe, expect, it, vi } from "vitest";

import { layoutHash } from "@/lib/layoutHash";

import { computeForceLayout } from "./forceLayout";
import type { LayoutRequest } from "./forceLayout";
import { initialPositions } from "./initialPositions";

type Payload = {
  nodes: { id: string }[];
  edges: { source: string; target: string }[];
  constants: { node_visual_px: number };
};

const FIXTURE = resolve(process.cwd(), "src/components/diagrams/FullGraphViewer/__fixtures__/full-graph-ref.json");
const payload: Payload = JSON.parse(readFileSync(FIXTURE, "utf8")).payload;

const REQUEST: LayoutRequest = {
  nodes: payload.nodes.map((node) => String(node.id)),
  edges: payload.edges.map((edge) => [String(edge.source), String(edge.target)] as [string, string]),
  nodeVisualPx: payload.constants.node_visual_px,
};

/** The fixture's layout hash, recorded on purpose; change it only together with ``LAYOUT_VERSION``. */
const GOLDEN_HASH = "a07662ef7a786b3d422a8899628edd06e99f5d8205328b758fa9965d8f46192b";

/** The first 16 starting positions, computed in Python with the same rotation. */
const SPIRAL_REFERENCE: [number, number][] = [
  [7.0710678118654755, 0.0],
  [-9.03088751750192, 8.273032735715967],
  [1.3823220809823635, -15.750847141167634],
  [11.382848792909419, 14.846910566099625],
  [-20.88892748977138, -3.6949571482052987],
  [19.787815661112656, -12.587388583889224],
  [-6.61863708252693, 24.621000044064],
  [-12.6224587174052, -24.303776166007655],
  [27.385686463348303, 10.001208773502418],
  [-28.49024344919017, 11.7603583366272],
  [13.734179949820836, -29.349144810470026],
  [10.149209636450287, 32.357279609932995],
  [-30.589835678756238, -17.727435041389736],
  [35.885359342905645, -7.889295585192338],
  [-21.90027619416637, 31.15088927493452],
  [-5.059470916859724, -39.04358787357344],
];

/** Lay the fixture out and return its hash. */
async function fixtureHash(): Promise<string> {
  return layoutHash(computeForceLayout(REQUEST), REQUEST.nodes);
}

afterEach(() => {
  vi.restoreAllMocks();
});

/**
 * These tests lay out the whole reference graph, which takes a few seconds alone and longer when the
 * check run keeps the machine busy. They check the layout's result, not its speed, so they get room
 * beyond vitest's default 5 s limit.
 */
const WHOLE_GRAPH_TIMEOUT_MS = 20_000;

describe("the full graph's layout is the same everywhere", { timeout: WHOLE_GRAPH_TIMEOUT_MS }, () => {
  it("(a) calls no Math.cos, Math.sin or Math.random", () => {
    const spies = [vi.spyOn(Math, "cos"), vi.spyOn(Math, "sin"), vi.spyOn(Math, "random")];
    computeForceLayout(REQUEST);
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });

  it("(a) does not depend on how an engine computes Math.pow", async () => {
    const expected = await fixtureHash();
    const exactPow = Math.pow;
    // Every result one unit in the last place away from the exact one: an engine that rounds
    // differently must not be able to move a node.
    vi.spyOn(Math, "pow").mockImplementation((base, exponent) => {
      const value = exactPow(base, exponent);
      return value + Math.abs(value) * Number.EPSILON;
    });
    expect(await fixtureHash()).toBe(expected);
  });

  it("(b) takes no canvas size and gives the same hash on any window", async () => {
    expect(Object.keys(REQUEST).sort()).toEqual(["edges", "nodeVisualPx", "nodes"]);
    const sizes: [number, number][] = [
      [375, 812],
      [1600, 900],
    ];
    const hashes: string[] = [];
    for (const [width, height] of sizes) {
      vi.stubGlobal("innerWidth", width);
      vi.stubGlobal("innerHeight", height);
      hashes.push(await fixtureHash());
    }
    vi.unstubAllGlobals();
    expect(hashes[1]).toBe(hashes[0]);
  });

  it("(c) equals the recorded golden hash", async () => {
    expect(await fixtureHash()).toBe(GOLDEN_HASH);
  });

  it("(d) starts every node on the golden-angle spiral", () => {
    const ids = Array.from({ length: 16 }, (_, index) => `n${index}`);
    const start = initialPositions(ids);
    ids.forEach((id, index) => {
      expect(start[id]).toEqual(SPIRAL_REFERENCE[index]);
    });
    const all = initialPositions(REQUEST.nodes);
    const distinct = new Set(REQUEST.nodes.map((id) => all[id].join(",")));
    expect(distinct.size).toBe(REQUEST.nodes.length);
    for (const id of REQUEST.nodes) {
      expect(Number.isFinite(all[id][0]) && Number.isFinite(all[id][1])).toBe(true);
    }
  });
});
