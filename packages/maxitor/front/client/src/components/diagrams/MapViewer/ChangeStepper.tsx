// src/components/diagrams/MapViewer/ChangeStepper.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Paper from "@mui/material/Paper";
import Popper from "@mui/material/Popper";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { PillArrow, PillChevron, PillDivider, pillSx } from "@/components/history/VersionButton";
import { changeLines, useChangeStepping, type ChangeLine } from "@/lib/changeStepping";
import { MARK_LOOK } from "@/lib/erdDiffCard";
import { nextChange } from "@/lib/mapDiff";
import { changeStepOfKey } from "@/lib/stepKeys";
import { useMirroredFocus, useShownPanel, type ChangeListState } from "@/rooms/focusStore";

const ROW_PX = 30;
const LIST_PX = 360;
/** How many rows are drawn past each edge of the list: only what can show is on the page. */
const OVERSCAN = 8;
const CLOSED: ChangeListState = { open: false, at: null, card: false, offset: 0 };
/** On a phone the top row has no room for it: it floats over the map's corner, clear of the zoom bar. */
const PHONE_SX = { position: "fixed", right: 10, bottom: 10, zIndex: 40, bgcolor: "rgba(255, 255, 255, 0.92)", boxShadow: "0 2px 10px rgba(0, 0, 0, 0.12)" } as const;

