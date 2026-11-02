// src/api/appInfo.ts
import { apiUrl } from "@/api/client";

/** ``GET /api/meta/app-info`` / ``AppInfoAction``: which Maxitor is running. */
export type AppInfo = { version: string; build: string };

/** Read the running Maxitor's package version and client build; needs no source. */
export async function getAppInfo(): Promise<AppInfo> {
  const res = await fetch(apiUrl("/api/meta/app-info"));
  if (!res.ok) throw new Error(`${res.status}`);
  return (await res.json()) as AppInfo;
}
