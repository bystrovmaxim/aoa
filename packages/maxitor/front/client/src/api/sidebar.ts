// src/api/sidebar.ts
import { GraphReadError, graphFetch, type GraphRead } from "@/api/client";
import type { SidebarPayload } from "@/model/sidebar";

/** Matches FastAPI handler ``get_sidebar`` → ``GET /api/sidebar``; ``read`` reads another version than the tab's (spec 038). */
export async function getSidebar(read?: GraphRead): Promise<SidebarPayload> {
  const res = await graphFetch("/api/sidebar", undefined, read);
  if (!res.ok) throw new GraphReadError(res.status, `${res.status}`);
  return (await res.json()) as SidebarPayload;
}
