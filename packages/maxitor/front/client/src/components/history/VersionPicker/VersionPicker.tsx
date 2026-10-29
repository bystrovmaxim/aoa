// src/components/history/VersionPicker/VersionPicker.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Drawer from "@mui/material/Drawer";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Paper from "@mui/material/Paper";
import Popper from "@mui/material/Popper";
import Tooltip from "@mui/material/Tooltip";
import { useEffect, useRef, useState, type ReactNode } from "react";
import type { HistoryVersion } from "@/api/history";
import { VersionTrack } from "@/components/history/VersionTrack";
import { pickerSubtitle } from "@/model/historyMode";

/** Width of the picker card and of its track — the mockup's 760 and 718. */
const WIDTH = 760;
const TRACK_WIDTH = 718;

export type VersionPickerProps = {
  /** The button the picker opens under; ``null`` keeps it closed. */
  anchor: HTMLElement | null;
  onClose: () => void;
  title: string;
  versions: readonly HistoryVersion[];
  live: string | null;
  /** The newest version's sha when Live runs exactly its graph: the track draws them as one point. */
  liveIs?: string | null;
  /** Pull requests still open that change the graph, drawn after Live by their state. */
  proposals?: readonly HistoryVersion[];
  value: string | null;
  onChange: (b: string) => void;
  /** The link **Copy link** hands out: this version, the key after ``#key=``. */
  link: string;
  /** Under the track: the chosen version's message. */
  children?: ReactNode;
  /** On a phone the picker is a sheet from the bottom, its track as wide as the screen (FR-031). */
  phone?: boolean;
};

/** A 14 px stroke icon of the mode switch, drawn as the mockup draws it. */
function ModeIcon({ children }: { children: ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" width={14} height={14} aria-hidden style={{ display: "block" }}>
      <g fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round">
        {children}
      </g>
    </svg>
  );
}

const MODES = [
  { value: "one", label: "One", icon: <rect x={5} y={5} width={14} height={14} rx={2} /> },
  {
    value: "diff",
    label: "Diff",
    icon: (
      <>
        <rect x={4} y={4} width={16} height={16} rx={2} />
        <path d="M8.5 9.5h4M10.5 7.5v4M8.5 15.5h4" />
      </>
    ),
  },
  {
    value: "split",
    label: "Side by side",
    icon: (
      <>
        <rect x={3.5} y={5} width={17} height={14} rx={2} />
        <path d="M12 5v14" />
      </>
    ),
  },
] as const;

/** The mode switch: One is on; Diff and Side by side are greyed out and "comes later". */
function ModeSwitch() {
  return (
    <Box role="radiogroup" aria-label="Mode" sx={{ display: "inline-flex", flexShrink: 0, border: "1px solid rgba(15, 23, 42, 0.12)", borderRadius: "8px", p: "2px", gap: "2px" }}>
      {MODES.map((mode) => {
        const on = mode.value === "one";
        const item = (
          <Box
            component="span"
            role="radio"
            aria-checked={on}
            aria-disabled={on ? undefined : "true"}
            sx={{
              height: 24,
              px: "10px",
              display: "inline-flex",
              alignItems: "center",
              gap: "5px",
              borderRadius: "6px",
              fontSize: 12,
              whiteSpace: "nowrap",
              color: on ? "#0f172a" : "#475569",
              fontWeight: on ? 600 : 400,
              bgcolor: on ? "rgba(15, 23, 42, 0.08)" : "transparent",
              opacity: on ? 1 : 0.45,
              cursor: on ? "default" : "not-allowed",
            }}
          >
            <ModeIcon>{mode.icon}</ModeIcon>
            {mode.label}
          </Box>
        );
        return on ? (
          <Box component="span" key={mode.value} sx={{ display: "inline-flex" }}>
            {item}
          </Box>
        ) : (
          <Tooltip key={mode.value} title="comes later" describeChild>
            {item}
          </Tooltip>
        );
      })}
    </Box>
  );
}

/**
 * The picker (spec 037, FR-014, FR-015), laid out as the mockup lays it out: a card under the version
 * button at the left of the top row; the service's name and how many versions it has on the left of the
 * head, the mode switch on the right — One on, Diff and Side by side greyed out, "comes later" — with
 * **Copy link** as a small link icon before it; then the track, then the chosen version's message. It
 * starts closed, a click outside or Escape closes it, and choosing a version leaves it open. On a phone
 * it is a sheet from the bottom with the same head, track and message, every point a 44 px touch target.
 */
