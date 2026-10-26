// src/components/diagrams/FullGraphViewer/forceLayout.ts
/**
 * The full graph's layout, computed by the same `D3ForceLayout` of `@antv/layout` G6 would run.
 *
 * Only the worker and the unit tests import this module: the viewer itself must not, or the
 * layout code and `@antv/layout` would enter the chunk every view loads (research R2).
 *
 * The options are one explicit nested object built from ``LAYOUT_SETTINGS`` — never a shallow
 * spread, which would drop ``center.strength`` and leave d3's default of 1 (research R4).
 */

import { D3ForceLayout } from "@antv/layout";

import { LAYOUT_SETTINGS } from "./layoutSettings";

/** One layout request, structured-clonable so it can cross a worker boundary. */
export type LayoutRequest = {
  nodes: string[];
  edges: [string, string][];
  nodeVisualPx: number;
  width: number;
  height: number;
};

/** The worker's answer: the position of every node, or why there is none. */
export type LayoutResponse =
  | { ok: true; positions: Record<string, [number, number]>; ms: number }
  | { ok: false; error: string };

type D3Node = { id?: string | number; x?: number; y?: number };

/**
 * Check that every requested node has a finite position, and return the map.
 *
 * Throws when a node is missing or a coordinate is not a finite number, so a broken layout
 * never reaches the graph.
 */
export function validatePositions(
  positions: Record<string, [number, number]>,
  nodeIds: string[],
): Record<string, [number, number]> {
  for (const id of nodeIds) {
    const position = positions[id];
    if (
      !Array.isArray(position) ||
      position.length !== 2 ||
      !Number.isFinite(position[0]) ||
      !Number.isFinite(position[1])
    ) {
      throw new Error(`the layout has no finite position for ${id}`);
    }
  }
  return positions;
}

/**
 * Run the layout exactly as G6 does — ``execute``, ``stop``, ``tick`` — and return the positions.
 *
 * The options are the ones G6's ``initGraphLayout`` would merge from today's viewer, given as
 * one object so no merge can drop a field.
 */
export function computeForceLayout(request: LayoutRequest): Record<string, [number, number]> {
  const { nodeVisualPx, width, height } = request;
  const options = {
    nodeSize: nodeVisualPx,
    width,
    height,
    center: { x: width / 2, y: height / 2, z: 0, strength: LAYOUT_SETTINGS.centerStrength },
    link: { distance: LAYOUT_SETTINGS.linkDistance, strength: LAYOUT_SETTINGS.linkStrength },
    manyBody: { ...LAYOUT_SETTINGS.manyBody },
    collide: {
      radius: nodeVisualPx * 0.5 + LAYOUT_SETTINGS.collide.radiusOffset,
      strength: LAYOUT_SETTINGS.collide.strength,
      iterations: LAYOUT_SETTINGS.collide.iterations,
    },
    alphaDecay: LAYOUT_SETTINGS.alphaDecay,
    alphaMin: LAYOUT_SETTINGS.alphaMin,
    velocityDecay: LAYOUT_SETTINGS.velocityDecay,
  };
  const layout = new D3ForceLayout(options as never);
  const data = {
    nodes: request.nodes.map((id) => ({ id })),
    edges: request.edges.map(([source, target]) => ({ source, target })),
  };
  // G6 does not await execute either: it runs the simulation into existence, stops the timer,
  // and steps it by hand (research R2).
  void layout.execute(data as never);
  layout.stop();
  layout.tick(LAYOUT_SETTINGS.iterations);

  const positions: Record<string, [number, number]> = {};
  for (const node of layout.nodes() as D3Node[]) {
    if (node.id === undefined) continue;
    positions[String(node.id)] = [Number(node.x), Number(node.y)];
  }
  return validatePositions(positions, request.nodes);
}
