// src/components/diagrams/FullGraphViewer/forceLayout.ts
/**
 * The full graph's layout, computed by Maxitor with the `D3ForceLayout` of `@antv/layout`, so the
 * same graph gets bit-identical positions in every browser and on every screen size.
 *
 * The viewer imports this module lazily, together with G6, so the layout code never enters the
 * chunk every view loads (spec 026, research R2). Three things make the result the same
 * everywhere (spec 028, research R2): the centre is the origin, never the canvas or window
 * middle; every node starts where ``initialPositions`` puts it, so `d3-force-3d` never reaches
 * its own `Math.cos` / `Math.sin` spiral; and nodes enter in the order of the server's answer.
 *
 * The options are one explicit nested object built from ``LAYOUT_SETTINGS`` — never a shallow
 * spread, which would drop ``center.strength`` and leave d3's default of 1 (spec 026, research R4).
 */

import { D3ForceLayout } from "@antv/layout";

import { initialPositions } from "./initialPositions";
import { LAYOUT_SETTINGS } from "./layoutSettings";

/** One layout request; no canvas size enters it, so the screen cannot change the result. */
export type LayoutRequest = {
  nodes: string[];
  edges: [string, string][];
  nodeVisualPx: number;
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
 * Run the layout the way G6 does — ``execute``, ``stop``, ``tick`` — around the origin, from the
 * starting spiral, and return the positions.
 */
export function computeForceLayout(request: LayoutRequest): Record<string, [number, number]> {
  const { nodeVisualPx } = request;
  const options = {
    nodeSize: nodeVisualPx,
    // `D3ForceLayout` always sets the centre to half its viewport, overriding ``center.x`` /
    // ``center.y``, and without a size it takes the browser window's. A fixed size of zero puts
    // the centre at the origin on every screen.
    width: 0,
    height: 0,
    center: { x: 0, y: 0, z: 0, strength: LAYOUT_SETTINGS.centerStrength },
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
  const start = initialPositions(request.nodes);
  const data = {
    nodes: request.nodes.map((id) => ({ id, x: start[id][0], y: start[id][1] })),
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
