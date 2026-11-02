// src/lib/erdCard.ts
/** What a card says of a table or a row of the ERD, from what the diagram holds (spec 043, FR-004 – FR-006). */
import type { CardField, CardSubject } from "@/components/diagrams/ElementCard";
import type { ErdEntity, ErdField, ErdRelation } from "@/lib/buildDotSource";
import { FIELDS_CHANGED, MOVED_DOMAIN, rowElements, type CardTarget } from "@/lib/erdDiffCard";
import { tooltipOf } from "@/rooms/graphvizFocus";
import type { ElementRef } from "@/rooms/focusStore";

/** A row's cell id, without the ``a_`` Graphviz adds: ``fn<table>_<row>`` or ``ft<table>_<row>``. */
const ROW = /^f[nt](\d+)_(\d+)$/;

function keyWord(field: ErdField): CardField["key"] {
  return field.primary_key ? "PK" : field.foreign_key ? "FK" : undefined;
}

function marked<T>(status: T): status is Exclude<T, "unchanged" | undefined> {
  return status !== undefined && status !== "unchanged";
}

/** What a table's card says changed: the table itself, or something in it, which a table of no change of its own shows too. */
function tableChange(entity: ErdEntity, title: string): CardTarget | null {
  const status = marked(entity.diff) ? entity.diff : (entity.fields ?? []).some((field) => marked(field.diff)) ? "changed" : null;
  if (!status) return null;
  const note = entity.movedDomain ? MOVED_DOMAIN : marked(entity.diff) ? undefined : FIELDS_CHANGED;
  return { title, status, elements: [{ kind: "node", id: entity.id }], ...(note ? { note } : {}) };
}

/** How low a row may stand on screen and still be read or aimed at, in CSS px; a finger needs more than a pointer. */
export const ROW_READABLE_PX = 10;
export const ROW_TAPPABLE_PX = 20;

/** The table of a row too small to read or aim at: from afar a card tells the whole table (spec 043, FR-001a). */
export function fromAfar(ref: ElementRef, cell: Element | undefined, entities: readonly ErdEntity[], touch: boolean): ElementRef {
  const table = ref.kind === "row" ? ROW.exec(ref.id)?.[1] : undefined;
  const entity = table === undefined ? undefined : entities[Number(table)];
  const height = cell?.getBoundingClientRect().height ?? Infinity;
  return entity && height < (touch ? ROW_TAPPABLE_PX : ROW_READABLE_PX) ? { kind: "table", id: entity.id } : ref;
}

/** How many a line's end stands for. */
const ENDS: Readonly<Record<string, string>> = { one: "1", zero_one: "0..1", one_many: "1..*", zero_many: "0..*" };

/** A line's id: ``re<k>``, or ``rp<k>`` for where it pointed in A. */
const LINE = /^r[ep](\d+)$/;

function titleCase(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

/** The card of a line (spec 043, FR-011): what joins what, of which kind and how many, in the words of the model. */
function lineSubject(ref: ElementRef, entities: readonly ErdEntity[], relations: readonly ErdRelation[]): Omit<CardSubject, "at"> | null {
  const line = relations[Number(LINE.exec(ref.id)?.[1] ?? -1)];
  if (!line) return null;
  const name = (id: string) => entities.find((entity) => entity.id === id)?.label || id.split(".").pop() || id;
  const end = (id: string, field?: string | null) => (field ? `${name(id)}.${field}` : name(id));
  const title = `${end(line.source, line.source_field)} → ${end(line.target, line.target_field)}`;
  const counts = line.source_cardinality && line.target_cardinality ? ` · ${ENDS[line.source_cardinality] ?? line.source_cardinality} → ${ENDS[line.target_cardinality] ?? line.target_cardinality}` : "";
  return {
    key: `line:${ref.id}`,
    ref,
    title,
    detail: `${titleCase(line.relationship_kind ?? "association")}${counts}`,
    description: line.description,
    nodeId: null,
    change: marked(line.diff) ? { title, status: line.diff, elements: line.source_field ? [{ kind: "edge", id: `${line.source}|entity_relation|${line.source_field}` }] : [] } : null,
  };
}

/** What a hover on ``ref`` lights: the tables it joins to and its lines, which its card should leave in sight. */
export function litBy(ref: ElementRef, entities: readonly ErdEntity[], relations: readonly ErdRelation[]): { tables: string[]; lines: number[] } {
  if (ref.kind === "edge") {
    const index = Number(LINE.exec(ref.id)?.[1] ?? -1);
    const line = relations[index];
    return line ? { tables: [line.source, line.target], lines: [index] } : { tables: [], lines: [] };
  }
  const place = ref.kind === "row" ? ROW.exec(ref.id) : null;
  const entity = place ? entities[Number(place[1])] : entities.find((each) => each.id === ref.id);
  if (!entity) return { tables: [], lines: [] };
  const field = place ? entity.fields?.[Number(place[2])]?.name : undefined;
  const tables = new Set<string>();
  const lines: number[] = [];
  relations.forEach((line, index) => {
    const from = line.source === entity.id && (!place || line.source_field === field);
    const to = line.target === entity.id && (!place || line.target_field === field);
    if (!from && !to) return;
    lines.push(index);
    if (from) tables.add(line.target);
    if (to) tables.add(line.source);
  });
  tables.delete(entity.id);
  return { tables: [...tables], lines };
}

/** The subject of ``ref``, less its place; ``null`` when it is not a table, a row or a line of the drawing. */
export function erdSubject(ref: ElementRef, entities: readonly ErdEntity[], root: ParentNode, relations: readonly ErdRelation[] = []): Omit<CardSubject, "at"> | null {
  if (ref.kind === "edge") return lineSubject(ref, entities, relations);
  if (ref.kind === "table") {
    const entity = entities.find((each) => each.id === ref.id);
    if (!entity) return null;
    const title = entity.label || entity.id;
    return {
      key: `table:${entity.id}`,
      ref,
      title,
      detail: "",
      nodeId: entity.id,
      change: tableChange(entity, title),
      // In Diff what changed comes first: from afar this list is all a person reads (spec 043, FR-006a).
      fields: [...(entity.fields ?? [])]
        .sort((one, other) => Number(marked(other.diff)) - Number(marked(one.diff)))
        .map((field) => ({ name: field.name, type: field.type, key: keyWord(field), description: field.description, status: marked(field.diff) ? field.diff : undefined, previousType: field.previous_type, lifecycleId: field.lifecycle_id })),
      lifecycleIds: (entity.fields ?? []).flatMap((field) => field.lifecycle_id ?? []),
      copy: title,
    };
  }
  if (ref.kind !== "row") return null;
  const place = ROW.exec(ref.id);
  const entity = place ? entities[Number(place[1])] : undefined;
  const row = place ? Number(place[2]) : -1;
  const field = entity?.fields?.[row];
  if (!entity || !field) return null;
  const typeCell = root.querySelector(`[id="a_ft${place![1]}_${row}"]`);
  return {
    key: `row:${entity.id}:${field.name}`,
    ref,
    title: field.name,
    detail: (typeCell ? tooltipOf(typeCell) : "") || field.annotation || field.type || "",
    // All of it is already here: a row needs no read, and a relation's row has no node to read.
    description: field.description,
    nodeId: null,
    change: marked(field.diff) ? { title: field.name, status: field.diff, elements: rowElements(entity.id, field.name) } : null,
    lifecycleIds: field.lifecycle_id ? [field.lifecycle_id] : [],
    copy: field.name,
  };
}
