// src/components/navigation/LeftSidebar/hooks/useSidebarPayload.ts
import { getSidebar } from "@/api/sidebar";
import type { SidebarPayload } from "@/model/sidebar";
import { useCallback, useEffect, useState } from "react";

export function useSidebarPayload() {
  const [sidebar, setSidebar] = useState<SidebarPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    try {
      const json = await getSidebar();
      const hasData = json.level1_nodes.length > 0;
      setSidebar(hasData ? json : null);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const json = await getSidebar();
        if (cancelled) return;
        const hasData = json.level1_nodes.length > 0;
        setSidebar(hasData ? json : null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { sidebar, error, reload: fetch_ };
}
