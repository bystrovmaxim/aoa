// packages/aoa-maxitor/client/src/features/diagrams/erd/api/erd_api.ts
import { apiUrl } from "../../../../shared/config/api";
import type { DomainQualnamesPayload, ErdDomainPayload } from "../model";

export async function fetchErdDomainQualnames(): Promise<DomainQualnamesPayload> {
  const res = await fetch(apiUrl("/api/v1/erd/domain-qualnames"));
  if (!res.ok) throw new Error(`domain-qualnames ${res.status}`);
  return (await res.json()) as DomainQualnamesPayload;
}

export async function fetchErdDomainPayload(qual: string): Promise<ErdDomainPayload> {
  const res = await fetch(apiUrl(`/api/v1/erd/domains/${encodeURIComponent(qual)}`));
  if (!res.ok) throw new Error(`domain ${res.status}`);
  return (await res.json()) as ErdDomainPayload;
}
