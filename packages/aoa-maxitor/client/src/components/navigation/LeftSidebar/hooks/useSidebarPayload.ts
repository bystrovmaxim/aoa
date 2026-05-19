// src/components/navigation/LeftSidebar/hooks/useSidebarPayload.ts
import { getSidebar } from "@/api/sidebar";
import type { SidebarPayload } from "@/model/sidebar";
import { useEffect, useState } from "react";

export function useSidebarPayload() {
  const [sidebar, setSidebar] = useState<SidebarPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const json = await getSidebar();
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
