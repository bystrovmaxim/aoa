// src/lib/erdKindFilter.ts
/**
 * ERD visibility by entity kind, and the one pruning rule every ERD filter shares.
 *
 * A table is on screen only when every filter keeps it (its domain or 1-hop qualifier, and its kind).
 * Whatever hides a table, the drawing is pruned the same way: no line ends at a hidden table, a
 * container keeps only the members on screen and disappears below two, and a line into a container
 * stays only while the container does. Hiding a table never hides the neighbours it brought.
 */

import type { ErdEntity, ErdGraphPayload } from "@/lib/buildDotSource";

/** The kind a table is filtered under: its word, or ``unknown`` when the graph states none. */
export function entityKindOf(entity: ErdEntity): string {
  const kind = typeof entity.entity_kind === "string" ? entity.entity_kind.trim() : "";
  return kind || "unknown";
}

/** Keep the tables ``keep`` accepts, and prune lines and containers to them. */
export function pruneGraphToEntities(data: ErdGraphPayload, keep: (entity: ErdEntity) => boolean): ErdGraphPayload {
  const entities = (data.entities ?? []).filter(keep);
  const ids = new Set(entities.map((e) => e.id));
  // A group survives only with the members that survived, and a container around one remaining
  // table would claim a choice that is not on screen.
  const groups = (data.groups ?? [])
    .map((g) => ({ ...g, members: g.members.filter((m) => ids.has(m)) }))
    .filter((g) => g.members.length > 1);
  const keptGroups = new Set(groups.map((g) => g.group_id));
  const relations = (data.relations ?? []).filter((r) => {
    // A line into a container is kept while the container is, and points at no entity of its own.
    if (r.relationship_kind === "specialization") return keptGroups.has(r.target) && ids.has(r.source);
    return ids.has(r.source) && ids.has(r.target);
  });
  return { entities, relations, groups };
}

/** Hide the tables of the kinds switched off. */
export function filterGraphByKinds(data: ErdGraphPayload, disabledKinds: ReadonlySet<string>): ErdGraphPayload {
  if (disabledKinds.size === 0) return data;
  return pruneGraphToEntities(data, (e) => !disabledKinds.has(entityKindOf(e)));
}

/**
 * The kinds a filter offers for a diagram: those of the named list (in its order) that at least one of
 * ``entities`` has — the tables the diagram shows before kinds are filtered, so a kind switched off stays
 * listed (spec 029, FR-044), as the domain filter lists only the diagram's domains.
 */
export function kindsOnDiagram<T extends { entity_kind: string }>(kinds: readonly T[], entities: readonly ErdEntity[]): T[] {
  const present = new Set(entities.map(entityKindOf));
  return kinds.filter((kind) => present.has(kind.entity_kind));
}
