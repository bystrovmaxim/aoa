// src/lib/sidebarDiff.ts
/**
 * The left panel of two versions (spec 038, FR-032; research R15): the pages of A and of B together, each once,
 * a page that only one of them has marked with the side it is in. A page is known by what it opens — its kind,
 * its node and the node it stands under — never by its label, which two different pages may share.
 */

import type { CompareResult } from "@/api/compare";
import type { ErdEntity, ErdRelation } from "@/lib/buildDotSource";
import type { ErdDomainsBundle } from "@/lib/loadErdDomainsBundle";
import type { DomainUseCaseDiagramPayload } from "@/model/domainUseCaseDiagram";
import type { NodeRow, SidebarPayload } from "@/model/sidebar";

/** A page's identity across two versions. */
export function pageKey(row: NodeRow): string {
  return `${row.type}|${row.id}|${row.parent_id ?? ""}`;
}

/** B's rows in B's order, then the rows only A has; a row in one only carries ``only``. */
function mergedRows(older: readonly NodeRow[], newer: readonly NodeRow[]): NodeRow[] {
  const before = new Set(older.map(pageKey));
  const now = new Set(newer.map(pageKey));
  return [
    ...newer.map((row) => (before.has(pageKey(row)) ? row : { ...row, only: "b" as const })),
    ...older.filter((row) => !now.has(pageKey(row))).map((row) => ({ ...row, only: "a" as const })),
  ];
}

/** The lifecycles with a state or a transition that differs; both ids begin with the lifecycle's id, a colon and the state. */
function changedLifecycles(compared: CompareResult): Set<string> {
  const lifecycles = new Set<string>();
  for (const id of [...Object.keys(compared.nodes), ...Object.keys(compared.edges)]) {
    const element = id.split("|")[0];
    lifecycles.add(element.slice(0, element.lastIndexOf(":")));
  }
  return lifecycles;
}

/** ``changed`` on a lifecycle's row that both versions have, when something in it differs (spec 042, FR-026a). */
function markChanged(rows: NodeRow[], compared: CompareResult | null): NodeRow[] {
  if (!compared) return rows;
  const lifecycles = changedLifecycles(compared);
  return rows.map((row) => (row.type === "lifecycle_state_diagram" && !row.only && lifecycles.has(row.id) ? { ...row, changed: true } : row));
}

/** The domains whose ERD or use-case diagram holds a change. */
export type ChangedDomains = { erd: ReadonlySet<string>; useCase: ReadonlySet<string> };

const marked = (status: string | undefined) => status !== undefined && status !== "unchanged";

/** The domains with a change, from the pair's ERD and its use cases of all domains. */
export function changedDomains(erd: Pick<ErdDomainsBundle, "domains" | "domain_qualifiers">, useCases: DomainUseCaseDiagramPayload): ChangedDomains {
  const inErd = Object.entries(erd.domains).flatMap(([key, slice]) => {
    const { entities = [], relations = [] } = slice as { entities?: ErdEntity[]; relations?: ErdRelation[] };
    const changed = entities.some((entity) => marked(entity.diff) || (entity.fields ?? []).some((field) => marked(field.diff))) || relations.some((relation) => marked(relation.diff));
    return changed ? [erd.domain_qualifiers[key]] : [];
  });
  const ofAction = new Map(useCases.actions.map((action) => [action.id, action.domain_id]));
  const inUseCases = [
    ...useCases.actions.filter((action) => marked(action.diff)).map((action) => action.domain_id),
    ...useCases.edges.filter((edge) => marked(edge.diff)).flatMap((edge) => [ofAction.get(edge.source_id), ofAction.get(edge.target_id)].filter((id): id is string => id !== undefined)),
  ];
  return { erd: new Set(inErd), useCase: new Set(inUseCases) };
}

/**
 * The left panel narrowed to what holds a change (spec 044): a domain's diagrams that changed, its lifecycles that
 * changed, what only one version has, and the domains over them. The diagrams of all domains stay: they hold everything.
 */
export function narrowToChanges(sidebar: SidebarPayload, changed: ChangedDomains): SidebarPayload {
  const keeps = (row: NodeRow) => {
    if (row.only || row.changed) return true;
    if (row.type === "erd_domain") return changed.erd.has(row.parent_id ?? row.id);
    if (row.type === "use_case_domain") return changed.useCase.has(row.parent_id ?? row.id);
    return false;
  };
  const level3 = sidebar.level3_diagrams.filter(keeps);
  const under = new Set(level3.map((row) => row.parent_id));
  return { ...sidebar, level3_diagrams: level3, level2_nodes: sidebar.level2_nodes.filter((row) => row.only || under.has(row.id)) };
}

/** The left panel of A and B merged: every page of either, ``only: "a"`` on A's alone, ``only: "b"`` on B's. */
export function mergeSidebars(older: SidebarPayload, newer: SidebarPayload, compared: CompareResult | null = null): SidebarPayload {
  return {
    ...newer,
    level1_nodes: mergedRows(older.level1_nodes, newer.level1_nodes),
    level2_diagrams: mergedRows(older.level2_diagrams, newer.level2_diagrams),
    level2_nodes: mergedRows(older.level2_nodes, newer.level2_nodes),
    level3_diagrams: markChanged(mergedRows(older.level3_diagrams, newer.level3_diagrams), compared),
  };
}
