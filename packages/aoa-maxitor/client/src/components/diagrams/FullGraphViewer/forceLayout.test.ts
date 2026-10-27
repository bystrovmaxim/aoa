// src/components/diagrams/FullGraphViewer/forceLayout.test.ts
/**
 * `computeForceLayout` must run exactly the configuration it claims: the library's own merge of
 * the settings, around the origin, from the starting spiral.
 *
 * The reference is built independently of `forceLayout.ts` — the settings written out literally
 * and merged by the library itself (`new D3ForceLayout(rest)` then `execute(data, config)`). Only
 * a reference built a different way can prove the new code right (spec 026, research R4).
 *
 * The test runs in the check run, so it reads the fixture once and uses no timers or browser APIs.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { D3ForceLayout } from "@antv/layout";
import { describe, expect, it } from "vitest";

import { computeForceLayout, validatePositions } from "./forceLayout";
import { initialPositions } from "./initialPositions";

type Payload = {
  nodes: { id: string }[];
  edges: { source: string; target: string }[];
  constants: { node_visual_px: number };
};

// `npm test` runs in the client package; the fixture is Maxitor's answer for the frozen reference graph.
const FIXTURE = resolve(process.cwd(), "src/components/diagrams/FullGraphViewer/__fixtures__/full-graph-ref.json");
const payload: Payload = JSON.parse(readFileSync(FIXTURE, "utf8")).payload;

const NODE_VISUAL_PX = payload.constants.node_visual_px;
const NODE_IDS = payload.nodes.map((node) => String(node.id));
const EDGES = payload.edges.map((edge) => [String(edge.source), String(edge.target)] as [string, string]);

/** The settings written out literally, the way the old viewer gave them to G6. */
function literalLayout(): Record<string, unknown> {
  return {
    link: { distance: 72, strength: 0.82 },
    manyBody: { strength: -360, distanceMax: 1200 },
    collide: { radius: NODE_VISUAL_PX * 0.5 + 7, strength: 0.95, iterations: 4 },
    center: { strength: 0.012 },
    alphaDecay: 0.012,
    alphaMin: 0.0015,
    velocityDecay: 0.42,
  };
}

/** Run the library over the fixture around the origin, from the starting spiral. */
function runLibrary(layoutOptions: Record<string, unknown>): Map<string, [number, number]> {
  const start = initialPositions(NODE_IDS);
  const layout = new D3ForceLayout(layoutOptions as never);
  const data = {
    nodes: NODE_IDS.map((id) => ({ id, x: start[id][0], y: start[id][1] })),
    edges: EDGES.map(([source, target]) => ({ source, target })),
  };
  void layout.execute(data as never, {
    nodeSize: NODE_VISUAL_PX,
    width: 0,
    height: 0,
    center: { x: 0, y: 0, z: 0 },
  } as never);
  layout.stop();
  layout.tick(220);
  const positions = new Map<string, [number, number]>();
  for (const node of (layout as unknown as { nodes(): { id?: string | number; x?: number; y?: number }[] }).nodes()) {
    if (node.id === undefined) continue;
    positions.set(String(node.id), [Number(node.x), Number(node.y)]);
  }
  return positions;
}

describe("the full graph's layout", () => {
  it("equals the library's own merge of the settings for every node", () => {
    const reference = runLibrary(literalLayout());
    const actual = computeForceLayout({ nodes: NODE_IDS, edges: EDGES, nodeVisualPx: NODE_VISUAL_PX });

    expect(reference.size).toBe(NODE_IDS.length);
    for (const id of NODE_IDS) {
      const expected = reference.get(id);
      expect(expected, id).toBeDefined();
      expect(actual[id][0], `${id} x`).toBeCloseTo(expected![0], 9);
      expect(actual[id][1], `${id} y`).toBeCloseTo(expected![1], 9);
    }
  });

  it("rejects a result that misses a node", () => {
    expect(() => validatePositions({}, ["a"])).toThrow(/no finite position for a/);
    expect(() => validatePositions({ a: [0, Number.NaN] }, ["a"])).toThrow(/no finite position for a/);
  });

  it("differs when the centre's strength is lost by a shallow merge", () => {
    const reference = runLibrary(literalLayout());
    const { center: _center, ...withoutCenter } = literalLayout();
    const shallow = runLibrary(withoutCenter);
    let moved = 0;
    for (const id of NODE_IDS) {
      const expected = reference.get(id)!;
      const actual = shallow.get(id)!;
      moved = Math.max(moved, Math.hypot(actual[0] - expected[0], actual[1] - expected[1]));
    }
    expect(moved).toBeGreaterThan(1);
  });
});
