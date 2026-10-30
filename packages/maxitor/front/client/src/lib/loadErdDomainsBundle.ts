// src/lib/loadErdDomainsBundle.ts
import { getActiveBase } from "@/api/client";
import { compareVersions } from "@/api/compare";
import { listDomains, listEntities, listEntityKinds } from "@/api/erd";
import { markErd, mergeErdSlices, mergeRelations, type ErdSlice } from "@/lib/erdDiff";
import type { ErdRelation } from "@/lib/buildDotSource";
import type { EntityKindRow } from "@/model/erd";
import type { DiagramSelection } from "@/model/diagramSelection";
import { allocateDomainTabKey } from "@/lib/domainTabKeys";

export type ErdViewerSelection = Extract<DiagramSelection, { kind: "erd" }>;

export type ErdDomainsBundle = {
  domains: Record<string, { entities: unknown[]; relations: unknown[] }>;
  domain_qualifiers: Record<string, string>;
  domain_qualifier_colors: Record<string, string>;
  /** ``domain_qualname`` → short label from ``list_domains`` / DuckDB ``domain.label``. */
  domain_qualifier_labels: Record<string, string>;
  /** Tab key → human domain label (for legend row text). */
  domain_tab_labels?: Record<string, string>;
  /** First domain row label for the diagram title (optional). */
  first_domain_label?: string;
  /** Every line between two tables of the whole request; the merged ERD draws these, pruned to the screen. */
  relations?: unknown[];
  /** Entity kinds of the loaded graph with their display names (``list-entity-kinds``). */
  entity_kinds?: EntityKindRow[];
  /** In Diff (spec 038): the slices are A's and B's together, every table, row and line marked. */
  diff?: boolean;
};

export type ErdDomainSliceRequest = {
  key: string;
  qualname: string;
};

/**
 * Load all ERD domain slices for the current selection (same contract as the blob HTML builder).
 * Runs in the SPA origin so ``fetch`` matches ``api/erd`` (same origin as the Vite app).
 */
export async function loadErdDomainsBundle(
  selection: ErdViewerSelection,
  includeOneHopNeighbors: boolean,
): Promise<ErdDomainsBundle> {
  if (getActiveBase()) return loadErdDiffBundle(selection, includeOneHopNeighbors);
  const listing = await listDomains();
  const domain_qualifier_colors = Object.fromEntries(
    listing.list_domains.map((r) => [r.qualname, r.color]),
  );
  const domain_qualifier_labels = Object.fromEntries(
    listing.list_domains.map((r) => [r.qualname, r.label]),
  );
  const quals: string[] =
    selection.qualifier !== null
      ? [selection.qualifier]
      : listing.list_domains.map((r) => r.qualname);

  if (!quals.length) throw new Error("No domain qualnames");

  const used = new Set<string>();
  const domains: Record<string, { entities: unknown[]; relations: unknown[] }> = {};
  const domain_qualifiers: Record<string, string> = {};
  const domain_tab_labels: Record<string, string> = {};

  const [{ domain_slices: payloads, relations }, kinds] = await Promise.all([
    listEntities(quals, includeOneHopNeighbors),
    listEntityKinds(),
  ]);
  let first_domain_label: string | undefined;
  for (const p of payloads) {
    const key = allocateDomainTabKey(used, p.domain_label);
    domains[key] = p.list_entities;
    domain_qualifiers[key] = p.domain_qualname;
    domain_tab_labels[key] = p.domain_label;
    if (first_domain_label === undefined) first_domain_label = p.domain_label;
  }

  return {
    domains,
    domain_qualifiers,
    domain_qualifier_colors,
    domain_qualifier_labels,
    domain_tab_labels,
    first_domain_label,
    relations,
    entity_kinds: kinds.list_entity_kinds,
  };
}

