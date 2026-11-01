// src/components/history/VersionPicker/VersionPicker.tsx
import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Paper from "@mui/material/Paper";
import Popper from "@mui/material/Popper";
import Tooltip from "@mui/material/Tooltip";
import { useEffect, useRef, type KeyboardEvent as ReactKeyboardEvent, type ReactNode, type RefObject } from "react";
import type { HistoryVersion } from "@/api/history";
import { VersionTrack } from "@/components/history/VersionTrack";
import type { Range } from "@/lib/versionRange";
import { TrackLegend } from "./TrackLegend";
import { pickerSubtitle } from "@/model/historyMode";

/** Width of the picker card and of its track — the mockup's 760 and 718. */
const WIDTH = 760;
const TRACK_WIDTH = 718;

export type VersionPickerProps = {
  /** The button the picker opens under, as a ref: it is asked where it stands each time, so a button drawn anew still holds the picker; ``null`` keeps it closed. */
  anchor: RefObject<HTMLElement | null> | null;
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
  /** Under the track: the chosen version's message — in Diff, B's, on the right. */
  children?: ReactNode;
  /** In Diff: A's message, on the left of B's — over it on a phone (spec 038, FR-030). */
  older?: ReactNode;
  /** In Diff, under the two messages: the versions between A and B (FR-031). */
  between?: ReactNode;
  /** On a phone the picker is a sheet from the bottom, its track as wide as the screen (FR-031). */
  phone?: boolean;
  /** One version or two (spec 038): in Diff the track holds ``range``. */
  mode?: PickerMode;
  /** Switch between One and Diff; without it the switch shows One alone as on. */
  onMode?: (mode: PickerMode) => void;
  /** Whether Diff can be picked: two points or more (spec 038, FR-015). */
  diffOffered?: boolean;
  range?: Range | null;
  onRange?: (range: Range) => void;
};

/** What the switch picks in this step: one version, or two compared. Side by side comes later. */
export type PickerMode = "one" | "diff" | "split";

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

/**
 * The mode switch (spec 038, FR-009, FR-015): One and Diff, Diff greyed out with "needs two versions" where the
 * history has fewer than two points; Side by side too (spec 044).
 */
function ModeSwitch({ value, onChange, diffOffered }: { value: PickerMode; onChange?: (mode: PickerMode) => void; diffOffered: boolean }) {
  return (
    <Box role="radiogroup" aria-label="Mode" sx={{ display: "inline-flex", flexShrink: 0, border: "1px solid rgba(15, 23, 42, 0.12)", borderRadius: "8px", p: "2px", gap: "2px" }}>
      {MODES.map((mode) => {
        const on = mode.value === value;
        const hint = mode.value !== "one" && !diffOffered ? "needs two versions" : null;
        const enabled = hint === null && Boolean(onChange);
        const item = (
          <Box
            component="span"
            role="radio"
            aria-checked={on}
            aria-disabled={on || enabled ? undefined : "true"}
            tabIndex={enabled && !on ? 0 : undefined}
            onClick={() => enabled && !on && onChange?.(mode.value as PickerMode)}
            onKeyDown={(event: ReactKeyboardEvent) => {
              if (enabled && !on && (event.key === "Enter" || event.key === " ")) {
                event.preventDefault();
                onChange?.(mode.value as PickerMode);
              }
            }}
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
              opacity: on || enabled ? 1 : 0.45,
              cursor: on ? "default" : enabled ? "pointer" : "not-allowed",
            }}
          >
            <ModeIcon>{mode.icon}</ModeIcon>
            {mode.label}
          </Box>
        );
        return hint === null || on ? (
          <Box component="span" key={mode.value} sx={{ display: "inline-flex" }}>
            {item}
          </Box>
        ) : (
          <Tooltip key={mode.value} title={hint} describeChild>
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
 * head, the mode switch on the right — One, Diff (spec 038) and Side by side (spec 044) — with
 * an "i" before the mode switch that explains the track's marks; then the track, then the chosen version's message — in Diff A's
 * on the left and B's on the right, stacked on a phone, the versions between them below. The
 * link to share is the address bar itself, which keeps a private history's key after ``#key=``. It
 * starts closed, a click outside or Escape closes it, and choosing a version leaves it open. On a phone
 * it is a sheet from the bottom with the same head, track and message, every point a 44 px touch target.
 */
export function VersionPicker({
  anchor,
  onClose,
  title,
  versions,
  live,
  liveIs = null,
  proposals = [],
  value,
  onChange,
  children,
  phone = false,
  mode = "one",
  onMode,
  diffOffered = false,
  range = null,
  onRange,
  older,
  between,
}: VersionPickerProps) {
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
    const row = anchor?.current?.parentElement;
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
          <Box sx={{ display: "flex", alignItems: "center", gap: "5px", fontSize: 11.5, lineHeight: "16px", color: "#64748b", mt: "1px" }}>
            <span>{pickerSubtitle(versions.length, Boolean(live), proposals.length)}</span>
          </Box>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <TrackLegend />
          <ModeSwitch value={mode} onChange={onMode} diffOffered={diffOffered} />
        </Box>
      </Box>
      <VersionTrack
        versions={versions}
        live={live}
        liveIs={liveIs}
        proposals={proposals}
        value={value}
        onChange={onChange}
        width={trackWidth}
        touch={phone}
        range={mode !== "one" ? range : null}
        onRange={onRange}
      />
      {mode !== "one" && older !== undefined ? (
        <>
          {/* No header above either message: A is on the left and B on the right, as their handles stand. */}
          <Box sx={{ display: "grid", gridTemplateColumns: phone ? "minmax(0, 1fr)" : "minmax(0, 1fr) minmax(0, 1fr)", columnGap: 2 }}>
            <Box data-testid="message-a" sx={{ minWidth: 0, display: "flex", flexDirection: "column" }}>
              {older}
            </Box>
            <Box data-testid="message-b" sx={{ minWidth: 0, display: "flex", flexDirection: "column" }}>
              {children}
            </Box>
          </Box>
          {between}
        </>
      ) : (
        children
      )}
    </>
  );

  if (phone) {
    return (
      <Drawer anchor="bottom" open={anchor !== null} onClose={onClose} slotProps={{ paper: { role: "dialog", "aria-label": "Pick a version", ...{ "data-pointer-frame": "versions" }, sx: { p: 2, borderTopLeftRadius: 12, borderTopRightRadius: 12 } } }}>
        {content}
      </Drawer>
    );
  }

  // Not modal: a click outside still does what it is for — the sidebar's button collapses the sidebar, a page
  // opens — and the picker stays open over the sidebar's clicks, as the mockup shows it beside a collapsed
  // sidebar. A click on the diagram, or Escape, closes it.
  const onClickAway = (event: MouseEvent | TouchEvent) => {
    const target = event.target as Element | null;
    if (target?.closest(".MuiDrawer-root, .MuiTooltip-popper") || (anchor?.current && target && anchor.current.contains(target))) return;
    onClose();
  };

  return (
    <Popper popperRef={(instance) => void (popper.current = instance)} open={anchor !== null} anchorEl={() => anchor?.current ?? document.body} placement="bottom-start" modifiers={[{ name: "offset", options: { offset: [0, 11] } }]} sx={{ zIndex: 1300 }}>
      <ClickAwayListener onClickAway={onClickAway}>
        <Paper
          role="dialog"
          aria-label="Pick a version"
          // A pointer over the picker lands on the same place of it for a follower, wherever it opened (spec 038).
          data-pointer-frame="versions"
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
