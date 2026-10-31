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
import { useMirroredFocus, useShownPanel, type Panels } from "@/rooms/focusStore";
import type { PaintSection } from "@/lib/erdPaint";
import { HiddenMark, type RowHidden } from "./HiddenMark";

/** One toggle row: a domain or an entity kind. */
export type ErdFilterRow = {
  key: string;
  label: string;
  iconSrc: string;
  on: boolean;
  /** Nothing of it is on screen under the other filters: its name is dimmed; whether it is on stays the user's. */
  absent?: boolean;
  /** What keeps a dimmed row off the screen, and the way to switch that on (spec 040, FR-028c). */
  hidden?: RowHidden;
};

export type ErdFilterPanelProps = {
  domainRows: ErdFilterRow[];
  kindRows: ErdFilterRow[];
  onToggleDomain: (key: string) => void;
  onToggleKind: (key: string) => void;
  /** The heading of ``kindRows``; on the map they are node types. */
  kindsTitle?: string;
  /** (spec 038) in Diff, the kinds of change — Added, Removed, Changed, Unchanged. */
  changeRows?: ErdFilterRow[];
  onToggleChange?: (key: string) => void;
  /** which section paints the diagram, chosen by the gear shift at the panel's foot; absent, none. */
  paint?: { source: PaintSection; onPaint: (source: PaintSection) => void } | null;
};

type SectionId = "domains" | "kinds" | "changes";


/**
 * the gear shift — one point per section joined by a line, like a gearbox's shift pattern, with no
 * words; left to right in the order the sections stand top to bottom. The painting section's point is the
 * stronger one; a click on another shifts the colours to its section.
 */
export function GearShift({ sections, source, onPaint, kindsTitle = "Kinds" }: { sections: readonly PaintSection[]; source: PaintSection; onPaint: (source: PaintSection) => void; kindsTitle?: string }) {
  const titles: Record<PaintSection, string> = { domains: "Domains", kinds: kindsTitle, changes: "Changes" };
  const step = 18;
  const width = step * (sections.length - 1) + 16;
  return (
    <Box role="radiogroup" aria-label="Paint the diagram by" sx={{ display: "inline-flex", position: "relative", width, height: 20 }}>
      <Box component="span" aria-hidden sx={{ position: "absolute", left: 8, right: 8, top: 9.5, height: "1px", bgcolor: "#cbd5e1" }} />
      {sections.map((section, index) => {
        const on = section === source;
        return (
          <Tooltip key={section} title={titles[section]} placement="bottom" disableInteractive>
            <Box
              component="button"
              type="button"
              role="radio"
              aria-checked={on}
              aria-label={`Paint by ${titles[section]}`}
              onClick={() => onPaint(section)}
              sx={{
                position: "absolute",
                left: index * step,
                top: 0,
                width: 16,
                height: 20,
                m: 0,
                p: 0,
                border: "none",
                bgcolor: "transparent",
                cursor: on ? "default" : "pointer",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                "& > span": {
                  width: on ? 8 : 6,
                  height: on ? 8 : 6,
                  borderRadius: "50%",
                  bgcolor: on ? "#475569" : "#fff",
                  border: on ? "none" : "1px solid #cbd5e1",
                  boxShadow: on ? "0 0 0 3px rgba(71, 85, 105, 0.12)" : "none",
                  transition: "all 120ms ease",
                },
                "&:hover > span": { borderColor: "#94a3b8" },
                "&:focus-visible": { outline: "2px solid rgba(59, 130, 246, 0.45)", outlineOffset: 1, borderRadius: "50%" },
              }}
            >
              <span />
            </Box>
          </Tooltip>
        );
      })}
    </Box>
  );
}

/** The panel's fixed width: the production Domains legend measured 148 CSS px; labels cut, never widen it. */
export const ERD_FILTER_PANEL_WIDTH = 148;
const ROW_OFF_OPACITY = 0.42;
/** A row's name when nothing of it is on screen. */
const ABSENT_LABEL_OPACITY = 0.4;
// The panel stops above the zoom toolbar: its top inset (12) + the toolbar's bottom offset (10) +
// its height (30 px buttons, 44 px on touch, plus 2 px padding each side) + 12 px of air.
const ROOM_BELOW_DESKTOP = 12 + 10 + 34 + 12;
const ROOM_BELOW_TOUCH = 12 + 10 + 48 + 12;

/** A label that is cut with an ellipsis and shows its full text in a tooltip only when it was cut. */
function RowLabel({ text, absent = false }: { text: string; absent?: boolean }) {
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
        sx={{ ...legendRowLabelSx, minWidth: 0, display: "block", opacity: absent ? ABSENT_LABEL_OPACITY : 1, transition: "opacity 120ms ease" }}
      >
        {text}
      </Typography>
    </Tooltip>
  );
}

