// src/components/diagrams/FullGraphViewer/layoutSettings.ts
/**
 * The d3-force settings that are in effect today, in one place.
 *
 * The viewer's fallback path (G6's own layout) and the worker both build their options from
 * this object, and the fingerprint reads it: a change here changes every remembered arrangement.
 *
 * `linkDistance` and `linkStrength` are constants although today's viewer passes functions:
 * d3 hands those functions node objects rather than ids, so their lookup never matched and
 * every edge got the "same type" values 72 and 0.82 (research R3). Writing the result of that
 * rule down as a constant is the same picture, without the dead lookup.
 */

export type LayoutSettings = {
  iterations: number;
  linkDistance: number;
  linkStrength: number;
  manyBody: { strength: number; distanceMax: number };
  collide: { radiusOffset: number; strength: number; iterations: number };
  centerStrength: number;
  alphaDecay: number;
  alphaMin: number;
  velocityDecay: number;
};

export const LAYOUT_SETTINGS: LayoutSettings = {
  iterations: 220,
  linkDistance: 72,
  linkStrength: 0.82,
  manyBody: { strength: -360, distanceMax: 1200 },
  collide: { radiusOffset: 7, strength: 0.95, iterations: 4 },
  centerStrength: 0.012,
  alphaDecay: 0.012,
  alphaMin: 0.0015,
  velocityDecay: 0.42,
};

/**
 * Today's G6 `layout` option, built from ``LAYOUT_SETTINGS`` — the page's fallback path.
 *
 * It has the shape the viewer used before the worker existed; G6 adds ``nodeSize``, ``width``,
 * ``height`` and the centre point itself when it merges it (research R3, R4).
 */
export function g6LayoutOptions(nodeVisualPx: number): Record<string, unknown> {
  return {
    type: "d3-force",
    iterations: LAYOUT_SETTINGS.iterations,
    animation: false,
    link: {
      distance: LAYOUT_SETTINGS.linkDistance,
      strength: LAYOUT_SETTINGS.linkStrength,
    },
    manyBody: { ...LAYOUT_SETTINGS.manyBody },
    collide: {
      radius: nodeVisualPx * 0.5 + LAYOUT_SETTINGS.collide.radiusOffset,
      strength: LAYOUT_SETTINGS.collide.strength,
      iterations: LAYOUT_SETTINGS.collide.iterations,
    },
    center: { strength: LAYOUT_SETTINGS.centerStrength },
    alphaDecay: LAYOUT_SETTINGS.alphaDecay,
    alphaMin: LAYOUT_SETTINGS.alphaMin,
    velocityDecay: LAYOUT_SETTINGS.velocityDecay,
  };
}
