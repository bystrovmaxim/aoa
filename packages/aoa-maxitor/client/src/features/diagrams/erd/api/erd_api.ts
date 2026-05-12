// packages/aoa-maxitor/client/src/features/diagrams/erd/api/erd_api.ts
import { apiUrl } from "../../../../shared/config/api";
import type { DomainQualnamesPayload, ErdDomainPayload } from "../model";

export async function fetchErdDomainQualnames(): Promise<DomainQualnamesPayload> {
  const res = await fetch(apiUrl("/api/v1/erd/domain-qualnames"));
  if (!res.ok) throw new Error(`domain-qualnames ${res.status}`);
  return (await res.json()) as DomainQualnamesPayload;
}

export async function fetchErdDomainPayload(
  qual: string,
  includeOneHopNeighbors = true,
): Promise<ErdDomainPayload> {
  const params = new URLSearchParams({
    include_one_hop_neighbors: String(includeOneHopNeighbors),
  });
  const res = await fetch(
    apiUrl(`/api/v1/erd/domains/${encodeURIComponent(qual)}?${params.toString()}`),
  );
  if (!res.ok) throw new Error(`domain ${res.status}`);
  return (await res.json()) as ErdDomainPayload;
}
