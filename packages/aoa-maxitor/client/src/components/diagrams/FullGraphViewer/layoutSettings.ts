// src/components/diagrams/FullGraphViewer/layoutSettings.ts
/**
 * The d3-force settings that are in effect today, in one place.
 *
 * `computeForceLayout` builds its options from this object, and the fingerprint reads it: a change
 * here changes every remembered arrangement.
 *
 * `linkDistance` and `linkStrength` are constants although today's viewer passes functions:
 * d3 hands those functions node objects rather than ids, so their lookup never matched and
 * every edge got the "same type" values 72 and 0.82 (research R3). Writing the result of that
 * rule down as a constant is the same picture, without the dead lookup.
 */

/**
 * Version of the layout code. Raise it with any change that can move a node — a setting, the
 * starting spiral, the centre — so arrangements remembered by older code are never replayed.
 */
export const LAYOUT_VERSION = 2;

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