/** A toggle row with today's legend chrome: the disk, the label, dimmed when off. */
function FilterRow({ row, onToggle, why, onWhy }: { row: ErdFilterRow; onToggle: (key: string) => void; why: string | null; onWhy: (key: string | null) => void }) {
  const toggle = (
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
      <RowLabel text={row.label} absent={row.absent} />
    </Box>
  );
  if (!row.hidden) return toggle;
  return (
    <Box sx={{ position: "relative", minWidth: 0, pr: "18px" }}>
      {toggle}
      <HiddenMark row={row.key} label={row.label} iconSrc={row.iconSrc} hidden={row.hidden} why={why} onWhy={onWhy} />
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
 * Exactly one section is open at a time (on mount, the one that paints, else Domains); opening one
 * folds the other and clicking the open one folds it; moving the gear shift opens the section it
 * paints by, and opening a section by hand leaves the paint alone. The Kinds section exists only when the graph has more than one kind. The
 * panel stops above the zoom toolbar and scrolls inside itself. On a narrow screen it starts as a
 * "Filter" pill; opened, it shows the sections straight away, without the word "Filter".
 */
export function ErdFilterPanel({ domainRows, kindRows, onToggleDomain, onToggleKind, kindsTitle = "Kinds", changeRows = [], onToggleChange, paint = null }: ErdFilterPanelProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  // The section that paints is the one open first; without a gear shift, Domains (spec 040, FR-032).
  const [ownOpen, setOpen] = useState<SectionId | null>(paint?.source ?? "domains");
  const [ownCollapsed, setCollapsed] = useState(true);
  // While following, the panel shows as the followed person has it (spec 029, FR-010).
  const shown = useShownPanel<Panels["filter"]>(
    isMobile && ownCollapsed ? null : (ownOpen ?? "open"),
    (value) => {
      setCollapsed(value === null);
      if (value !== null) setOpen(value === "open" ? null : value);
    },
    (panels) => panels.filter,
    (value) => ({ filter: value }),
  );
  const collapsed = shown === null;
  const open: SectionId | null = shown === null ? ownOpen : shown === "open" ? null : shown;
  const toggleSection = (id: SectionId) => setOpen((prev) => (prev === id ? null : id));
  // The dimmed row whose card is open; while following, the followed person's (spec 040, FR-028c).
  const [ownWhy, setOwnWhy] = useState<string | null>(null);
  const why = useShownPanel<string | null>(
    ownWhy,
    setOwnWhy,
    (panels) => panels.why ?? null,
    (value) => ({ why: value }),
  );
  const following = useMirroredFocus() !== null;
  const onWhy = (key: string | null) => {
    if (!following) setOwnWhy(key);
  };
  // Moving the gear shift opens the section it paints by; the accordion folds the others (spec 040, FR-031).
  const shiftPaint = (source: PaintSection) => {
    setOpen(source);
    paint?.onPaint(source);
  };
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
  const paintSections: PaintSection[] = ["domains", ...(showKinds ? (["kinds"] as const) : []), ...(changeRows.length > 0 && onToggleChange ? (["changes"] as const) : [])];

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
            <FilterRow key={row.key} row={row} onToggle={onToggleDomain} why={why} onWhy={onWhy} />
          ))}
        </Box>
      )}
      {showKinds && (
        <Box>
          <SectionHeader title={kindsTitle} open={open === "kinds"} onClick={() => toggleSection("kinds")} />
          {open === "kinds" && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, pb: 1 }}>
              {kindRows.map((row) => (
                <FilterRow key={row.key} row={row} onToggle={onToggleKind} why={why} onWhy={onWhy} />
              ))}
            </Box>
          )}
        </Box>
      )}
      {changeRows.length > 0 && onToggleChange && (
        <Box>
          <SectionHeader title="Changes" open={open === "changes"} onClick={() => toggleSection("changes")} />
          {open === "changes" && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, pb: 1 }}>
              {changeRows.map((row) => (
                <FilterRow key={row.key} row={row} onToggle={onToggleChange} why={why} onWhy={onWhy} />
              ))}
            </Box>
          )}
        </Box>
      )}
      {paint && paintSections.length > 1 && (
        // the gear shift, the panel's last block, centred: one point per section above, in their order.
        <Box sx={{ borderTop: "1px solid rgba(0,0,0,0.07)", display: "flex", justifyContent: "center", pt: 0.75, pb: 0.25 }}>
          <GearShift sections={paintSections} source={paint.source} onPaint={shiftPaint} kindsTitle={kindsTitle} />
        </Box>
      )}
    </Box>
  );
}
