// src/api/sidebar.ts
import { apiUrl } from "@/api/client";
import type { SidebarPayload } from "@/model/sidebar";

/** Matches FastAPI handler ``get_sidebar`` → ``GET /api/sidebar``. */
export async function getSidebar(): Promise<SidebarPayload> {
  const res = await fetch(apiUrl("/api/sidebar"));
  if (!res.ok) throw new Error(`${res.status}`);
  return (await res.json()) as SidebarPayload;
}
