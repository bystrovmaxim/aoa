// src/components/navigation/LeftSidebar/hooks/useChangedPages.ts
import { useEffect, useState } from "react";
import { loadErdDomainsBundle } from "@/lib/loadErdDomainsBundle";
import { changedDomains, narrowToChanges } from "@/lib/sidebarDiff";
import { loadUseCaseDiff } from "@/lib/useCaseDiff";
import type { SidebarPayload } from "@/model/sidebar";

/**
 * The left panel as it shows: ``sidebar``, or while ``on`` what of it holds a change (spec 044). The pair is read only
 * when asked, and again whenever the panel is read for another pair; until it answers the whole panel stands.
 */
export function useChangedPages(sidebar: SidebarPayload | null, on: boolean): SidebarPayload | null {
  const [narrow, setNarrow] = useState<SidebarPayload | null>(null);
  useEffect(() => {
    setNarrow(null);
    if (!on || !sidebar) return undefined;
    let gone = false;
    void Promise.all([loadErdDomainsBundle({ kind: "erd", qualifier: null }, false), loadUseCaseDiff(null)])
      .then(([erd, useCases]) => {
        if (!gone) setNarrow(narrowToChanges(sidebar, changedDomains(erd, useCases)));
      })
      .catch(() => undefined);
    return () => {
      gone = true;
    };
  }, [sidebar, on]);
  return on && narrow ? narrow : sidebar;
}
