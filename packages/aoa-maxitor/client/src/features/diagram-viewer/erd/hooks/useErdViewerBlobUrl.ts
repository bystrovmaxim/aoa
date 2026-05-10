// packages/aoa-maxitor/client/src/features/diagram-viewer/erd/hooks/useErdViewerBlobUrl.ts
import { useCallback, useEffect, useRef, useState } from "react";
import type { DiagramSelection } from "../../model/types";
import { fetchErdDomainPayload, fetchErdDomainQualnames } from "../api/erdApi";
import { buildErdHtmlDocument } from "../lib/buildErdHtmlDocument";
import { allocateDomainTabKey } from "../lib/domainTabKeys";

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
        const quals: string[] =
          selection.qualifier !== null
            ? [selection.qualifier]
            : (await fetchErdDomainQualnames()).domain_qualnames;

        if (!quals.length) throw new Error("No domain qualnames");

        const used = new Set<string>();
        const domains: Record<string, { nodes: unknown[]; edges: unknown[] }> = {};
        const domain_qualifiers: Record<string, string> = {};

        const payloads = await Promise.all(quals.map((q) => fetchErdDomainPayload(q)));
        for (const p of payloads) {
          const key = allocateDomainTabKey(used, p.domain_label);
          domains[key] = p.graph;
          domain_qualifiers[key] = p.domain_qualifier;
        }

        const title =
          selection.qualifier === null
            ? "Interchange ERD"
            : `ERD — ${payloads[0]?.domain_label ?? selection.qualifier.split(".").pop() ?? "domain"}`;

        const html = buildErdHtmlDocument({ domains, domain_qualifiers }, title);
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
