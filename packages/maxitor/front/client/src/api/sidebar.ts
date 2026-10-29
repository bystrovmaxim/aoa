// src/api/sidebar.ts
import { GraphReadError, graphFetch } from "@/api/client";
import type { SidebarPayload } from "@/model/sidebar";

/** Matches FastAPI handler ``get_sidebar`` → ``GET /api/sidebar``. */
export async function getSidebar(): Promise<SidebarPayload> {
  const res = await graphFetch("/api/sidebar");
  if (!res.ok) throw new GraphReadError(res.status, `${res.status}`);
  return (await res.json()) as SidebarPayload;
}
