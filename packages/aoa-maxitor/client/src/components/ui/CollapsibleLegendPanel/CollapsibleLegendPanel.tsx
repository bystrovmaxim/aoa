// src/components/ui/CollapsibleLegendPanel/CollapsibleLegendPanel.tsx
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import { useState, type ReactNode } from "react";
import { floatingLegendPanelSx, floatingLegendTitleSx } from "@/lib/ui";

export type CollapsibleLegendPanelProps = {
  ariaLabel: string;
  title: string;
  children: ReactNode;
};

/**
 * Floating graph/ERD legend chrome (node types, domain toggles) — on mobile a full-height panel
 * pinned to the top-left corner would cover most of a ~375px canvas, so it starts collapsed to a
 * small pill there and expands on tap. Desktop keeps the original always-expanded panel.
 */
export function CollapsibleLegendPanel({ ariaLabel, title, children }: CollapsibleLegendPanelProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const [collapsed, setCollapsed] = useState(true);

  if (isMobile && collapsed) {
    return (
      <Box
        component="button"
        type="button"
        aria-label={`Show ${title.toLowerCase()} legend`}
        onClick={() => setCollapsed(false)}
        sx={{
          position: "absolute",
          top: 12,
          left: 12,
          zIndex: 40,
          display: "flex",
          alignItems: "center",
          gap: 0.5,
          m: 0,
          border: "1px solid",
          borderColor: "rgba(0,0,0,0.08)",
          borderRadius: 1,
          bgcolor: "rgba(255,255,255,0.88)",
          backdropFilter: "blur(8px)",
          boxShadow: "0 2px 10px rgba(0,0,0,0.07)",
          px: 1,
          py: 0.75,
          cursor: "pointer",
        }}
      >
        <Typography variant="caption" sx={{ ...floatingLegendTitleSx, mb: 0 }}>
          {title}
        </Typography>
        <ExpandMoreIcon sx={{ fontSize: 16, color: "text.secondary" }} />
      </Box>
    );
  }

  return (
    <Box component="aside" aria-label={ariaLabel} sx={floatingLegendPanelSx}>
      <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 1 }}>
        <Typography variant="caption" sx={floatingLegendTitleSx}>
          {title}
        </Typography>
        {isMobile && (
          <IconButton
            size="small"
            onClick={() => setCollapsed(true)}
            aria-label={`Hide ${title.toLowerCase()} legend`}
            sx={{ p: 0.25, mt: -0.5, mr: -0.5 }}
          >
            <CloseIcon sx={{ fontSize: 14 }} />
          </IconButton>
        )}
      </Box>
      {children}
    </Box>
  );
}
