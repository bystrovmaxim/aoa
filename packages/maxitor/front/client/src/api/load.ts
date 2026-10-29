// src/api/load.ts
import { apiUrl } from "@/api/client";

/** POST /api/load — loads the coordinator graph from the given AOA service URL. */
export async function loadGraph(serviceUrl: string): Promise<void> {
  const res = await fetch(apiUrl("/api/load"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ service_url: serviceUrl }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = (body as { detail?: string }).detail ?? `HTTP ${res.status}`;
    throw new Error(detail);
  }
}
