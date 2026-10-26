// src/components/ui/ErdFilterPanel/ErdFilterPanel.tsx
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { floatingLegendPanelSx, floatingLegendTitleSx, legendDiskImgSx, legendRowLabelSx, legendRowSx } from "@/lib/ui";

/** One toggle row: a domain or an entity kind. */
export type ErdFilterRow = {
  key: string;
  label: string;
  iconSrc: string;
  on: boolean;
};

export type ErdFilterPanelProps = {
  domainRows: ErdFilterRow[];
  kindRows: ErdFilterRow[];
  onToggleDomain: (key: string) => void;
  onToggleKind: (key: string) => void;
};

type SectionId = "domains" | "kinds";

/** The panel's fixed width: the production Domains legend measured 148 CSS px; labels cut, never widen it. */
export const ERD_FILTER_PANEL_WIDTH = 148;
const ROW_OFF_OPACITY = 0.42;
// The panel stops above the zoom toolbar: its top inset (12) + the toolbar's bottom offset (10) +
// its height (30 px buttons, 44 px on touch, plus 2 px padding each side) + 12 px of air.
const ROOM_BELOW_DESKTOP = 12 + 10 + 34 + 12;
const ROOM_BELOW_TOUCH = 12 + 10 + 48 + 12;

/** A label that is cut with an ellipsis and shows its full text in a tooltip only when it was cut. */
function RowLabel({ text }: { text: string }) {
  const ref = useRef<HTMLSpanElement | null>(null);
  const [cut, setCut] = useState(false);
  return (
    <Tooltip title={cut ? text : ""} placement="right" disableInteractive>
      <Typography
        ref={ref}
        component="span"
        variant="caption"
        noWrap
        data-testid="erd-filter-label"
        onMouseEnter={() => {
          const el = ref.current;
          setCut(el !== null && el.scrollWidth > el.clientWidth);
        }}
        sx={{ ...legendRowLabelSx, minWidth: 0, display: "block" }}
      >
        {text}
      </Typography>
    </Tooltip>
  );
}

/** A toggle row with today's legend chrome: the disk, the label, dimmed when off. */
function FilterRow({ row, onToggle }: { row: ErdFilterRow; onToggle: (key: string) => void }) {
  return (
    <Box
      component="button"
      type="button"
      onClick={() => onToggle(row.key)}
      aria-pressed={row.on}
      aria-label={row.label}
      sx={{
        ...legendRowSx,
        m: 0,
        p: 0,
        width: "100%",
        minWidth: 0,
        border: "none",
        bgcolor: "transparent",
        cursor: "pointer",
        textAlign: "left",
        borderRadius: 0.5,
        opacity: row.on ? 1 : ROW_OFF_OPACITY,
        transition: "opacity 120ms ease",
        "&:hover": { opacity: row.on ? 1 : Math.min(ROW_OFF_OPACITY + 0.22, 0.85) },
        "&:focus-visible": { outline: "2px solid rgba(59, 130, 246, 0.45)", outlineOffset: 1 },
      }}
    >
      <Box component="img" src={row.iconSrc} width={20} height={20} alt="" sx={legendDiskImgSx} />
      <RowLabel text={row.label} />
    </Box>
  );
}

/** A section header: the chevron and the name, nothing else. */
function SectionHeader({
  title,
  open,
  onClick,
  trailing,
}: {
  title: string;
  open: boolean;
  onClick: () => void;
  trailing?: ReactNode;
}) {
  return (
    <Box sx={{ display: "flex", alignItems: "center" }}>
      <Box
        component="button"
        type="button"
        onClick={onClick}
        aria-expanded={open}
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          gap: 0.5,
          m: 0,
          px: 0,
          py: 0.75,
          border: "none",
          bgcolor: "transparent",
          cursor: "pointer",
          textAlign: "left",
          "&:focus-visible": { outline: "2px solid rgba(59, 130, 246, 0.45)", outlineOffset: 1 },
        }}
      >
        <ExpandMoreIcon
          sx={{
            fontSize: 16,
            color: "text.secondary",
            transform: open ? "none" : "rotate(-90deg)",
            transition: "transform 120ms ease",
            "@media (prefers-reduced-motion: reduce)": { transition: "none" },
          }}
        />
        <Typography variant="caption" sx={{ ...floatingLegendTitleSx, mb: 0 }}>
          {title}
        </Typography>
      </Box>
      {trailing}
    </Box>
  );
}

