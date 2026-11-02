// src/api/domainUseCaseDiagram.ts
import { graphFetch, type GraphRead } from "@/api/client";
import type { DomainUseCaseDiagramPayload } from "@/model/domainUseCaseDiagram";

/** ``GET /api/v1/domain-use-case-diagram`` — UML use-case slice for one Domain interchange id. */
export async function fetchDomainUseCaseDiagram(domainId: string | null, read?: GraphRead): Promise<DomainUseCaseDiagramPayload> {
  // With no domain, the diagram of all of them (spec 041).
  const response = domainId === null ? await graphFetch("/api/v1/use-case-diagram", undefined, read) : await graphFetch("/api/v1/domain-use-case-diagram", new URLSearchParams({ domain_id: domainId }), read);
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Use-case diagram request failed (${response.status}): ${text || response.statusText}`);
  }
  const body = (await response.json()) as { domain_use_case_diagram?: DomainUseCaseDiagramPayload };
  const payload = body.domain_use_case_diagram;
  if (!payload || typeof payload !== "object") {
    throw new Error("Use-case diagram response missing domain_use_case_diagram");
  }
  return payload;
}
