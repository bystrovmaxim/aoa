// src/lib/mapLevels.ts
/**
 * How far zoom has revealed each level of the map (spec 040, FR-001 – FR-003). The level follows the width of the map
 * in view alone, so everyone at one zoom sees one level, and it reveals across a band, so things fade rather than pop.
 */

/** Between these widths of the map in view, entities and operations fade in. */
export const LEVEL_TWO_BAND: readonly [number, number] = [7600, 5200];

/** Between these widths, fields, states and other parts fade in. */
export const LEVEL_THREE_BAND: readonly [number, number] = [3000, 2000];

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
