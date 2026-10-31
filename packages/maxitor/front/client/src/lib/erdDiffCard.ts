// src/lib/erdDiffCard.ts
/**
 * Which graph elements a click on the ERD in Diff stands for (spec 038, FR-028): a marked table's header is its
 * ``Entity`` node; a marked row is its ``EntityField`` node with its ``entity_field`` edge, or — a relation's row —
 * its ``entity_relation`` edge. The card asks the server for each and shows what changed in those it has.
 */
import type { ErdDiff, ErdEntity } from "@/lib/buildDotSource";

/** One graph element a card reads. */
export type CardElement = { kind: "node" | "edge"; id: string };

/** What a click opened a card for: its title, its status, and the elements it reads. */
export type CardTarget = { title: string; status: Exclude<ErdDiff, "unchanged">; elements: CardElement[] };

/** The ids ``erdCellId`` writes on a header's cells and a row's cells, as Graphviz wraps them (``a_<id>``). */
const HEADER = /^a_(?:hd|hn|ks)(\d+)$/;
const ROW = /^a_f[nt](\d+)_(\d+)$/;

/** The elements a row of ``entity`` stands for. */
export function rowElements(entityId: string, field: string): CardElement[] {
  return [
    { kind: "node", id: `${entityId}:${field}` },
    { kind: "edge", id: `${entityId}|entity_field|${entityId}:${field}` },
    { kind: "edge", id: `${entityId}|entity_relation|${field}` },
  ];
}

/** The card a click on ``target`` opens, or ``null`` when it is not a marked table or row of ``entities``. */
export function cardAt(target: Element | null, entities: readonly ErdEntity[]): CardTarget | null {
  for (let node: Element | null = target; node; node = node.parentElement) {
    const id = node.getAttribute?.("id") ?? "";
    const header = HEADER.exec(id);
    if (header) {
      const entity = entities[Number(header[1])];
      const status = entity?.diff;
      return entity && status && status !== "unchanged" ? { title: entity.label || entity.id, status, elements: [{ kind: "node", id: entity.id }] } : null;
    }
    const row = ROW.exec(id);
    if (row) {
      const entity = entities[Number(row[1])];
      const field = entity?.fields?.[Number(row[2])];
      const status = field?.diff;
      return entity && field && status && status !== "unchanged" ? { title: field.name, status, elements: rowElements(entity.id, field.name) } : null;
    }
  }
  return null;
}

/** Whether a name cell belongs to a marked table or row: in Diff it opens the card, it is not copied. */
export function isMarkedCell(cell: Element, entities: readonly ErdEntity[]): boolean {
  return cardAt(cell, entities) !== null;
}
