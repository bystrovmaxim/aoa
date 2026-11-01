// src/components/ui/ZoomToolbar/ToolbarIcons.tsx
import ButtonBase from "@mui/material/ButtonBase";
import Tooltip from "@mui/material/Tooltip";
import type { ReactNode } from "react";
import { setHoverCardsOn, useHoverCardsOn } from "@/lib/hoverCardsOn";

const ICON_COLOUR = "#64748b";
/** The colour of what is on, the layout presets' own. */
const ON_COLOUR = "#1d4ed8";

function IconButton({ label, on, testId, onClick, children }: { label: string; on?: boolean; testId: string; onClick: () => void; children: ReactNode }) {
  return (
    <Tooltip title={label} placement="top">
      <ButtonBase
        aria-label={label}
        aria-pressed={on}
        data-testid={testId}
        onClick={onClick}
        sx={{ width: 30, height: 30, borderRadius: "8px", fontSize: 15, color: on ? ON_COLOUR : ICON_COLOUR, "&:hover": { bgcolor: "rgba(15, 23, 42, 0.06)", color: on ? ON_COLOUR : "#0f172a" } }}
      >
        {/* The layout presets' thin stroke, at their size. */}
        <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          {children}
        </svg>
      </ButtonBase>
    </Tooltip>
  );
}

/** Collapse every table, or expand them: chevrons that close on a line, or open away from it. */
export function CollapseAllButton({ collapsed, onClick }: { collapsed: boolean; onClick: () => void }) {
  return (
    <IconButton label={collapsed ? "Expand all tables" : "Collapse all tables"} testId="collapse-all" onClick={onClick}>
      <path d="M4 12h16" />
      {collapsed ? <path d="M8 7l4-4 4 4M8 17l4 4 4-4" /> : <path d="M8 3l4 4 4-4M8 21l4-4 4 4" />}
    </IconButton>
  );
}

/** Switch the cards on and off; on at first. */
export function HoverCardsButton() {
  const on = useHoverCardsOn();
  return (
    <IconButton label={on ? "Hide cards on hover" : "Show cards on hover"} on={on} testId="hover-cards" onClick={() => setHoverCardsOn(!on)}>
      <path d="M4 5.5A1.5 1.5 0 0 1 5.5 4h13A1.5 1.5 0 0 1 20 5.5v10a1.5 1.5 0 0 1-1.5 1.5H11l-3.5 3.5V17h-2A1.5 1.5 0 0 1 4 15.5z" />
      <path d="M8 9h8M8 12.5h5" />
    </IconButton>
  );
}
