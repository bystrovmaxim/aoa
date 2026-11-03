// src/api/erd.ts
import { graphFetch, type GraphRead } from "@/api/client";
import type { DomainQualnamesPayload, EntityKindsPayload, ErdDomainPayload, ErdDomainsBatchPayload } from "@/model/erd";

/** Matches ``GET /api/v1/list-domains`` / ``ListDomainsAction``. */
export async function listDomains(read?: GraphRead): Promise<DomainQualnamesPayload> {
  const res = await graphFetch("/api/v1/list-domains", undefined, read);
  if (!res.ok) throw new Error(`list-domains ${res.status}`);
  return (await res.json()) as DomainQualnamesPayload;
}

/** Matches ``GET /api/v1/list-entity-kinds`` / ``ListEntityKindsAction``. */
export async function listEntityKinds(read?: GraphRead): Promise<EntityKindsPayload> {
  const res = await graphFetch("/api/v1/list-entity-kinds", undefined, read);
  if (!res.ok) throw new Error(`list-entity-kinds ${res.status}`);
  return (await res.json()) as EntityKindsPayload;
}

/** Matches ``GET /api/v1/list-entities`` / ``ListEntitiesAction``. */
export async function listEntities(
  domainQualnames: string[],
  includeOneHopNeighbors = true,
  read?: GraphRead,
): Promise<ErdDomainsBatchPayload> {
  const params = new URLSearchParams();
  params.set("include_one_hop_neighbors", String(includeOneHopNeighbors));
  for (const q of domainQualnames) {
    params.append("domain_qualnames", q);
  }
  const res = await graphFetch("/api/v1/list-entities", params, read);
  if (!res.ok) throw new Error(`list-entities ${res.status}`);
  return (await res.json()) as ErdDomainsBatchPayload;
}

/** Same endpoint as ``listEntities``; convenience for a single ``domain_qualname``. */
export async function listEntitiesForDomain(
  qual: string,
  includeOneHopNeighbors = true,
): Promise<ErdDomainPayload> {
  const batch = await listEntities([qual], includeOneHopNeighbors);
  const slice = batch.domain_slices[0];
  if (!slice) {
    throw new Error("empty domain_slices");
  }
  return slice;
}
