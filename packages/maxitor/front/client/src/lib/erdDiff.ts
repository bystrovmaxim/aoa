// src/lib/erdDiff.ts
/**
 * The ERD of two versions (spec 038, FR-022 – FR-026; research R10, R11): the union of A's and B's tables,
 * rows and lines, each marked with what the comparison says happened to it. The ERD's things are the graph's
 * own elements by the protocol's ids — a table is its ``Entity`` node; a scalar row is its ``EntityField`` node
 * ``<entity>:<field>`` with its ``entity_field`` edge; a relation's row and its line are one ``entity_relation``
 * edge ``<entity>|entity_relation|<field>`` (#285) — so no ERD knowledge reaches the server.
 */

import type { CompareResult, DiffStatus } from "@/api/compare";
import { drawnOn, type Side } from "@/lib/half";
import type { ErdEntity, ErdField, ErdRelation } from "@/lib/buildDotSource";

/** One domain's slice of the ERD, as ``list-entities`` gives it. */
export type ErdSlice = { entities?: ErdEntity[]; relations?: ErdRelation[]; groups?: unknown[] };

/** The tables, rows and lines the diagram draws in each status, each element once; on the map, its nodes and links. */
export type DiagramCounts = { added: number; removed: number; changed: number };

/** Which of two statuses says more: a row is as marked as the most marked of its parts. */
const WEIGHT: Record<DiffStatus, number> = { unchanged: 0, changed: 1, added: 2, removed: 2 };

function strongest(...statuses: (DiffStatus | undefined)[]): DiffStatus {
  return statuses.reduce<DiffStatus>((best, status) => (status && WEIGHT[status] > WEIGHT[best] ? status : best), "unchanged");
}

/** A relation's identity on the ERD: its table and its field, or — a line without a field — its two ends and kind. */
export function relationKey(relation: ErdRelation): string {
  return relation.source_field ? `${relation.source}|${relation.source_field}` : `${relation.source}|${relation.relationship_kind ?? ""}|${relation.target}`;
}

/** ``list`` with each item told what A held there and where, so that a half can stand them as A had them (spec 044). */
function remembered<T>(list: readonly T[]): Map<T, { was: T; wasAt: number }> {
  return new Map(list.map((was, wasAt) => [was, { was, wasAt }]));
}

/** A table's rows of both versions: B's in B's order, then the rows only A had; a row whose type changed keeps A's. */
function mergedFields(older: readonly ErdField[], newer: readonly ErdField[]): ErdField[] {
  const before = new Map(older.map((field) => [field.name, field]));
  const place = remembered(older);
  const now = new Set(newer.map((field) => field.name));
  return [
    ...newer.map((field) => {
      const was = before.get(field.name);
      if (!was) return field;
      const kept = { ...field, ...place.get(was) };
      return (was.type ?? "") !== (field.type ?? "") ? { ...kept, previous_type: was.type ?? "" } : kept;
    }),
    ...older.filter((field) => !now.has(field.name)).map((field) => ({ ...field, ...place.get(field) })),
  ];
}

/** The union of two lists of lines: B's — a line that now points elsewhere keeping A's target —, then the lines only A had. */
export function mergeRelations(older: readonly ErdRelation[] = [], newer: readonly ErdRelation[] = []): ErdRelation[] {
  const before = new Map(older.map((relation) => [relationKey(relation), relation]));
  const now = new Set(newer.map(relationKey));
  const place = remembered(older);
  return [
    ...newer.map((relation) => {
      const was = before.get(relationKey(relation));
      if (!was) return relation;
      const kept = { ...relation, ...place.get(was) };
      return was.target !== relation.target ? { ...kept, previous_target: was.target } : kept;
    }),
    ...older.filter((relation) => !now.has(relationKey(relation))).map((relation) => ({ ...relation, ...place.get(relation) })),
  ];
}

/** The union of one domain's slice in A and in B: every table of either, each with the rows of both. */
export function mergeErdSlices(older: ErdSlice | undefined, newer: ErdSlice | undefined): ErdSlice {
  const before = new Map((older?.entities ?? []).map((entity) => [entity.id, entity]));
  const now = new Set((newer?.entities ?? []).map((entity) => entity.id));
  const place = remembered(older?.entities ?? []);
  const entities = [
    ...(newer?.entities ?? []).map((entity) => {
      const was = before.get(entity.id);
      return was ? { ...entity, ...place.get(was), fields: mergedFields(was.fields ?? [], entity.fields ?? []) } : entity;
    }),
    ...(older?.entities ?? []).filter((entity) => !now.has(entity.id)).map((entity) => ({ ...entity, ...place.get(entity), fields: mergedFields(entity.fields ?? [], []) })),
  ];
  return { ...(newer ?? older ?? {}), entities, relations: mergeRelations(older?.relations, newer?.relations) };
}

