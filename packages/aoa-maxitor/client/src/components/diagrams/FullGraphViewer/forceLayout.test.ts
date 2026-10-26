// src/components/diagrams/FullGraphViewer/forceLayout.test.ts
/**
 * The worker's layout must be today's picture: the same positions G6's configuration gives.
 *
 * The reference is built independently of `forceLayout.ts` — today's `layout` object copied
 * literally from the old viewer, its date and strength accessors included, and merged by the
 * library itself (`new D3ForceLayout(rest)` then `execute(data, config)`). Only a reference
 * built a different way can prove the new code right (research R4).
 *
 * The test runs in the check run, so it reads the fixture once and uses no timers or browser APIs.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { D3ForceLayout } from "@antv/layout";
import { describe, expect, it } from "vitest";

import { computeForceLayout, validatePositions } from "./forceLayout";

type PayloadNode = { id: string; data?: Record<string, unknown>; style?: Record<string, unknown> };
type PayloadEdge = { source: string; target: string; id?: string; data?: Record<string, unknown> };
type Payload = {
  nodes: PayloadNode[];
  edges: PayloadEdge[];
  node_type_map: Record<string, string>;
  constants: {
    node_visual_px: number;
    entity_field_interchange_type?: string;
    layout_entity_scalar_link?: { distance: number; strength: number };
  };
};

// `npm test` runs in the client package, three levels below the repository root.
const DATA = resolve(process.cwd(), "../../../specs/026-full-graph-fast-open/data");
const payload: Payload = JSON.parse(readFileSync(resolve(DATA, "full-graph-ref.json"), "utf8")).payload;
const baseline = JSON.parse(readFileSync(resolve(DATA, "baseline-main.json"), "utf8")) as {
  canvasSize: [number, number];
};

const [CANVAS_WIDTH, CANVAS_HEIGHT] = baseline.canvasSize;
const NODE_VISUAL_PX = payload.constants.node_visual_px;
const NODE_IDS = payload.nodes.map((node) => String(node.id));
const EDGES = payload.edges.map((edge) => [String(edge.source), String(edge.target)] as [string, string]);

/** Today's `layout` object, copied verbatim from the old `FullGraphViewer.tsx`. */
function todayLayout(): Record<string, unknown> {
  const nodeTypeMap = payload.node_type_map;
  const scalarLink = payload.constants.layout_entity_scalar_link;
  const entityFieldType = String(payload.constants.entity_field_interchange_type ?? "EntityField").trim();
  const px = NODE_VISUAL_PX;
  return {
    type: "d3-force",
    iterations: 220,
    animation: false,
    link: {
      distance: (edge: { source: unknown; target: unknown }) => {
        const st = nodeTypeMap[String(edge.source)] ?? "";
        const tt = nodeTypeMap[String(edge.target)] ?? "";
        const entityScalar =
          (st === "Entity" && tt === entityFieldType) || (st === entityFieldType && tt === "Entity");
        if (scalarLink && entityScalar) return scalarLink.distance;
        return st === tt ? 72 : 200;
      },
      strength: (edge: { source: unknown; target: unknown }) => {
        const st = nodeTypeMap[String(edge.source)] ?? "";
        const tt = nodeTypeMap[String(edge.target)] ?? "";
        const entityScalar =
          (st === "Entity" && tt === entityFieldType) || (st === entityFieldType && tt === "Entity");
        if (scalarLink && entityScalar) return scalarLink.strength;
        return st === tt ? 0.82 : 0.11;
      },
    },
    manyBody: { strength: -360, distanceMax: 1200 },
    collide: { radius: px * 0.5 + 7, strength: 0.95, iterations: 4 },
    center: { strength: 0.012 },
    alphaDecay: 0.012,
    alphaMin: 0.0015,
    velocityDecay: 0.42,
  };
}

/** Run the library over the fixture the way G6 does, and return the positions it produces. */
function runG6Configuration(layoutOptions: Record<string, unknown>): Map<string, [number, number]> {
  const layout = new D3ForceLayout(layoutOptions as never);
  const data = {
    nodes: NODE_IDS.map((id) => ({ id })),
    edges: EDGES.map(([source, target]) => ({ source, target })),
  };
  void layout.execute(data as never, {
    nodeSize: NODE_VISUAL_PX,
    width: CANVAS_WIDTH,
    height: CANVAS_HEIGHT,
    center: { x: CANVAS_WIDTH / 2, y: CANVAS_HEIGHT / 2, z: 0 },
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

/** Today's layout minus the keys G6 strips before it merges. */
function restOfTodayLayout(): Record<string, unknown> {
  const { type: _type, animation: _animation, iterations: _iterations, ...rest } = todayLayout();
  return rest;
}

describe("the layout worker's positions", () => {
  it("equal today's G6 configuration for every node", () => {
    const reference = runG6Configuration(restOfTodayLayout());
    const actual = computeForceLayout({
      nodes: NODE_IDS,
      edges: EDGES,
      nodeVisualPx: NODE_VISUAL_PX,
      width: CANVAS_WIDTH,
      height: CANVAS_HEIGHT,
    });

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
    const reference = runG6Configuration(restOfTodayLayout());
    const { center: _center, ...withoutCenter } = restOfTodayLayout();
    const shallow = runG6Configuration(withoutCenter);
    let moved = 0;
    for (const id of NODE_IDS) {
      const expected = reference.get(id)!;
      const actual = shallow.get(id)!;
      moved = Math.max(moved, Math.hypot(actual[0] - expected[0], actual[1] - expected[1]));
    }
    expect(moved).toBeGreaterThan(1);
  });
});