export function VersionPicker({ anchor, onClose, title, versions, live, liveIs = null, proposals = [], value, onChange, link, children, phone = false }: VersionPickerProps) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard unavailable: nothing to confirm.
    }
  }

  useEffect(() => {
    if (!anchor || phone) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [anchor, phone, onClose]);

  // The button moves when the sidebar collapses or opens: the card follows it.
  const popper = useRef<{ update(): unknown } | null>(null);
  useEffect(() => {
    const row = anchor?.parentElement;
    if (!row || phone) return;
    const follow = new ResizeObserver(() => void popper.current?.update());
    follow.observe(row);
    return () => follow.disconnect();
  }, [anchor, phone]);

  const trackWidth = phone ? Math.max(240, window.innerWidth - 32) : TRACK_WIDTH;
  const content = (
    <>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1.5, mb: "12px" }}>
        <Box sx={{ minWidth: 0 }}>
          <Box sx={{ fontSize: 13, fontWeight: 600, color: "#0f172a" }}>{title}</Box>
          <Box sx={{ fontSize: 11.5, color: "#64748b", mt: "1px" }}>{pickerSubtitle(versions.length, Boolean(live), proposals.length)}</Box>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Tooltip title={copied ? "Link copied" : "Copy link"}>
            <ButtonBase
              onClick={() => void copy()}
              aria-label={copied ? "Link copied" : "Copy link"}
              sx={{ width: 28, height: 28, borderRadius: "8px", color: "#64748b", "&:hover": { bgcolor: "rgba(15, 23, 42, 0.06)", color: "#0f172a" } }}
            >
              <svg viewBox="0 0 24 24" width={15} height={15} aria-hidden>
                <g fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round">
                  <path d="M10 13.5a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1.2 1.2" />
                  <path d="M14 10.5a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1.2-1.2" />
                </g>
              </svg>
            </ButtonBase>
          </Tooltip>
          <ModeSwitch />
        </Box>
      </Box>
      <VersionTrack versions={versions} live={live} liveIs={liveIs} proposals={proposals} value={value} onChange={onChange} width={trackWidth} touch={phone} />
      {children}
    </>
  );

  if (phone) {
    return (
      <Drawer anchor="bottom" open={anchor !== null} onClose={onClose} slotProps={{ paper: { role: "dialog", "aria-label": "Pick a version", sx: { p: 2, borderTopLeftRadius: 12, borderTopRightRadius: 12 } } }}>
        {content}
      </Drawer>
    );
  }

  // Not modal: a click outside still does what it is for — the sidebar's button collapses the sidebar, a page
  // opens — and the picker stays open over the sidebar's clicks, as the mockup shows it beside a collapsed
  // sidebar. A click on the diagram, or Escape, closes it.
  const onClickAway = (event: MouseEvent | TouchEvent) => {
    const target = event.target as Element | null;
    if (target?.closest(".MuiDrawer-root, .MuiTooltip-popper") || (anchor && target && anchor.contains(target))) return;
    onClose();
  };

  return (
    <Popper popperRef={(instance) => void (popper.current = instance)} open={anchor !== null} anchorEl={anchor} placement="bottom-start" modifiers={[{ name: "offset", options: { offset: [0, 11] } }]} sx={{ zIndex: 1300 }}>
      <ClickAwayListener onClickAway={onClickAway}>
        <Paper
          role="dialog"
          aria-label="Pick a version"
          elevation={0}
          sx={{
            width: WIDTH,
            boxSizing: "border-box",
            maxWidth: "calc(100vw - 20px)",
            // Never taller than the workspace: the mockup's card scrolls as a whole.
            maxHeight: "calc(100vh - 60px)",
            overflowY: "auto",
            p: "14px 20px 12px",
            bgcolor: "#fff",
            border: "1px solid rgba(15, 23, 42, 0.1)",
            borderRadius: "10px",
            boxShadow: "0 12px 40px rgba(15, 23, 42, 0.16), 0 1px 2px rgba(15, 23, 42, 0.06)",
            scrollbarWidth: "thin",
            overscrollBehavior: "contain",
          }}
        >
          {content}
        </Paper>
      </ClickAwayListener>
    </Popper>
  );
}