export async function loadErdDomainSlicesBundle(
  requests: ErdDomainSliceRequest[],
  includeOneHopNeighbors: boolean,
  domain_qualifier_colors: Record<string, string>,
): Promise<Pick<ErdDomainsBundle, "domains" | "domain_qualifiers" | "domain_qualifier_colors">> {
  const domains: Record<string, { entities: unknown[]; relations: unknown[] }> = {};
  const domain_qualifiers: Record<string, string> = {};

  const { domain_slices } = await listEntities(
    requests.map((r) => r.qualname),
    includeOneHopNeighbors,
  );
  const byQual = new Map(domain_slices.map((s) => [s.domain_qualname, s]));

  for (const { key, qualname } of requests) {
    const payload = byQual.get(qualname);
    if (!payload) {
      throw new Error(`missing domain slice for ${qualname}`);
    }
    domains[key] = payload.list_entities;
    domain_qualifiers[key] = payload.domain_qualname;
  }

  return { domains, domain_qualifiers, domain_qualifier_colors };
}

/**
 * The ERD of two versions (spec 038, research R10): A's and B's domains, and each domain's tables, rows and lines
 * read from both and merged, then marked with what the comparison says. A domain that only one version has comes
 * from that one alone, so everything on it is added or removed.
 */
async function loadErdDiffBundle(selection: ErdViewerSelection, includeOneHopNeighbors: boolean): Promise<ErdDomainsBundle> {
  const base = getActiveBase()!;
  const [newerListing, olderListing, kinds, compared] = await Promise.all([listDomains(), listDomains(base), listEntityKinds(), compareVersions()]);
  const rows = [...newerListing.list_domains, ...olderListing.list_domains.filter((row) => !newerListing.list_domains.some((each) => each.qualname === row.qualname))];
  const inOlder = new Set(olderListing.list_domains.map((row) => row.qualname));
  const inNewer = new Set(newerListing.list_domains.map((row) => row.qualname));
  const quals = selection.qualifier !== null ? [selection.qualifier] : rows.map((row) => row.qualname);
  if (!quals.length) throw new Error("No domain qualnames");
  const newerQuals = quals.filter((qual) => inNewer.has(qual));
  const olderQuals = quals.filter((qual) => inOlder.has(qual));
  const empty = { domain_slices: [], relations: [] as unknown[] };
  const [newer, older] = await Promise.all([
    newerQuals.length ? listEntities(newerQuals, includeOneHopNeighbors) : empty,
    olderQuals.length ? listEntities(olderQuals, includeOneHopNeighbors, base) : empty,
  ]);
  const olderByQual = new Map(older.domain_slices.map((slice) => [slice.domain_qualname, slice]));
  const newerByQual = new Map(newer.domain_slices.map((slice) => [slice.domain_qualname, slice]));
  const used = new Set<string>();
  const domains: Record<string, { entities: unknown[]; relations: unknown[] }> = {};
  const domain_qualifiers: Record<string, string> = {};
  const domain_tab_labels: Record<string, string> = {};
  let first_domain_label: string | undefined;
  for (const qual of quals) {
    const now = newerByQual.get(qual);
    const was = olderByQual.get(qual);
    if (!now && !was) continue;
    const label = (now ?? was)!.domain_label;
    const key = allocateDomainTabKey(used, label);
    const merged = markErd(mergeErdSlices(was?.list_entities as ErdSlice | undefined, now?.list_entities as ErdSlice | undefined), compared);
    domains[key] = merged as { entities: unknown[]; relations: unknown[] };
    domain_qualifiers[key] = qual;
    domain_tab_labels[key] = label;
    if (first_domain_label === undefined) first_domain_label = label;
  }
  const relations = markErd({ relations: mergeRelations(older.relations as ErdRelation[] | undefined, newer.relations as ErdRelation[] | undefined) }, compared).relations;
  return {
    domains,
    domain_qualifiers,
    domain_qualifier_colors: Object.fromEntries(rows.map((row) => [row.qualname, row.color])),
    domain_qualifier_labels: Object.fromEntries(rows.map((row) => [row.qualname, row.label])),
    domain_tab_labels,
    first_domain_label,
    relations,
    entity_kinds: kinds.list_entity_kinds,
    diff: true,
  };
}