/** The status of a relation's line: its ``entity_relation`` edge, or a generalization's ``parent_entity`` edge either way. */
function relationStatus(relation: ErdRelation, compared: CompareResult): DiffStatus {
  if (relation.source_field) return compared.edges[`${relation.source}|entity_relation|${relation.source_field}`] ?? "unchanged";
  return compared.edges[`${relation.source}|parent_entity|${relation.target}`] ?? compared.edges[`${relation.target}|parent_entity|${relation.source}`] ?? "unchanged";
}

/** The tables whose domain differs between the versions: their ``domain`` edges changed, whatever their own properties did. */
function movedTables(compared: CompareResult): Set<string> {
  return new Set(Object.keys(compared.edges).flatMap((id) => {
    const at = id.indexOf("|domain|");
    return at > 0 ? [id.slice(0, at)] : [];
  }));
}

/** Every table, row and line of a merged slice marked with its status. */
export function markErd(slice: ErdSlice, compared: CompareResult): ErdSlice {
  const moved = movedTables(compared);
  const entities = (slice.entities ?? []).map((entity) => ({
    ...entity,
    // A table that stands in another domain changed, though its own properties did not (spec 043).
    diff: compared.nodes[entity.id] ?? (moved.has(entity.id) ? "changed" : "unchanged"),
    movedDomain: !compared.nodes[entity.id] && moved.has(entity.id),
    fields: (entity.fields ?? []).map((field) => ({
      ...field,
      diff: strongest(
        compared.nodes[`${entity.id}:${field.name}`],
        compared.edges[`${entity.id}|entity_field|${entity.id}:${field.name}`],
        compared.edges[`${entity.id}|entity_relation|${field.name}`],
      ),
    })),
  }));
  const relations = (slice.relations ?? []).map((relation) => ({ ...relation, diff: relationStatus(relation, compared) }));
  return { ...slice, entities, relations };
}

/**
 * The drawn diagram's counts: its tables, its rows and its lines, each element once — a relation's row and its
 * line are one, so a line with a field is counted by its row —, a row of a new table counted as added like it.
 */
export function diagramCounts(entities: readonly ErdEntity[], relations: readonly ErdRelation[]): DiagramCounts {
  const counts: DiagramCounts = { added: 0, removed: 0, changed: 0 };
  const count = (status: DiffStatus | undefined) => {
    if (status && status !== "unchanged") counts[status] += 1;
  };
  for (const entity of entities) {
    count(entity.diff);
    for (const field of entity.fields ?? []) count(field.diff);
  }
  for (const relation of relations) if (!relation.source_field) count(relation.diff);
  return counts;
}

/** Whether the counts say nothing changed: the diagram is then drawn as one version, nothing faded (FR-026). */
export function nothingChanged(counts: DiagramCounts): boolean {
  return counts.added + counts.removed + counts.changed === 0;
}

/** ``list`` in A's order. */
function inOlderOrder<T extends { wasAt?: number }>(list: readonly T[]): T[] {
  return [...list].sort((one, other) => (one.wasAt ?? 0) - (other.wasAt ?? 0));
}

/**
 * The part of a merged drawing that one version has, with its marks (spec 044, research R2): on A every table, row and
 * line stands as A had it and where A had it, so a half is laid out as One lays out that version.
 */
export function erdOfSide<T extends { entities: ErdEntity[]; relations?: ErdRelation[] }>(data: T, side: Side): T {
  const drawn = <E extends { diff?: DiffStatus }>(list: readonly E[]) => list.filter((each) => drawnOn(side, each.diff ?? "unchanged"));
  const entities = drawn(data.entities).map((entity) => {
    const fields = drawn(entity.fields ?? []);
    if (side === "b") return { ...entity, fields };
    return { ...entity, ...entity.was, diff: entity.diff, fields: inOlderOrder(fields).map((field) => ({ ...field, ...field.was, diff: field.diff })) };
  });
  const tables = new Set(entities.map((entity) => entity.id));
  const relations = drawn(data.relations ?? []).map((relation) => (side === "a" ? { ...relation, ...relation.was, diff: relation.diff } : relation));
  const ordered = side === "a" ? { entities: inOlderOrder(entities), relations: inOlderOrder(relations) } : { entities, relations };
  return { ...data, entities: ordered.entities, relations: ordered.relations.filter((relation) => tables.has(relation.source) && tables.has(relation.target)) };
}

/** The same drawing with every mark taken off, as One draws it. */
export function unmarked<T extends { entities: ErdEntity[]; relations: ErdRelation[] }>(data: T): T {
  return {
    ...data,
    entities: data.entities.map(({ diff: _diff, ...entity }) => ({ ...entity, fields: (entity.fields ?? []).map(({ diff: _field, previous_type: _type, ...field }) => field) })),
    relations: data.relations.map(({ diff: _diff, previous_target: _target, ...relation }) => relation),
  };
}
