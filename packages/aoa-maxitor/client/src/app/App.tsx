// src/app/App.tsx
import { useEffect, useRef, useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { DiagramWorkspacePage } from "@/components/pages/DiagramWorkspacePage";
import { LeftSidebar } from "@/components/navigation/LeftSidebar";
import { useSidebarPayload } from "@/components/navigation/LeftSidebar/hooks/useSidebarPayload";
import type { DiagramSelection } from "@/model/diagramSelection";
import type { SidebarPayload } from "@/model/sidebar";
import { loadGraph } from "@/api/load";
import { pushServiceUrl } from "@/lib/serviceUrlHistory";
import { firstSelectionOfKind } from "@/lib/sidebarNavigation";
import {
  deepLinkNeedsSidebarDefault,
  deepLinkToSelection,
  pushUrlState,
  readUrlDeepLink,
  syncUrlToState,
  type UrlDeepLink,
} from "@/lib/urlState";

export function App() {
  const [diagram, setDiagram] = useState<DiagramSelection | null>(null);
  const [serviceUrl, setServiceUrl] = useState<string | null>(null);
  const { sidebar, reload, reset } = useSidebarPayload();
  const pendingKind = useRef<ReturnType<typeof deepLinkNeedsSidebarDefault>>(null);

  // Captured once on the first render — reading window.location.search fresh inside the
  // mount effect below is unsafe: the URL-sync effect further down rewrites the URL as soon
  // as it runs, so a second read (e.g. React StrictMode's dev-only double-invoke of mount
  // effects) would see an already-rewritten URL and silently drop the deep link.
  const initialLinkRef = useRef<UrlDeepLink | undefined>(undefined);
  if (!initialLinkRef.current) initialLinkRef.current = readUrlDeepLink();

  /** Applies a service+view combination read from the URL — initial load or a popstate. */
  function applyDeepLink(link: UrlDeepLink, activeServiceUrl: string | null, activeSidebar: SidebarPayload | null) {
    const resolved = deepLinkToSelection(link);
    if (resolved) {
      pendingKind.current = null;
      setDiagram(resolved);
    } else {
      const kind = deepLinkNeedsSidebarDefault(link);
      const fallback = kind && activeSidebar ? firstSelectionOfKind(activeSidebar, kind) : null;
      pendingKind.current = fallback ? null : kind;
      setDiagram(fallback);
    }

    if (link.source && link.source !== activeServiceUrl) {
      const source = link.source;
      setServiceUrl(source);
      void loadGraph(source)
        .then(() => {
          pushServiceUrl(source);
          return reload();
        })
        .catch(() => {
          // Bad/unreachable ?source= — fall back to the manual "AOA Service URL" prompt.
          setServiceUrl(null);
        });
    } else if (!link.source) {
      setServiceUrl(null);
    }
  }

  // Honor a deep link on first load: ?source=<service-url>&view=<slug>[&domain=|&node=&host=].
  useEffect(() => {
    applyDeepLink(initialLinkRef.current!, null, null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reload]);

  // Resolve a use-case/lifecycle-fsm deep link that named a kind but no qualifier, once the sidebar arrives.
  useEffect(() => {
    if (!sidebar || !pendingKind.current) return;
    const resolved = firstSelectionOfKind(sidebar, pendingKind.current);
    pendingKind.current = null;
    if (resolved) setDiagram(resolved);
  }, [sidebar]);

  // Back/forward — the browser already changed the URL for us; mirror it into state.
  useEffect(() => {
    function handlePopState() {
      applyDeepLink(readUrlDeepLink(), serviceUrl, sidebar);
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [serviceUrl, sidebar]);

  // Keep the URL accurate as state resolves — replaceState, so it never adds a history entry on its own.
  useEffect(() => {
    syncUrlToState(serviceUrl, diagram);
  }, [serviceUrl, diagram]);

  function handleSelectDiagram(sel: DiagramSelection) {
    pushUrlState(serviceUrl, sel);
    setDiagram(sel);
  }

  function handleLoaded(url: string) {
    pushUrlState(url, null);
    setServiceUrl(url);
    void reload();
  }

  function handleReset() {
    pushUrlState(null, null);
    setServiceUrl(null);
    setDiagram(null);
    reset();
  }

  return (
    <MainLayout
      sidebar={
        <LeftSidebar
          diagram={diagram}
          onSelectDiagram={handleSelectDiagram}
          sidebar={sidebar}
          onLoaded={handleLoaded}
          onReset={handleReset}
        />
      }
    >
      <DiagramWorkspacePage diagram={diagram} />
    </MainLayout>
  );
}
