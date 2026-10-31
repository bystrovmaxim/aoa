// src/lib/erdDiff.ts
/**
 * The ERD of two versions (spec 038, FR-022 – FR-026; research R10, R11): the union of A's and B's tables,
 * rows and lines, each marked with what the comparison says happened to it. The ERD's things are the graph's
 * own elements by the protocol's ids — a table is its ``Entity`` node; a scalar row is its ``EntityField`` node
 * ``<entity>:<field>`` with its ``entity_field`` edge; a relation's row and its line are one ``entity_relation``
 * edge ``<entity>|entity_relation|<field>`` (#285) — so no ERD knowledge reaches the server.
 */

import type { CompareResult, DiffStatus } from "@/api/compare";
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

/** A table's rows of both versions: B's in B's order, then the rows only A had; a row whose type changed keeps A's. */
function mergedFields(older: readonly ErdField[], newer: readonly ErdField[]): ErdField[] {
  const before = new Map(older.map((field) => [field.name, field]));
  const now = new Set(newer.map((field) => field.name));
  return [
    ...newer.map((field) => {
      const was = before.get(field.name);
      return was && (was.type ?? "") !== (field.type ?? "") ? { ...field, previous_type: was.type ?? "" } : field;
    }),
    ...older.filter((field) => !now.has(field.name)),
  ];
}

/** The union of two lists of lines: B's — a line that now points elsewhere keeping A's target —, then the lines only A had. */
export function mergeRelations(older: readonly ErdRelation[] = [], newer: readonly ErdRelation[] = []): ErdRelation[] {
  const before = new Map(older.map((relation) => [relationKey(relation), relation]));
  const now = new Set(newer.map(relationKey));
  return [
    ...newer.map((relation) => {
      const was = before.get(relationKey(relation));
      return was && was.target !== relation.target ? { ...relation, previous_target: was.target } : relation;
    }),
    ...older.filter((relation) => !now.has(relationKey(relation))),
  ];
}

/** The union of one domain's slice in A and in B: every table of either, each with the rows of both. */
export function mergeErdSlices(older: ErdSlice | undefined, newer: ErdSlice | undefined): ErdSlice {
  const before = new Map((older?.entities ?? []).map((entity) => [entity.id, entity]));
  const now = new Set((newer?.entities ?? []).map((entity) => entity.id));
  const entities = [
    ...(newer?.entities ?? []).map((entity) => {
      const was = before.get(entity.id);
      return was ? { ...entity, fields: mergedFields(was.fields ?? [], entity.fields ?? []) } : entity;
    }),
    ...(older?.entities ?? []).filter((entity) => !now.has(entity.id)),
  ];
  return { ...(newer ?? older ?? {}), entities, relations: mergeRelations(older?.relations, newer?.relations) };
}

/** The status of a relation's line: its ``entity_relation`` edge, or a generalization's ``parent_entity`` edge either way. */
function relationStatus(relation: ErdRelation, compared: CompareResult): DiffStatus {
  if (relation.source_field) return compared.edges[`${relation.source}|entity_relation|${relation.source_field}`] ?? "unchanged";
  return compared.edges[`${relation.source}|parent_entity|${relation.target}`] ?? compared.edges[`${relation.target}|parent_entity|${relation.source}`] ?? "unchanged";
}

/** Every table, row and line of a merged slice marked with its status. */
export function markErd(slice: ErdSlice, compared: CompareResult): ErdSlice {
  const entities = (slice.entities ?? []).map((entity) => ({
    ...entity,
    diff: compared.nodes[entity.id] ?? "unchanged",
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

/** The same drawing with every mark taken off, as One draws it. */
export function unmarked<T extends { entities: ErdEntity[]; relations: ErdRelation[] }>(data: T): T {
  return {
    ...data,
    entities: data.entities.map(({ diff: _diff, ...entity }) => ({ ...entity, fields: (entity.fields ?? []).map(({ diff: _field, previous_type: _type, ...field }) => field) })),
    relations: data.relations.map(({ diff: _diff, previous_target: _target, ...relation }) => relation),
  };
}
