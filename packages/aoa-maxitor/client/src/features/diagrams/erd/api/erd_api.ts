// packages/aoa-maxitor/client/src/features/diagrams/erd/api/erd_api.ts
import { apiUrl } from "../../../../shared/config/api";
import type { DomainQualnamesPayload, ErdDomainPayload, ErdDomainsBatchPayload } from "../model";

export async function fetchErdDomainQualnames(): Promise<DomainQualnamesPayload> {
  const res = await fetch(apiUrl("/api/v1/list-domains"));
  if (!res.ok) throw new Error(`list-domains ${res.status}`);
  return (await res.json()) as DomainQualnamesPayload;
}

export async function fetchErdDomainsBatch(
  domainQualnames: string[],
  includeOneHopNeighbors = true,
): Promise<ErdDomainsBatchPayload> {
  const params = new URLSearchParams();
  params.set("include_one_hop_neighbors", String(includeOneHopNeighbors));
  for (const q of domainQualnames) {
    params.append("domain_qualnames", q);
  }
  const res = await fetch(apiUrl(`/api/v1/list-entities?${params.toString()}`));
  if (!res.ok) throw new Error(`list-entities ${res.status}`);
  return (await res.json()) as ErdDomainsBatchPayload;
}

export async function fetchErdDomainPayload(
  qual: string,
  includeOneHopNeighbors = true,
): Promise<ErdDomainPayload> {
  const batch = await fetchErdDomainsBatch([qual], includeOneHopNeighbors);
  const slice = batch.domain_slices[0];
  if (!slice) {
    throw new Error("empty domain_slices");
  }
  return slice;
}
