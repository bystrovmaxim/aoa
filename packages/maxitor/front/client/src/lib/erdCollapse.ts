// src/lib/erdCollapse.ts
/**
 * Which rows a collapsed table keeps (spec 043, FR-021, FR-022): its keys, any row a line belongs to, and in Diff what
 * changed. Whether a table is collapsed comes from two page settings: one for all tables, and the tables that differ from it,
 * so that the address stays short however large the diagram is (FR-027).
 */
import type { ErdEntity, ErdFold, ErdRelation } from "@/lib/buildDotSource";

/** The names of the rows of ``entity`` that have a line in ``relations``. */
function rowsWithLines(entity: ErdEntity, relations: readonly ErdRelation[]): Set<string> {
  const names = new Set<string>();
  for (const relation of relations) {
    if (relation.source === entity.id && relation.source_field) names.add(relation.source_field);
    if (relation.target === entity.id && relation.target_field) names.add(relation.target_field);
  }
  return names;
}

/** The rows a collapse of ``entity`` hides. */
export function rowsToHide(entity: ErdEntity, relations: readonly ErdRelation[]): Set<number> {
  const lined = rowsWithLines(entity, relations);
  const hidden = new Set<number>();
  (entity.fields ?? []).forEach((field, row) => {
    const marked = field.diff !== undefined && field.diff !== "unchanged";
    if (!field.primary_key && !field.foreign_key && !marked && !lined.has(field.name)) hidden.add(row);
  });
  return hidden;
}

/** Whether a table is collapsed: the switch, turned over for the tables it excepts. */
export function isCollapsed(id: string, all: boolean, except: ReadonlySet<string>): boolean {
  return all !== except.has(id);
}

/** Every table's fold. */
export function erdFolds(entities: readonly ErdEntity[], relations: readonly ErdRelation[], all: boolean, except: ReadonlySet<string>): ReadonlyMap<string, ErdFold> {
  return new Map(entities.map((entity) => [entity.id, { hidden: rowsToHide(entity, relations), collapsed: isCollapsed(entity.id, all, except) }]));
}
