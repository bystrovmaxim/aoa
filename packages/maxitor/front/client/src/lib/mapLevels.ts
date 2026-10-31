// src/lib/mapLevels.ts
/**
 * How far zoom has revealed each level of the map (spec 040, FR-001 – FR-003). The level follows the zoom alone, so
 * everyone at one zoom sees one level on any screen, and it reveals across a band, so things fade rather than pop.
 */

/** The screen the bands are measured on: a phone and a wide monitor at one zoom read the same width of map from it. */
export const LEVEL_SCREEN_PX = 1400;

/** Between these widths of the map, entities and operations fade in. */
export const LEVEL_TWO_BAND: readonly [number, number] = [7600, 5200];

/** Between these widths, fields, states and other parts fade in. */
export const LEVEL_THREE_BAND: readonly [number, number] = [3000, 2000];

/** The width of map the levels read at a zoom, a camera's ratio of map units to pixels. */
export function widthAtRatio(ratio: number): number {
  return ratio * LEVEL_SCREEN_PX;
}

/** The zoom a map opens at: fitted, and one level closer with no domains to fold. */
export function openingRatio(fit: number, areas: number): number {
  return areas > 1 ? fit : Math.min(fit, LEVEL_TWO_BAND[1] / LEVEL_SCREEN_PX);
}

/** How far a level is revealed at ``width``: 0 at the band's start, 1 at its end, eased. */
export function revealOf(width: number, [from, to]: readonly [number, number]): number {
  const t = Math.min(1, Math.max(0, (from - width) / (from - to)));
  return t * t * (3 - 2 * t);
}

/** Which level detail is needed from at ``width``: 1 needs none. */
export function levelAt(width: number): 1 | 2 | 3 {
  if (width >= LEVEL_TWO_BAND[0]) return 1;
  return width >= LEVEL_THREE_BAND[0] ? 2 : 3;
}
