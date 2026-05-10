// packages/aoa-maxitor/client/src/features/diagram-viewer/DiagramWorkspace.tsx
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { ErdViewer } from "./erd";
import type { DiagramSelection } from "./model/types";

type DiagramWorkspaceProps = {
  diagram: DiagramSelection | null;
};

/** Main diagram area: interchange graph iframe, or ERD viewer sub-feature. */
export function DiagramWorkspace({ diagram }: DiagramWorkspaceProps) {
  return (
    <Box
      sx={{
        flex: 1,
        minWidth: 0,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        bgcolor: "grey.100",
        overflow: "hidden",
      }}
    >
      {diagram?.kind === "iframe" ? (
        <Box
          component="iframe"
          key={diagram.url}
          title="Diagram viewer"
          src={diagram.url}
          sx={{ border: 0, flex: 1, width: "100%", minHeight: 0 }}
        />
      ) : diagram?.kind === "erd" ? (
        <ErdViewer key={diagram.qualifier ?? "all"} selection={diagram} />
      ) : (
        <Box sx={{ flex: 1, display: "grid", placeItems: "center", p: 2 }}>
          <Paper variant="outlined" sx={{ maxWidth: 520, p: 3, borderRadius: 2 }}>
            <Typography variant="h5" component="h1" gutterBottom>
              Diagram workspace
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Open the interchange graph (iframe) or an ERD. The graph loads HTML from{" "}
              <Box component="code" sx={{ fontSize: "0.85em" }}>
                /api/diagrams/graph
              </Box>
              ; ERD uses JSON from{" "}
              <Box component="code" sx={{ fontSize: "0.85em" }}>
                /api/v1/erd/*
              </Box>{" "}
              and bundles the viewer shell in the SPA.
            </Typography>
          </Paper>
        </Box>
      )}
    </Box>
  );
}
