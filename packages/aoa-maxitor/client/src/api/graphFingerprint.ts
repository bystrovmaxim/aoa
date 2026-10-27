// src/api/graphFingerprint.ts
import { GraphReadError, graphFetch } from "@/api/client";

/**
 * ``GET /api/v1/graph-fingerprint`` / ``GraphFingerprintAction`` — the fingerprint of the graph Maxitor
 * holds for the open source, answered from memory (spec 028, FR-076).
 */
export async function getGraphFingerprint(): Promise<string> {
  const res = await graphFetch("/api/v1/graph-fingerprint");
  if (!res.ok) throw new GraphReadError(res.status, `${res.status}`);
  const body = (await res.json()) as { fingerprint: string };
  return body.fingerprint;
}
