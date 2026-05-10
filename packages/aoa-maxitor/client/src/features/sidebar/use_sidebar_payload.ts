// packages/aoa-maxitor/client/src/features/sidebar/use_sidebar_payload.ts
import { useEffect, useState } from "react";
import { apiUrl } from "../../shared/config/api";
import type { SidebarPayload } from "./types";

export function useSidebarPayload() {
  const [sidebar, setSidebar] = useState<SidebarPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(apiUrl("/api/sidebar"));
        if (!res.ok) throw new Error(`${res.status}`);
        const json = (await res.json()) as SidebarPayload;
        if (!cancelled) setSidebar(json);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { sidebar, error };
}
