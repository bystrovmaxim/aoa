// src/components/diagrams/DiagramShell/DiagramShell.tsx
import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

export type DiagramShellProps = {
  loading: boolean;
  error: string | null;
  children: ReactNode;
};

/** Shared loading overlay and error strip for diagram viewers. */
export function DiagramShell({ loading, error, children }: DiagramShellProps) {
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
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            display: "grid",
            placeItems: "center",
            zIndex: 2,
            bgcolor: "rgba(255,255,255,0.6)",
          }}
        >
          <CircularProgress size={40} />
        </Box>
      )}
      {children}
    </Box>
  );
}
