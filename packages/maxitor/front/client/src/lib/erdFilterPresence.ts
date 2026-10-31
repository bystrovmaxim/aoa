// src/lib/erdFilterPresence.ts
/**
 * Which filter rows a diagram has, and which of them are on screen (spec 038). The rows come from the diagram's base —
 * the drawing that is open, of the version or the two versions that are open, before any filter: a filter never adds
 * or removes another filter's rows. Under the filters a row may have nothing of it left on screen; it is then shown
 * dimmed, and whether it is on stays the user's.
 */

import { erdGlance, type ErdDiff, type ErdEntity } from "@/lib/buildDotSource";
import type { ErdGraphPayload } from "@/lib/buildDotSource";
import { entityKindOf, pruneGraphToEntities } from "@/lib/erdKindFilter";

/** The kinds of change, in the order the filter lists them. */
export const CHANGE_ORDER: readonly ErdDiff[] = ["added", "removed", "changed", "unchanged"];

/** A legend disk for a kind of change: the status colour with its sign in white. */
export function statusDiskUri(fill: string, sign: string): string {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="${fill}"/>` +
    (sign ? `<text x="12" y="16.5" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="700" fill="#fff">${sign}</text>` : "") +
    `</svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

/** The kinds of change the base has, in the filter's order; none when nothing on it changed (or one version is drawn). */
export function changesOnDiagram(entities: readonly ErdEntity[]): ErdDiff[] {
  const present = new Set(entities.filter((entity) => entity.diff !== undefined).map(erdGlance));
  if (![...present].some((status) => status !== "unchanged")) return [];
  return CHANGE_ORDER.filter((status) => present.has(status));
}

/** Hide the tables of the kinds of change switched off — as a domain or a kind switched off hides its tables. */
export function filterGraphByChanges(data: ErdGraphPayload, offChanges: ReadonlySet<string>): ErdGraphPayload {
  if (offChanges.size === 0) return data;
  return pruneGraphToEntities(data, (entity) => entity.diff === undefined || !offChanges.has(erdGlance(entity)));
}

/**
 * 1-hop over the filters: the tables the filters left, and every table of the base one line away from them — even one
 * a filter hid —, with the lines and containers between them.
 */
export function withOneHop(kept: ErdGraphPayload, base: ErdGraphPayload): ErdGraphPayload {
  const ids = new Set(kept.entities.map((entity) => entity.id));
  const reach = new Set(ids);
  for (const relation of base.relations ?? []) {
    if (ids.has(relation.source)) reach.add(relation.target);
    if (ids.has(relation.target)) reach.add(relation.source);
  }
  return pruneGraphToEntities(base, (entity) => reach.has(entity.id));
}

/** The domains of the tabs switched on: only these own the tables a diagram draws without 1-hop. */
export function domainsOn(domainQualifiers: Record<string, string>, tabsOn: ReadonlySet<string>): Set<string> {
  return new Set(Object.entries(domainQualifiers).filter(([tab]) => tabsOn.has(tab)).map(([, qual]) => qual.trim()));
}

/**
 * What a diagram draws: the tables the filters left that belong to a domain switched on — a slice also carries its
 * 1-hop neighbours, and a neighbour from a domain switched off is not that domain's way back onto the screen —, and
 * with 1-hop on, the base's tables one line away from those.
 */
export function tablesToDraw(
  filtered: ErdGraphPayload,
  base: ErdGraphPayload,
  domains: ReadonlySet<string>,
  domainOf: (entity: ErdEntity) => string | null,
  includeOneHop: boolean,
): ErdGraphPayload {
  const own = pruneGraphToEntities(filtered, (entity) => domains.has(domainOf(entity) ?? ""));
  return includeOneHop ? withOneHop(own, base) : own;
}

/** What the screen shows of each filter. */
export type OnScreen = { ids: ReadonlySet<string>; domains: ReadonlySet<string | null>; kinds: ReadonlySet<string>; changes: ReadonlySet<ErdDiff> };

/** ``shown`` — the tables every filter left, 1-hop neighbours included — read as each filter sees it. */
export function onScreen(shown: readonly ErdEntity[], domainOf: (entity: ErdEntity) => string | null): OnScreen {
  return {
    ids: new Set(shown.map((entity) => entity.id)),
    domains: new Set(shown.map(domainOf)),
    kinds: new Set(shown.map(entityKindOf)),
    changes: new Set(shown.filter((entity) => entity.diff !== undefined).map(erdGlance)),
  };
}
