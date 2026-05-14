// src/api/sidebar.ts
import { apiUrl } from "@/api/client";
import type { SidebarPayload } from "@/model/sidebar";

export async function fetchSidebarPayload(): Promise<SidebarPayload> {
  const res = await fetch(apiUrl("/api/sidebar"));
  if (!res.ok) throw new Error(`${res.status}`);
  return (await res.json()) as SidebarPayload;
}
