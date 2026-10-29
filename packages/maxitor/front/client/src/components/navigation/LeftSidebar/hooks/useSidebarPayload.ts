// src/components/navigation/LeftSidebar/hooks/useSidebarPayload.ts
import { getSidebar } from "@/api/sidebar";
import type { SidebarPayload } from "@/model/sidebar";
import { useCallback, useState } from "react";

/** The sidebar of the open source; the page reads it after it knows which source it shows. */
export function useSidebarPayload() {
  const [sidebar, setSidebar] = useState<SidebarPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  /** Read the sidebar for the active source; throws so the caller can fall back to the prompt. */
  const reload = useCallback(async () => {
    try {
      const json = await getSidebar();
      const hasData = json.level1_nodes.length > 0;
      setSidebar(hasData ? json : null);
      setError(null);
      return json;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    }
  }, []);

  const reset = useCallback(() => {
    setSidebar(null);
    setError(null);
  }, []);

  return { sidebar, error, reload, reset };
}
