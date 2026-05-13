// packages/aoa-maxitor/client/src/features/diagrams/shared/zoom_toolbar.tsx
import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";

export type ZoomToolbarProps = {
  zoomPct: number | string;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
  /** Optional trailing controls (e.g. ERD layout presets + one-hop). */
  children?: ReactNode;
};

/** Ghost zoom buttons — same visual language as the former ``#zoom-toolbar`` (no card chrome). */
const ZOOM_BTN_SX = {
  minWidth: 30,
  width: 30,
  maxWidth: 30,
  height: 30,
  minHeight: 30,
  p: 0,
  fontSize: 15,
  fontWeight: 500,
  lineHeight: 1,
  border: "none",
  borderRadius: "8px",
  bgcolor: "transparent",
  color: "#64748b",
  boxShadow: "none",
  "&:hover": {
    bgcolor: "rgba(15, 23, 42, 0.06)",
    color: "#0f172a",
  },
} as const;

/** Zoom +/−/fit cluster for use inside a ``position: relative`` graph viewport. */
export function ZoomToolbar({ zoomPct, onZoomIn, onZoomOut, onFit, children }: ZoomToolbarProps) {
  const pctLabel = typeof zoomPct === "number" ? `${zoomPct}%` : zoomPct;
  return (
    <Box
      role="toolbar"
      aria-label="View controls"
      sx={{
        position: "absolute",
        bottom: 10,
        left: 10,
        zIndex: 40,
        display: "flex",
        flexDirection: "row",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "6px",
        bgcolor: "transparent",
        backdropFilter: "none",
        border: "none",
        borderRadius: 0,
        boxShadow: "none",
        p: "2px 0",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: "2px" }}>
        <Button
          variant="text"
          disableRipple
          onClick={onZoomIn}
          aria-label="Zoom in"
          sx={ZOOM_BTN_SX}
        >
          +
        </Button>
        <Button
          variant="text"
          disableRipple
          onClick={onZoomOut}
          aria-label="Zoom out"
          sx={ZOOM_BTN_SX}
        >
          −
        </Button>
        <Button
          variant="text"
          disableRipple
          onClick={onFit}
          aria-label="Fit to window"
          sx={ZOOM_BTN_SX}
        >
          ⊡
        </Button>
        <Typography
          component="span"
          sx={{
            minWidth: "3.1em",
            textAlign: "center",
            fontSize: 11,
            fontVariantNumeric: "tabular-nums",
            color: "#64748b",
            userSelect: "none",
            pl: "4px",
            pr: "6px",
            lineHeight: 1,
          }}
        >
          {pctLabel}
        </Typography>
      </Box>
      {children}
    </Box>
  );
}
