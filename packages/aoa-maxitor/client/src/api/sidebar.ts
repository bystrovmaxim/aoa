// src/api/sidebar.ts
import { graphApiUrl } from "@/api/client";
import type { SidebarPayload } from "@/model/sidebar";

/** Matches FastAPI handler ``get_sidebar`` → ``GET /api/sidebar``. */
export async function getSidebar(): Promise<SidebarPayload> {
  const res = await fetch(graphApiUrl("/api/sidebar"));
  if (!res.ok) throw new Error(`${res.status}`);
  return (await res.json()) as SidebarPayload;
}
