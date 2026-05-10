// packages/aoa-maxitor/client/src/features/diagrams/erd/components/erd_viewer.tsx
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import { useErdViewerBlobUrl, type ErdViewerSelection } from "../hooks/use_erd_viewer_blob_url";

type ErdViewerProps = {
  selection: ErdViewerSelection;
};

/** Full-page ERD workspace: API JSON → in-browser HTML shell → iframe (Graphviz / Cytoscape / Mermaid inside). */
export function ErdViewer({ selection }: ErdViewerProps) {
  const { iframeUrl, loading, error } = useErdViewerBlobUrl(selection);

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
