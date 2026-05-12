// packages/aoa-maxitor/client/src/features/diagrams/erd/hooks/use_erd_viewer_blob_url.ts
import { useCallback, useEffect, useRef, useState } from "react";
import type { DiagramSelection } from "../../../diagram_selection/types";
import { buildErdHtmlDocument } from "../lib/build_erd_html_document";
import { loadErdDomainsBundle } from "../lib/load_erd_domains_bundle";

export type ErdViewerSelection = Extract<DiagramSelection, { kind: "erd" }>;

/**
 * Load ERD JSON from the Maxitor API, build the standalone HTML document in-browser, expose a blob URL for an iframe.
 */
export function useErdViewerBlobUrl(selection: ErdViewerSelection): {
  iframeUrl: string | null;
  loading: boolean;
  error: string | null;
} {
  const [iframeUrl, setIframeUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastUrl = useRef<string | null>(null);

  const revokeLast = useCallback(() => {
    if (lastUrl.current) {
      URL.revokeObjectURL(lastUrl.current);
      lastUrl.current = null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      setError(null);
      setIframeUrl(null);
      revokeLast();
      setLoading(true);
      try {
        const includeOneHopNeighbors = true;
        const bundle = await loadErdDomainsBundle(selection, includeOneHopNeighbors);

        const title =
          selection.qualifier === null
            ? "Interchange ERD"
            : `ERD — ${bundle.first_domain_label ?? selection.qualifier.split(".").pop() ?? "domain"}`;

        const html = buildErdHtmlDocument(
          {
            ...bundle,
            initial_include_one_hop: includeOneHopNeighbors,
          },
          title,
        );
        const blob = new Blob([html], { type: "text/html;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        lastUrl.current = url;
        setIframeUrl(url);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      setIframeUrl(null);
      revokeLast();
    };
  }, [selection.qualifier, revokeLast]);

  return { iframeUrl, loading, error };
}
