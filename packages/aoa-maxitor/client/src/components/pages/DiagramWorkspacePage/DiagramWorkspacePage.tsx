// src/components/pages/DiagramWorkspacePage/DiagramWorkspacePage.tsx
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import type { DiagramSelection } from "@/model/diagramSelection";
import { ErdViewer } from "@/components/diagrams/ErdViewer";
import { FullGraphViewer } from "@/components/diagrams/FullGraphViewer";

type DiagramWorkspacePageProps = {
  diagram: DiagramSelection | null;
};

/** Central workspace: full graph, ERD, or empty state from sidebar selection. */
export function DiagramWorkspacePage({ diagram }: DiagramWorkspacePageProps) {
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
      {diagram?.kind === "interchange_graph" ? (
        <FullGraphViewer key="full-graph" />
      ) : diagram?.kind === "erd" ? (
        <ErdViewer key={diagram.qualifier ?? "all"} selection={diagram} />
      ) : (
        <Box sx={{ flex: 1, display: "grid", placeItems: "center", p: 2 }}>
          <Paper variant="outlined" sx={{ maxWidth: 520, p: 3, borderRadius: 2 }}>
            <Typography variant="h5" component="h1" gutterBottom>
              Select a diagram
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Open the interchange graph or an ERD. The graph loads JSON from{" "}
              <Box component="code" sx={{ fontSize: "0.85em" }}>
                /api/v1/full-graph
              </Box>{" "}
              and renders with AntV G6 in the SPA; ERD uses{" "}
              <Box component="code" sx={{ fontSize: "0.85em" }}>
                /api/v1/list-domains
              </Box>{" "}
              and{" "}
              <Box component="code" sx={{ fontSize: "0.85em" }}>
                /api/v1/list-entities
              </Box>
              ; the SPA bundles the viewer shell.
            </Typography>
          </Paper>
        </Box>
      )}
    </Box>
  );
}
