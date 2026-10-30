// src/components/navigation/LeftSidebar/hooks/useSidebarPayload.ts
import { getActiveBase } from "@/api/client";
import { getSidebar } from "@/api/sidebar";
import { mergeSidebars } from "@/lib/sidebarDiff";
import type { SidebarPayload } from "@/model/sidebar";
import { useCallback, useState } from "react";

/** The sidebar of the open source — in Diff, of A and B merged (spec 038, FR-032); the page reads it after it knows which source it shows. */
/** ``newer`` merged with A's sidebar while Diff compares with A; A refused leaves B's alone, as the page says A is refused. */
async function withOlder(newer: SidebarPayload): Promise<SidebarPayload> {
  const base = getActiveBase();
  if (!base) return newer;
  try {
    return mergeSidebars(await getSidebar(base), newer);
  } catch {
    return newer;
  }
}

export function useSidebarPayload() {
  const [sidebar, setSidebar] = useState<SidebarPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  /** Read the sidebar for the active source; throws so the caller can fall back to the prompt. */
  const reload = useCallback(async () => {
    try {
      const json = await withOlder(await getSidebar());
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
