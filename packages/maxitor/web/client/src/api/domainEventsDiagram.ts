// src/api/domainEventsDiagram.ts
import { graphFetch, type GraphRead } from "@/api/client";
import type { DomainEventsDiagramPayload } from "@/model/domainEventsDiagram";

/** The events diagram of one domain, or of all of them when ``domainId`` is ``null``. */
export async function fetchDomainEventsDiagram(domainId: string | null, read?: GraphRead): Promise<DomainEventsDiagramPayload> {
  const response = domainId === null ? await graphFetch("/api/v1/events-diagram", undefined, read) : await graphFetch("/api/v1/domain-events-diagram", new URLSearchParams({ domain_id: domainId }), read);
  if (!response.ok) throw new Error(`Events diagram request failed (${response.status}): ${response.statusText}`);
  const body = (await response.json()) as { domain_events_diagram?: DomainEventsDiagramPayload };
  if (!body.domain_events_diagram) throw new Error("Events diagram response missing domain_events_diagram");
  return body.domain_events_diagram;
}