/**
 * The ERD's one filter panel: Domains and Kinds as a strict accordion, 148 px wide whatever it holds.
 *
 * Exactly one section is open at a time (Domains on mount); opening one folds the other and clicking
 * the open one folds it. The Kinds section exists only when the graph has more than one kind. The
 * panel stops above the zoom toolbar and scrolls inside itself. On a narrow screen it starts as a
 * "Filter" pill; opened, it shows the sections straight away, without the word "Filter".
 */
export function ErdFilterPanel({ domainRows, kindRows, onToggleDomain, onToggleKind }: ErdFilterPanelProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const [open, setOpen] = useState<SectionId | null>("domains");
  const [collapsed, setCollapsed] = useState(true);
  const toggleSection = (id: SectionId) => setOpen((prev) => (prev === id ? null : id));
  // A native listener: React's synthetic stopPropagation would run after the event reached the canvas.
  const panelRef = useRef<HTMLElement | null>(null);
  const showPanel = !(isMobile && collapsed);
  useEffect(() => {
    const el = panelRef.current;
    if (!el) return undefined;
    const keepWheel = (event: WheelEvent) => event.stopPropagation();
    el.addEventListener("wheel", keepWheel, { passive: true });
    return () => el.removeEventListener("wheel", keepWheel);
  }, [showPanel]);

  if (isMobile && collapsed) {
    return (
      <Box
        component="button"
        type="button"
        aria-label="Show filter"
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
          Filter
        </Typography>
        <ExpandMoreIcon sx={{ fontSize: 16, color: "text.secondary" }} />
      </Box>
    );
  }

  const closeButton = isMobile ? (
    <IconButton size="small" onClick={() => setCollapsed(true)} aria-label="Hide filter" sx={{ p: 0.25, mr: -0.5 }}>
      <CloseIcon sx={{ fontSize: 14 }} />
    </IconButton>
  ) : null;
  const showKinds = kindRows.length > 1;

  return (
    <Box
      component="aside"
      aria-label="Filter"
      data-testid="erd-filter-panel"
      ref={panelRef}
      sx={{
        ...floatingLegendPanelSx,
        width: ERD_FILTER_PANEL_WIDTH,
        minWidth: ERD_FILTER_PANEL_WIDTH,
        maxWidth: ERD_FILTER_PANEL_WIDTH,
        maxHeight: `calc(100% - ${isMobile ? ROOM_BELOW_TOUCH : ROOM_BELOW_DESKTOP}px)`,
        overflowY: "auto",
        overscrollBehavior: "contain",
        gap: 0,
        py: 0.5,
        boxSizing: "border-box",
      }}
    >
      <SectionHeader title="Domains" open={open === "domains"} onClick={() => toggleSection("domains")} trailing={closeButton} />
      {open === "domains" && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, pb: 1 }}>
          {domainRows.map((row) => (
            <FilterRow key={row.key} row={row} onToggle={onToggleDomain} />
          ))}
        </Box>
      )}
      {showKinds && (
        <Box sx={{ borderTop: "1px solid rgba(0,0,0,0.07)" }}>
          <SectionHeader title="Kinds" open={open === "kinds"} onClick={() => toggleSection("kinds")} />
          {open === "kinds" && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, pb: 1 }}>
              {kindRows.map((row) => (
                <FilterRow key={row.key} row={row} onToggle={onToggleKind} />
              ))}
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}
