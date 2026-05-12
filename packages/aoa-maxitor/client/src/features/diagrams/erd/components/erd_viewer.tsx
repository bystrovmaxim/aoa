// packages/aoa-maxitor/client/src/features/diagrams/erd/components/erd_viewer.tsx
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useRef } from "react";
import { useErdViewerBlobUrl, type ErdViewerSelection } from "../hooks/use_erd_viewer_blob_url";
import { enrichErdDataForViewer } from "../lib/enrich_erd_data";
import { loadErdDomainSlicesBundle } from "../lib/load_erd_domains_bundle";

type ErdViewerProps = {
  selection: ErdViewerSelection;
};

/** Full-page ERD workspace: API JSON → in-browser HTML shell → iframe (Graphviz / Cytoscape / Mermaid inside). */
export function ErdViewer({ selection }: ErdViewerProps) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const { iframeUrl, loading, error } = useErdViewerBlobUrl(selection);

  const postPatchToShell = useCallback((patch: { domains: unknown; domain_accent_colors: unknown }) => {
    const win = iframeRef.current?.contentWindow;
    if (!win) return;
    win.postMessage(
      {
        source: "maxitor-erd",
        type: "domains-patch",
        patch,
      },
      "*",
    );
  }, []);

  const postPatchErrorToShell = useCallback((revertTo: boolean, message: string) => {
    const win = iframeRef.current?.contentWindow;
    if (!win) return;
    win.postMessage(
      {
        source: "maxitor-erd",
        type: "domains-patch-error",
        revertTo,
        message,
      },
      "*",
    );
  }, []);

  useEffect(() => {
    const onMessage = (ev: MessageEvent) => {
      const d = ev.data as {
        source?: string;
        type?: string;
        include?: boolean;
        domains?: Array<{ key: string; qualname: string }>;
        domain_qualifier_colors?: Record<string, string>;
      } | null;
      if (!d || d.source !== "maxitor-erd" || d.type !== "set-one-hop") return;
      const include = Boolean(d.include);
      const revertTo = !include;
      const domainRequests = (d.domains ?? []).filter((row) => row.key && row.qualname);
      void (async () => {
        try {
          const raw = await loadErdDomainSlicesBundle(
            domainRequests,
            include,
            d.domain_qualifier_colors ?? {},
          );
          const enriched = enrichErdDataForViewer({
            domains: raw.domains,
            domain_qualifiers: raw.domain_qualifiers,
            domain_qualifier_colors: raw.domain_qualifier_colors,
          } as Record<string, unknown>);
          postPatchToShell({
            domains: enriched.domains,
            domain_accent_colors: enriched.domain_accent_colors,
          });
        } catch (e) {
          postPatchErrorToShell(revertTo, e instanceof Error ? e.message : String(e));
        }
      })();
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [postPatchErrorToShell, postPatchToShell]);

  return (
    <Box
      sx={{
        flex: 1,
        minWidth: 0,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        bgcolor: "grey.100",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {error && (
        <Typography color="error" variant="body2" sx={{ p: 2 }}>
          {error}
        </Typography>
      )}
      {loading && (
        <Box sx={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", zIndex: 1, bgcolor: "rgba(255,255,255,0.6)" }}>
          <CircularProgress size={40} />
        </Box>
      )}
      {iframeUrl && (
        <Box
          ref={iframeRef}
          component="iframe"
          key={iframeUrl}
          title="ERD viewer"
          src={iframeUrl}
          sx={{ border: 0, flex: 1, width: "100%", minHeight: 0 }}
        />
      )}
    </Box>
  );
}