function GroupRow({ group, top }: { group: string; top: number }) {
  return (
    <Box sx={{ position: "absolute", top, left: 0, right: 0, height: ROW_PX, display: "flex", alignItems: "flex-end", px: "12px", pb: "5px", boxSizing: "border-box", fontSize: 11, fontWeight: 600, color: "#64748b", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
      {group}
    </Box>
  );
}

function ChangeRow({ line, top, chosen, onPick }: { line: Extract<ChangeLine, { entry: unknown }>; top: number; chosen: boolean; onPick: (position: number) => void }) {
  const { entry, position } = line;
  const look = MARK_LOOK[entry.status];
  return (
    <ButtonBase
      aria-current={chosen || undefined}
      onClick={() => onPick(position)}
      sx={{ position: "absolute", top, left: 0, right: 0, height: ROW_PX, display: "flex", justifyContent: "flex-start", gap: "8px", px: "12px", fontSize: 12.5, color: "#0f172a", textAlign: "left", bgcolor: chosen ? "rgba(15, 23, 42, 0.08)" : "transparent", "&:hover": { bgcolor: chosen ? "rgba(15, 23, 42, 0.1)" : "rgba(15, 23, 42, 0.05)" } }}
    >
      <Box component="span" sx={{ width: 10, flexShrink: 0, fontWeight: 700, color: look.colour }}>
        {look.sign}
      </Box>
      <Box component="span" sx={{ flex: 1, minWidth: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
        {entry.title}
      </Box>
      <Box component="span" sx={{ maxWidth: "40%", flexShrink: 0, fontSize: 11, color: "#64748b", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
        {entry.detail}
      </Box>
    </ButtonBase>
  );
}

/** Where the list opens: a little above the change the person stands on. */
function openingOffset(lines: readonly ChangeLine[], position: number | null): number {
  return Math.max(0, lines.findIndex((line) => "entry" in line && line.position === position) * ROW_PX - LIST_PX / 3);
}

type ChangeListProps = {
  lines: readonly ChangeLine[];
  position: number | null;
  following: boolean;
  /** The followed person's scroll, while following. */
  offset: number;
  onScrolled: (offset: number) => void;
  onPick: (position: number) => void;
};

/**
 * The list of changes, on the page only while it is open, so each opening starts from where the person stands. Only
 * the rows that can show are drawn, however long the list; which ones follows the list's own scroll.
 */
function ChangeList({ lines, position, following, offset, onScrolled, onPick }: ChangeListProps) {
  const list = useRef<HTMLDivElement | null>(null);
  const [scroll, setScroll] = useState(() => (following ? offset : openingOffset(lines, position)));

  useLayoutEffect(() => {
    if (list.current) list.current.scrollTop = scroll;
    onScrolled(scroll);
    // Only as it opens: after that the scroll is the person's own.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useLayoutEffect(() => {
    if (!following || !list.current) return;
    list.current.scrollTop = offset;
    setScroll(offset);
  }, [following, offset]);

  const first = Math.max(0, Math.floor(scroll / ROW_PX) - OVERSCAN);
  const last = Math.min(lines.length, first + Math.ceil(LIST_PX / ROW_PX) + 2 * OVERSCAN);
  return (
    <Box
      ref={list}
      data-pointer-frame="changes"
      data-testid="change-list"
      onScroll={(event) => {
        const next = event.currentTarget.scrollTop;
        setScroll(next);
        if (!following) onScrolled(next);
      }}
      sx={{ maxHeight: LIST_PX, overflowY: "auto", position: "relative", scrollbarWidth: "thin", overscrollBehavior: "contain" }}
    >
      <Box sx={{ position: "relative", height: lines.length * ROW_PX }}>
        {lines.slice(first, last).map((line, index) => {
          const top = (first + index) * ROW_PX;
          return "entry" in line ? <ChangeRow key={line.entry.key} line={line} top={top} chosen={line.position === position} onPick={onPick} /> : <GroupRow key={`group-${first + index}`} group={line.group} top={top} />;
        })}
      </Box>
    </Box>
  );
}

/**
 * Next and previous through a comparison's changes, beside the version button and apart from its arrows, which step
 * versions: one control with the same look, whose middle opens the list of the changes (spec 040, FR-025b, FR-025d).
 * It shows while a diagram steps, on every diagram that marks a comparison. In a room a follower sees it as its person
 * does: the position, the list and its scroll, and the pointer over it, through the ``changes`` panel and the
 * ``change-steps`` and ``changes`` frames (FR-025f).
 */
export function ChangeStepper({ compact = false }: { compact?: boolean }) {
  const stepping = useChangeStepping();
  const entries = stepping?.entries;
  const [ownOpen, setOwnOpen] = useState(false);
  const [ownOffset, setOwnOffset] = useState(0);
  const pill = useRef<HTMLDivElement | null>(null);
  const ownAt = stepping && stepping.position !== null ? (entries?.[stepping.position]?.key ?? null) : null;
  const own = useMemo<ChangeListState>(() => ({ open: ownOpen, at: ownAt, card: stepping?.card ?? false, offset: ownOffset }), [ownOpen, ownAt, stepping?.card, ownOffset]);
  const following = useMirroredFocus() !== null;
  const shown = useShownPanel<ChangeListState>(
    own,
    (value) => {
      setOwnOpen(value.open);
      setOwnOffset(value.offset);
    },
    (panels) => panels.changes ?? CLOSED,
    (value) => ({ changes: value }),
  );
  const lines = useMemo(() => changeLines(entries ?? []), [entries]);
  const open = shown.open && lines.length > 0;

  // A follower stands where the followed person stands; the view comes by following.
  const steppingRef = useRef(stepping);
  steppingRef.current = stepping;
  useEffect(() => {
    if (!following) return;
    const found = entries?.findIndex((entry) => entry.key === shown.at) ?? -1;
    steppingRef.current?.mirror(found >= 0 ? found : null, shown.card);
  }, [following, shown.at, shown.card, entries]);

  // Shift + ↑ ↓ step through the changes from anywhere on the page, when there are any.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const by = changeStepOfKey(event);
      const now = steppingRef.current;
      if (by === null || !now || now.entries.length === 0) return;
      event.preventDefault();
      if (!following) now.go(nextChange(now.position, by, now.entries.length));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [following]);

  useEffect(() => {
    if (!ownOpen) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOwnOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [ownOpen]);

  if (!stepping || !entries || entries.length === 0) return null;
  const { position } = stepping;
  const total = entries.length;
  const pick = (next: number) => {
    if (following) return;
    setOwnOpen(false);
    stepping.go(next);
  };
  const step = (by: -1 | 1) => {
    if (!following) stepping.go(nextChange(position, by, total));
  };
  const onClickAway = (event: MouseEvent | TouchEvent) => {
    if (!following && !(event.target instanceof Node && pill.current?.contains(event.target))) setOwnOpen(false);
  };
  const said = position === null ? `${total} ${total === 1 ? "change" : "changes"}` : compact ? `${position + 1}/${total}` : `${position + 1} of ${total}`;

  return (
    <>
      <Box ref={pill} role="group" aria-label="Changes" data-pointer-frame="change-steps" data-testid="change-stepper" sx={{ ...pillSx(open), flexShrink: 0, ...(compact && PHONE_SX) }}>
        <PillArrow delta={-1} label="Previous change" title="Previous change (Shift + ↑)" aria-keyshortcuts="Shift+ArrowUp" onStep={step} touch={compact} />
        <PillDivider />
        <ButtonBase
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-label={`Changes: ${said}`}
          onClick={() => !following && setOwnOpen((value) => !value)}
          sx={{ height: 28, pl: "8px", pr: "6px", gap: "6px", fontSize: 12.5, color: "#334155", whiteSpace: "nowrap", "&:hover": { bgcolor: "rgba(15, 23, 42, 0.06)" } }}
        >
          <b data-testid="change-position" style={{ color: "#0f172a", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
            {said}
          </b>
          <PillChevron />
        </ButtonBase>
        <PillDivider />
        <PillArrow delta={1} label="Next change" title="Next change (Shift + ↓)" aria-keyshortcuts="Shift+ArrowDown" onStep={step} touch={compact} />
      </Box>
      <Popper open={open} anchorEl={() => pill.current ?? document.body} placement={compact ? "top-end" : "bottom-start"} modifiers={[{ name: "offset", options: { offset: [0, 11] } }]} sx={{ zIndex: 1300 }}>
        <ClickAwayListener onClickAway={onClickAway}>
          <Paper
            role="dialog"
            aria-label="Pick a change"
            elevation={0}
            sx={{ width: 340, maxWidth: "calc(100vw - 20px)", py: "4px", boxSizing: "border-box", bgcolor: "#fff", border: "1px solid rgba(15, 23, 42, 0.1)", borderRadius: "10px", boxShadow: "0 12px 40px rgba(15, 23, 42, 0.16), 0 1px 2px rgba(15, 23, 42, 0.06)", overflow: "hidden" }}
          >
            <ChangeList lines={lines} position={position} following={following} offset={shown.offset} onScrolled={setOwnOffset} onPick={pick} />
          </Paper>
        </ClickAwayListener>
      </Popper>
    </>
  );
}
