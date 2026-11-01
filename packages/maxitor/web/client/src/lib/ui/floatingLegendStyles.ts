// src/lib/ui/floatingLegendStyles.ts
/**
 * Shared chrome for floating graph/ERD legend panels (graph node types, domain toggles).
 * Keep typography, spacing, and disk frame aligned across viewers.
 */

import type { SxProps, Theme } from "@mui/material/styles";

export const floatingLegendPanelSx: SxProps<Theme> = {
  position: "absolute",
  top: 12,
  left: 12,
  zIndex: 40,
  display: "flex",
  flexDirection: "column",
  gap: 0.75,
  p: 1.25,
  minWidth: 132,
  maxWidth: 260,
  maxHeight: "calc(100% - 60px)",
  overflowY: "auto",
  bgcolor: "rgba(255,255,255,0.88)",
  backdropFilter: "blur(8px)",
  border: "1px solid",
  borderColor: "rgba(0,0,0,0.08)",
  borderRadius: 1,
  boxShadow: "0 2px 10px rgba(0,0,0,0.07)",
};

export const floatingLegendTitleSx: SxProps<Theme> = {
  fontWeight: 600,
  fontSize: "10px",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  color: "text.secondary",
  mb: 0.25,
};

export const legendRowSx: SxProps<Theme> = {
  display: "flex",
  alignItems: "center",
  gap: 1,
};

/** 20×20 disk frame — matches graph node-type legend. */
export const legendDiskImgSx: SxProps<Theme> = {
  borderRadius: "50%",
  border: "1px solid rgba(0,0,0,0.12)",
  flexShrink: 0,
};

export const legendRowLabelSx: SxProps<Theme> = {
  fontSize: 11,
  color: "text.primary",
};

/** Centered copy on dotted diagram canvas when the visible graph is empty (use-case / ERD). */
export const diagramCanvasEmptyMessageSx: SxProps<Theme> = {
  position: "absolute",
  left: "50%",
  top: "50%",
  transform: "translate(-50%, -50%)",
  zIndex: 20,
  pointerEvents: "none",
  maxWidth: "90%",
  textAlign: "center",
};
