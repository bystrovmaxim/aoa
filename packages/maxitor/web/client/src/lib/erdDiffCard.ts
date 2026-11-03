// src/lib/erdDiffCard.ts
/**
 * Which graph elements a table or a row of the ERD stands for in Diff (spec 038, FR-028): a marked table's header is its
 * ``Entity`` node; a marked row is its ``EntityField`` node with its ``entity_field`` edge, or — a relation's row —
 * its ``entity_relation`` edge. The card asks the server for each and shows what changed in those it has.
 */
import type { ChangedPart } from "@/api/compare";
import type { ErdDiff, ErdEntity, ErdField, ErdRelation } from "@/lib/buildDotSource";
import type { GraphvizChange } from "@/lib/useGraphvizChangeStepping";
import { relationKey } from "@/lib/erdDiff";

/** The colours and signs of the three marks, the ERD's own. */
export const MARK_LOOK = { added: { colour: "#16a34a", sign: "+" }, removed: { colour: "#dc2626", sign: "−" }, changed: { colour: "#d97706", sign: "~" } } as const;

/** One graph element a card reads. */
export type CardElement = { kind: "node" | "edge"; id: string };

/** What a card reads changes of: its title, its status, and the elements. */
export type CardTarget = {
  title: string;
  status: Exclude<ErdDiff, "unchanged">;
  elements: CardElement[];
  /** What changed inside an element whose diagram does not draw its parts (spec 041, FR-012). */
  parts?: readonly ChangedPart[];
  /** A change no property of the element shows, in words. */
  note?: string;
};

/** What a table that changed domain says: its properties are the same. */
export const MOVED_DOMAIN = "Moved to another domain.";

/** What a lifecycle's row says when its states or transitions changed: they are listed under it. */
export const LIFECYCLE_CHANGED = "Its lifecycle changed.";

/** What a table says when only its rows changed. */
export const FIELDS_CHANGED = "Its fields changed.";

/** One change of the drawn ERD. */
export type ErdChange = GraphvizChange;

type Marked = Exclude<ErdDiff, "unchanged">;

function marked(status: ErdDiff | undefined): status is Marked {
  return status !== undefined && status !== "unchanged";
}

/** The last part of a dotted id: what a line's ends are called on its row in a list. */
function shortName(id: string): string {
  return id.split(".").pop() ?? id;
}

/**
 * Every change the ERD draws, in the order it draws them: each table, then its rows, then the lines that have no row,
 * each element once, as ``diagramCounts`` counts them.
 */
export function erdChanges(entities: readonly ErdEntity[], relations: readonly ErdRelation[]): ErdChange[] {
  const changes: ErdChange[] = [];
  entities.forEach((entity, table) => {
    const title = entity.label || entity.id;
    if (marked(entity.diff)) changes.push({ key: entity.id, title, detail: "Table", status: entity.diff, group: title, cell: `a_hd${table}`, card: { title, status: entity.diff, elements: [{ kind: "node", id: entity.id }], ...tableInside(entity) } });
    (entity.fields ?? []).forEach((field, row) => {
      if (marked(field.diff)) changes.push({ key: `${entity.id}:${field.name}`, title: field.name, detail: field.type ?? "", status: field.diff, group: title, cell: `a_fn${table}_${row}`, card: rowCard(entity.id, field, field.diff) });
    });
  });
  relations.forEach((relation, line) => {
    if (!relation.source_field && marked(relation.diff)) changes.push({ key: relationKey(relation), title: `${shortName(relation.source)} → ${shortName(relation.target)}`, detail: relation.relationship_kind ?? "", status: relation.diff, group: "Lines", cell: `re${line}`, card: null });
  });
  return changes;
}

/** What a table's card adds to its own properties: that it moved, or the lifecycle changes that changed it. */
export function tableInside(entity: ErdEntity): Pick<CardTarget, "note" | "parts"> {
  if (entity.movedDomain) return { note: MOVED_DOMAIN };
  const parts = (entity.fields ?? []).flatMap((field) => field.lifecycle_parts ?? []);
  return parts.length ? { note: LIFECYCLE_CHANGED, parts } : {};
}

/** A marked row's card: its elements, and for a lifecycle's row the states and transitions that changed. */
export function rowCard(entityId: string, field: ErdField, status: Marked): CardTarget {
  const inside = field.lifecycle_parts?.length ? { note: LIFECYCLE_CHANGED, parts: field.lifecycle_parts } : {};
  return { title: field.name, status, elements: rowElements(entityId, field.name), ...inside };
}

/** The elements a row of ``entity`` stands for. */
export function rowElements(entityId: string, field: string): CardElement[] {
  return [
    { kind: "node", id: `${entityId}:${field}` },
    { kind: "edge", id: `${entityId}|entity_field|${entityId}:${field}` },
    { kind: "edge", id: `${entityId}|entity_relation|${field}` },
  ];
}
