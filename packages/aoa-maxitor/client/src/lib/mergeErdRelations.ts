// src/lib/mergeErdRelations.ts
/**
 * Lines of the merged multi-domain ERD.
 *
 * Each domain slice only knows the lines among its own tables, so a line whose two ends were brought
 * by two different slices exists in none of them. The server also answers one request-wide list —
 * every line between two tables of the whole request — and the merged view draws that list, kept to
 * the tables actually on screen. Container links (``specialization``) still come from the slices,
 * because they point at a container, not at a table.
 */

import type { ErdRelation } from "@/lib/buildDotSource";

const SPECIALIZATION = "specialization";

/** Lines to draw: request-wide lines between two tables on screen, plus the slices' container links. */
export function mergeRelationsOnScreen(
  requestRelations: readonly ErdRelation[] | undefined,
  sliceRelations: readonly ErdRelation[],
  entityIdsOnScreen: ReadonlySet<string>,
): ErdRelation[] {
  const lines = requestRelations ?? sliceRelations.filter((r) => r.relationship_kind !== SPECIALIZATION);
  const containers = sliceRelations.filter((r) => r.relationship_kind === SPECIALIZATION);
  const seen = new Set<string>();
  const out: ErdRelation[] = [];
  for (const r of [...lines, ...containers]) {
    const isContainer = r.relationship_kind === SPECIALIZATION;
    if (!entityIdsOnScreen.has(r.source)) continue;
    if (!isContainer && !entityIdsOnScreen.has(r.target)) continue;
    const key = `${r.source}\u001f${r.target}\u001f${r.label ?? ""}\u001f${r.relationship_kind ?? ""}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(r);
  }
  return out;
}
