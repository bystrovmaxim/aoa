// src/lib/erdFilterPresence.ts
/**
 * Which filter rows a diagram has, and which of them are on screen (spec 038). The rows come from the diagram's base —
 * the drawing that is open, of the version or the two versions that are open, before any filter: a filter never adds
 * or removes another filter's rows. Under the filters a row may have nothing of it left on screen; it is then shown
 * dimmed, and whether it is on stays the user's.
 */

import { erdGlance, type ErdDiff, type ErdEntity } from "@/lib/buildDotSource";
import { entityKindOf } from "@/lib/erdKindFilter";

/** The kinds of change, in the order the filter lists them. */
export const CHANGE_ORDER: readonly ErdDiff[] = ["added", "removed", "changed", "unchanged"];

/** The kinds of change the base has, in the filter's order; none when nothing on it changed (or one version is drawn). */
export function changesOnDiagram(entities: readonly ErdEntity[]): ErdDiff[] {
  const present = new Set(entities.filter((entity) => entity.diff !== undefined).map(erdGlance));
  if (![...present].some((status) => status !== "unchanged")) return [];
  return CHANGE_ORDER.filter((status) => present.has(status));
}

/** What the screen shows of each filter: the tables drawn, less those of a kind of change switched off. */
export type OnScreen = { ids: ReadonlySet<string>; domains: ReadonlySet<string | null>; kinds: ReadonlySet<string>; changes: ReadonlySet<ErdDiff> };

/** ``drawn`` — the tables left by the domain and kind filters, 1-hop neighbours included — read as each filter sees it. */
export function onScreen(drawn: readonly ErdEntity[], offChanges: ReadonlySet<string>, domainOf: (entity: ErdEntity) => string | null): OnScreen {
  const shown = drawn.filter((entity) => !(entity.diff !== undefined && offChanges.has(erdGlance(entity))));
  return {
    ids: new Set(shown.map((entity) => entity.id)),
    domains: new Set(shown.map(domainOf)),
    kinds: new Set(shown.map(entityKindOf)),
    changes: new Set(shown.filter((entity) => entity.diff !== undefined).map(erdGlance)),
  };
}
