// src/lib/loadErdDomainsBundle.ts
import { fetchErdDomainsBatch, fetchErdDomainQualnames } from "@/api/erd";
import type { DiagramSelection } from "@/model/diagramSelection";
import { allocateDomainTabKey } from "@/lib/domainTabKeys";

export type ErdViewerSelection = Extract<DiagramSelection, { kind: "erd" }>;

export type ErdDomainsBundle = {
  domains: Record<string, { entities: unknown[]; relations: unknown[] }>;
  domain_qualifiers: Record<string, string>;
  domain_qualifier_colors: Record<string, string>;
  /** First domain row label for the diagram title (optional). */
  first_domain_label?: string;
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
  const listing = await fetchErdDomainQualnames();
  const domain_qualifier_colors = Object.fromEntries(
    listing.list_domains.map((r) => [r.qualname, r.color]),
  );
  const quals: string[] =
    selection.qualifier !== null
      ? [selection.qualifier]
      : listing.list_domains.map((r) => r.qualname);

  if (!quals.length) throw new Error("No domain qualnames");

  const used = new Set<string>();
  const domains: Record<string, { entities: unknown[]; relations: unknown[] }> = {};
  const domain_qualifiers: Record<string, string> = {};

  const { domain_slices: payloads } = await fetchErdDomainsBatch(quals, includeOneHopNeighbors);
  let first_domain_label: string | undefined;
  for (const p of payloads) {
    const key = allocateDomainTabKey(used, p.domain_label);
    domains[key] = p.list_entities;
    domain_qualifiers[key] = p.domain_qualname;
    if (first_domain_label === undefined) first_domain_label = p.domain_label;
  }

  return { domains, domain_qualifiers, domain_qualifier_colors, first_domain_label };
}

export async function loadErdDomainSlicesBundle(
  requests: ErdDomainSliceRequest[],
  includeOneHopNeighbors: boolean,
  domain_qualifier_colors: Record<string, string>,
): Promise<Pick<ErdDomainsBundle, "domains" | "domain_qualifiers" | "domain_qualifier_colors">> {
  const domains: Record<string, { entities: unknown[]; relations: unknown[] }> = {};
  const domain_qualifiers: Record<string, string> = {};

  const { domain_slices } = await fetchErdDomainsBatch(
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
