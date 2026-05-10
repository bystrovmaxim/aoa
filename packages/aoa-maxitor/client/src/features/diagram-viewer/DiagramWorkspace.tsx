// packages/aoa-maxitor/client/src/features/diagram-viewer/DiagramWorkspace.tsx
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

type DiagramWorkspaceProps = {
  diagramUrl: string | null;
};

export function DiagramWorkspace({ diagramUrl }: DiagramWorkspaceProps) {
  return (
    <Box
      component="main"
      sx={{
        flex: 1,
        minWidth: 0,
        display: "flex",
        flexDirection: "column",
        bgcolor: "grey.100",
      }}
    >
      {diagramUrl ? (
        <Box
          component="iframe"
          key={diagramUrl}
          title="Diagram viewer"
          src={diagramUrl}
          sx={{ border: 0, flex: 1, width: "100%", minHeight: 0 }}
        />
      ) : (
        <Box sx={{ flex: 1, display: "grid", placeItems: "center", p: 2 }}>
          <Paper variant="outlined" sx={{ maxWidth: 520, p: 3, borderRadius: 2 }}>
            <Typography variant="h5" component="h1" gutterBottom>
              Diagram workspace
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Open the interchange graph or an ERD. The viewer is Python-generated standalone HTML loaded here.
            </Typography>
          </Paper>
        </Box>
      )}
    </Box>
  );
}
