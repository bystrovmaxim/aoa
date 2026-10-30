// src/components/history/VersionTrack/VersionTrack.tsx
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Popper from "@mui/material/Popper";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import type { HistoryVersion, ProposalState } from "@/api/history";
import { flagsOf, numbersOf, releaseOf, shortSha, versionNames } from "@/lib/versionNames";
import { DIRECT_LOOK, LIVE_LOOK, MERGED_LOOK, PROPOSAL_LOOK } from "./proposalLook";
import { VersionTip } from "./VersionTip";
import { thinLabels } from "./thinLabels";

/** Where the axis runs, where names stand under it, and the drawing's height — the mockup's. */
const AXIS_Y = 26;
const LABEL_Y = 52;
const HEIGHT = 64;
/** Room at each end of the axis. */
const PAD = 16;
/** The dashed gap before Live, in steps of the track (the mockup's 1.4). */
const LIVE_GAP_STEPS = 1.4;
/** The least distance between two points (FR-023, the mockup's rule): 24 px. */
export const MIN_STEP = 24;
/** The least distance, and the touch target, on a phone (FR-031). */
export const TOUCH_STEP = 44;
const INK = "#0f172a";
const MUTED = "#94a3b8";

export type VersionTrackProps = {
  versions: readonly HistoryVersion[];
  /** The running service whose graph is Live, or ``null``. */
  live: string | null;
  /** The chosen version: a short sha, ``live``, or ``null``. */
  value: string | null;
  onChange: (b: string) => void;
  /** Width of the visible part of the track. */
  width: number;
  /** On a phone: points 44 px apart, each a 44 px touch target. */
  touch?: boolean;
  /** The newest version's sha when Live runs exactly its graph: that version is drawn as Live. */
  liveIs?: string | null;
  /** Pull requests still open that change the graph: drawn after Live, each in the colour of its state. */
  proposals?: readonly HistoryVersion[];
};



type Point = { b: string; x: number; name: string; release: boolean; refused: boolean; flags: string[]; version: HistoryVersion | null; date: string | null;
  /** Its version number — its own release, or the one it follows — where the history has one. */
  number: string | null;
  /** A pull request still open: where it stands. */
  state?: ProposalState };

/**
 * Where each version and Live stand: spread over the width as the mockup's track is, never closer than
 * ``minStep``; oldest left, Live last after a dashed gap of 1.4 steps.
 */
export function layOut(
  all: readonly HistoryVersion[],
  live: string | null,
  width: number,
  minStep: number = MIN_STEP,
  liveIs: string | null = null,
  proposals: readonly HistoryVersion[] = [],
): { points: Point[]; length: number } {
  const names = versionNames(all);
  const numbers = numbersOf(all);
  // While Live runs exactly the newest version's graph the two are one point: Live, carrying that version.
  const merged = live && liveIs && all.at(-1)?.sha === liveIs ? all.at(-1)! : null;
  const versions = merged ? all.slice(0, -1) : all;
  const slots = Math.max(versions.length - 1, 0) + (live ? LIVE_GAP_STEPS : 0) + (proposals.length ? LIVE_GAP_STEPS + proposals.length - 1 : 0);
  const step = slots > 0 ? Math.max(minStep, (width - 2 * PAD) / slots) : 0;
  const lone = versions.length === 1 && !live && !proposals.length;
  const points: Point[] = versions.map((version, index) => ({
    b: shortSha(version),
    x: lone ? width / 2 : PAD + index * step,
    name: names[index],
    release: releaseOf(version) !== null,
    refused: Boolean(version.refused),
    flags: flagsOf(version),
    version,
    number: numbers[index],
    date: version.date,
  }));
  // Pull requests still open stand after the history, past a gap: proposals, not yet part of it. Live is last.
  const start = (points.at(-1)?.x ?? PAD - LIVE_GAP_STEPS * step) + LIVE_GAP_STEPS * step;
  proposals.forEach((proposal, at) =>
    points.push({
      b: shortSha(proposal),
      x: start + at * step,
      name: `#${proposal.pr?.number ?? at + 1}`,
      release: false,
      refused: Boolean(proposal.refused),
      flags: [],
      version: proposal,
      date: null,
      number: null,
      state: proposal.pr?.state ?? "open",
    }),
  );
  if (live) {
    const x = points.length ? (points.at(-1)?.x ?? PAD) + LIVE_GAP_STEPS * step : width / 2;
    points.push({ b: "live", x, name: "Live", release: true, refused: false, flags: merged ? flagsOf(merged) : [], version: merged, date: null, number: merged ? numbers[all.length - 1] : null });
  }
  const length = Math.max(width, (points.at(-1)?.x ?? 0) + PAD);
  return { points, length };
}

const EMPTY: readonly HistoryVersion[] = [];

/** Half the width of a name's chip, as the mockup sizes it. */
function chipHalf(text: string): number {
  return (text.length * 6.3 + 16) / 2;
}

/** The chosen version's chip under the track: dark, its name in white, centred on ``x``. */
function Chip({ x, text, colour = INK }: { x: number; text: string; colour?: string }) {
  const half = chipHalf(text);
  return (
    <g data-testid="chip">
      <rect x={x - half} y={LABEL_Y - 9} width={half * 2} height={18} rx={9} fill={colour} />
      <text x={x} y={LABEL_Y + 3.8} fontSize={10.5} fontWeight={600} fill="#fff" textAnchor="middle">
        {text}
      </text>
    </g>
  );
}

/**
 * The mockup's tooltip card: white, a thin border, a soft shadow. It opens under the track, below the names,
 * so it never covers a point another pick needs, and the pointer passes through it.
 */
const TIP_SX = {
  width: 320,
  bgcolor: "#fff",
  color: "#1e293b",
  border: "1px solid rgba(15, 23, 42, 0.1)",
  borderRadius: "8px",
  boxShadow: "0 8px 30px rgba(15, 23, 42, 0.14), 0 1px 2px rgba(15, 23, 42, 0.06)",
  p: "10px 12px",
  fontSize: 12,
  lineHeight: 1.45,
  fontWeight: 400,
} as const;

/** The point's tooltip: under the point, 2 px below the track's names. */
const TIP_OFFSET = [0, HEIGHT + 2 - (AXIS_Y + MIN_STEP / 2)] as const;

/** The chosen version's knob on the axis: dark, a white ring, a soft shadow. */
/**
 * Each point's colour says how it came, the same on the track, in its card and in the legend: merged purple, a
 * direct push grey, an open pull request its state's colour, Live hollow grey. The chosen point keeps it.
 */
function lookOf(point: Point): { colour: string; hollow: boolean } {
  if (point.b === "live") return { colour: LIVE_LOOK.colour, hollow: true };
  if (point.state) return { colour: PROPOSAL_LOOK[point.state].colour, hollow: false };
  if (point.refused) return { colour: "#dc2626", hollow: true };
  return { colour: point.version?.pr ? MERGED_LOOK.colour : DIRECT_LOOK.colour, hollow: false };
}

/** The radius of the chosen point's knob. */
const KNOB = 5.5;

function Knob({ x, point, shadow = true }: { x: number; point: Point; shadow?: boolean }) {
  const look = lookOf(point);
  return look.hollow ? (
    <circle cx={x} cy={AXIS_Y} r={KNOB} fill="#fff" stroke={look.colour} strokeWidth={2.4} filter={shadow ? "url(#track-shadow)" : undefined} />
  ) : (
    <circle cx={x} cy={AXIS_Y} r={KNOB} fill={look.colour} stroke="#fff" strokeWidth={2} filter={shadow ? "url(#track-shadow)" : undefined} />
  );
}

/**
 * One time axis of a history, drawn as the mockup draws it (spec 037, FR-016 – FR-027): light points,
 * releases a little larger, tags as small flags above, refused versions hollow and red, Live a hollow
 * point after a dashed gap; the chosen version is a dark knob with its name in a dark chip below, and the
 * other names stand under their points, thinned before they collide. A long history scrolls sideways the
 * way the browser scrolls — a sideways swipe or wheel with its momentum, the vertical wheel over the track
 * turned sideways, a drag on it — with no scrollbar and nothing faded: the right edge counts what is newer
 * out of view, and a chosen version out of view is pinned to its edge. The track is a slider: ← → step,
 * Home and End jump to the ends.
 */
export function VersionTrack({ versions, live, value, onChange, width, touch = false, liveIs = null, proposals = EMPTY }: VersionTrackProps) {
  const { points, length } = useMemo(
    () => layOut(versions, live, width, touch ? TOUCH_STEP : MIN_STEP, liveIs, proposals),
    [versions, live, width, touch, liveIs, proposals],
  );
  const hitRadius = (touch ? TOUCH_STEP : MIN_STEP) / 2;
  const maxOffset = Math.max(0, length - width);
  const index = points.findIndex((point) => point.b === value);
  const chosen = index >= 0 ? points[index] : null;
  const scroller = useRef<HTMLDivElement | null>(null);
  const [offset, setOffset] = useState(() => (chosen ? clamp(chosen.x - width / 2, 0, maxOffset) : maxOffset));
  const drag = useRef<{ x: number; left: number; moved: boolean; pointer: number } | null>(null);
  const frame = useRef(0);
  // One tooltip for the track: the point under the pointer and where it stood on the screen. It stays where it
  // is while the track scrolls under a still pointer; when the track stops, it moves to the point now under the
  // pointer, or closes when there is none.
  const [tip, setTip] = useState<{ b: string; rect: DOMRect } | null>(null);
  const pointer = useRef<{ x: number; y: number } | null>(null);
  const scrolling = useRef(false);
  const settle = useRef(0);
  const hovered = tip?.b ?? null;

  const scrollTo = (x: number, smooth = true) => scroller.current?.scrollTo({ left: clamp(x - width / 2, 0, maxOffset), behavior: smooth ? "smooth" : "auto" });

  // The track opens where the chosen version is.
  useLayoutEffect(() => {
    if (scroller.current) scroller.current.scrollLeft = offset;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // The chosen version stays in view as it changes by keys (FR-027).
  useEffect(() => {
    if (chosen && (chosen.x < offset + PAD || chosen.x > offset + width - PAD)) scrollTo(chosen.x);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  // The vertical wheel over the track scrolls it sideways; a sideways swipe scrolls natively. Neither ever
  // reaches the page — React's wheel listener is passive and cannot stop it, so this one is not.
  useEffect(() => {
    const element = scroller.current;
    if (!element) return;
    const onWheel = (event: globalThis.WheelEvent) => {
      if (maxOffset === 0) return;
      if (Math.abs(event.deltaY) > Math.abs(event.deltaX)) {
        event.preventDefault();
        element.scrollLeft += event.deltaY;
      }
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
  }, [maxOffset]);

  /** What depends on where the track is scrolled follows it once a frame, never the points themselves. */
  function onScroll() {
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => setOffset(scroller.current?.scrollLeft ?? 0));
    scrolling.current = true;
    window.clearTimeout(settle.current);
    settle.current = window.setTimeout(() => {
      scrolling.current = false;
      // The pointer has not moved, so neither does the tooltip: only what it says follows the point now under it,
      // and an open tooltip's point glides the last few pixels to stand exactly under the pointer.
      const next = tipUnderPointer();
      setTip((current) => (next && current ? { b: next.b, rect: current.rect } : next));
      if (next && tip) settleUnderPointer(next.b);
    }, 150);
  }

  /** The point under the pointer, with where its target stands on the screen; ``null`` when there is none. */
  function tipUnderPointer(): { b: string; rect: DOMRect } | null {
    const element = scroller.current;
    if (!element || !pointer.current) return null;
    const box = element.getBoundingClientRect();
    const x = pointer.current.x - box.left + element.scrollLeft;
    const y = pointer.current.y - box.top;
    if (Math.abs(y - AXIS_Y) > hitRadius) return null;
    const near = points.reduce<Point | null>((best, point) => (Math.abs(point.x - x) <= hitRadius && (!best || Math.abs(point.x - x) < Math.abs(best.x - x)) ? point : best), null);
    if (!near) return null;
    return { b: near.b, rect: new DOMRect(box.left + near.x - element.scrollLeft - hitRadius, box.top + AXIS_Y - hitRadius, hitRadius * 2, hitRadius * 2) };
  }

  /** Scroll smoothly by the few pixels between point ``b`` and the pointer; nothing when they already meet. */
  function settleUnderPointer(b: string) {
    const element = scroller.current;
    const point = points.find((each) => each.b === b);
    if (!element || !point || !pointer.current) return;
    const gap = point.x - element.scrollLeft - (pointer.current.x - element.getBoundingClientRect().left);
    if (Math.abs(gap) >= 0.5) element.scrollBy({ left: gap, behavior: "smooth" });
  }

  function follow(event: PointerEvent<HTMLDivElement>) {
    pointer.current = { x: event.clientX, y: event.clientY };
    if (scrolling.current || drag.current?.moved) return;
    const next = tipUnderPointer();
    if (next?.b !== tip?.b) setTip(next);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (points.length < 2) return;
    const at = Math.max(index, 0);
    const next = { ArrowLeft: at - 1, ArrowRight: at + 1, Home: 0, End: points.length - 1 }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    const clamped = Math.min(Math.max(next, 0), points.length - 1);
    if (clamped !== index) onChange(points[clamped].b);
  }

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    event.currentTarget.focus();
    if (event.pointerType !== "mouse") return; // a finger scrolls natively
    drag.current = { x: event.clientX, left: scroller.current?.scrollLeft ?? 0, moved: false, pointer: event.pointerId };
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    follow(event);
    if (!drag.current || !scroller.current) return;
    const moved = event.clientX - drag.current.x;
    if (!drag.current.moved && Math.abs(moved) > 3) {
      drag.current.moved = true;
      // Once it is a drag, the track keeps the pointer even when it leaves the track.
      event.currentTarget.setPointerCapture?.(drag.current.pointer);
    }
    if (drag.current.moved) scroller.current.scrollLeft = drag.current.left - moved;
  }

  function endDrag() {
    // A click right after a drag is not a choice: forget the drag only after that click has passed.
    setTimeout(() => (drag.current = null), 0);
  }

  const shownOffset = clamp(offset, 0, maxOffset);
  const newer = points.filter((point) => point.x > shownOffset + width).length;
  const pinned = chosen && chosen.x < shownOffset ? "left" : chosen && chosen.x > shownOffset + width ? "right" : null;
  // The chosen point's chip, as the mockup writes it: its version and its name (``0.11.0 · #147``), or its name alone.
  const chipText = chosen ? (chosen.number && chosen.b !== "live" && !chosen.state ? `${chosen.number} · ${chosen.name}` : chosen.name) : "";
  const pinWidth = chosen ? chipHalf(chipText) * 2 + 16 : 0;

  // The points are drawn once per choice, hover or pin — not once per scrolled pixel.
  const body = useMemo(() => {
    // No name stands where the chosen version's chip does.
    const underChip = (x: number) => chosen !== null && !pinned && Math.abs(x - chosen.x) < chipHalf(chipText) + 20;
    // Names under the track: a version's own point by its number (``0.8.0``), as the mockup names it, and Live;
    // no dates. Names thin out where they would collide, never under the chip.
    const shown = trackLabels(points, (point) => point.b !== value && !underChip(point.x));
    return (
      <svg width={length} height={HEIGHT} viewBox={`0 0 ${length} ${HEIGHT}`} fontFamily="ui-sans-serif, system-ui, sans-serif" style={{ display: "block" }}>
        <defs>
          <filter id="track-shadow" x="-60%" y="-60%" width="220%" height="220%">
            <feDropShadow dx="0" dy="1" stdDeviation="1.2" floodColor={INK} floodOpacity=".22" />
          </filter>
        </defs>
        {points.map((point) =>
          point.flags.length ? (
            <g key={`flag-${point.b}`} data-testid={`flag-${point.b}`}>
              <path d={`M${point.x} ${AXIS_Y - 6}V${AXIS_Y - 18}`} stroke={MUTED} strokeWidth={1.2} />
              <path d={`M${point.x} ${AXIS_Y - 18}h7l-2 2.4 2 2.4h-7z`} fill={MUTED} />
            </g>
          ) : null,
        )}
        {/* Each stretch of the line takes the colour of the point it leads to: solid to a version in the history,
            dashed to what is not in it yet — an open pull request or Live. */}
        {points.slice(1).map((point, at) => (
          <line
            key={`line-${point.b}`}
            data-testid={point.b === "live" ? "live-gap" : point.state && !points[at].state ? "proposals-gap" : undefined}
            x1={points[at].x}
            y1={AXIS_Y}
            x2={point.x}
            y2={AXIS_Y}
            stroke={lookOf(point).colour}
            strokeOpacity={0.35}
            strokeWidth={2}
            strokeDasharray={point.b === "live" || point.state ? "2 4" : undefined}
            strokeLinecap="round"
          />
        ))}
        {points.map((point) => (
          <g
            key={point.b}
            data-testid={`point-${point.b}`}
            data-x={point.x}
            data-refused={point.refused || undefined}
            onClick={() => {
              if (!drag.current?.moved) onChange(point.b);
            }}
            style={{ cursor: "pointer" }}
          >
            <circle data-testid={`target-${point.b}`} cx={point.x} cy={AXIS_Y} r={hitRadius} fill="transparent" />
            {hovered === point.b && point.b !== value && <circle data-testid="hover-ring" cx={point.x} cy={AXIS_Y} r={KNOB + 1} fill="none" stroke={MUTED} strokeWidth={1.4} style={{ pointerEvents: "none" }} />}
            {point.b === "live" ? (
              <circle cx={point.x} cy={AXIS_Y} r={4} fill="#fff" stroke={LIVE_LOOK.colour} strokeWidth={1.5} style={{ pointerEvents: "none" }} />
            ) : point.state && !point.refused ? (
              <circle
                data-state={point.state}
                cx={point.x}
                cy={AXIS_Y}
                r={3.6}
                fill={PROPOSAL_LOOK[point.state].colour}
                stroke={PROPOSAL_LOOK[point.state].colour}
                strokeWidth={1.4}
                style={{ pointerEvents: "none" }}
              />
            ) : point.refused ? (
              <circle cx={point.x} cy={AXIS_Y} r={3.2} fill="#fff" stroke="#dc2626" strokeWidth={1.4} style={{ pointerEvents: "none" }} />
            ) : (
              <circle cx={point.x} cy={AXIS_Y} r={point.release ? 3.4 : 2.4} fill={lookOf(point).colour} style={{ pointerEvents: "none" }} />
            )}
            {shown.has(point.b) && (
              <text data-testid={`label-${point.b}`} x={point.x} y={LABEL_Y + 4} fontSize={10.5} fill={MUTED} textAnchor="middle">
                {shown.get(point.b)}
              </text>
            )}
          </g>
        ))}
        {chosen && !pinned && (
          <g data-testid="handle" style={{ pointerEvents: "none" }}>
            <Knob x={chosen.x} point={chosen} />
            <Chip x={clamp(chosen.x, chipHalf(chipText) + 1, length - chipHalf(chipText) - 1)} text={chipText} colour={lookOf(chosen).colour} />
          </g>
        )}
      </svg>
    );
  }, [points, length, value, chosen, pinned, hovered, hitRadius, live, onChange]);

  const tipPoint = tip ? points.find((point) => point.b === tip.b) ?? null : null;

  return (
    <Box
      role="slider"
      tabIndex={0}
      aria-label="Version"
      aria-valuemin={0}
      aria-valuemax={Math.max(points.length - 1, 0)}
      aria-valuenow={Math.max(index, 0)}
      aria-valuetext={chosen?.name ?? "none"}
      onKeyDown={onKeyDown}
      data-testid="track"
      data-offset={shownOffset}
      sx={{ position: "relative", width, height: HEIGHT, outline: "none", userSelect: "none", "&:focus-visible": { outline: "2px solid rgba(15, 23, 42, 0.2)", borderRadius: "6px" } }}
    >
      <Box
        ref={scroller}
        data-testid="track-view"
        onScroll={onScroll}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onPointerLeave={() => {
          pointer.current = null;
          if (!drag.current?.moved) setTip(null);
        }}
        sx={{
          width,
          height: HEIGHT,
          overflowX: "auto",
          overflowY: "hidden",
          // No scrollbar, and a swipe past either end never takes the browser back a page.
          scrollbarWidth: "none",
          "&::-webkit-scrollbar": { display: "none" },
          overscrollBehaviorX: "contain",
        }}
      >
        {body}
      </Box>
      {tip && tipPoint && (
        <Popper
          open
          anchorEl={{ getBoundingClientRect: () => tip.rect }}
          placement="bottom-start"
          modifiers={[{ name: "offset", options: { offset: TIP_OFFSET } }]}
          sx={{ zIndex: 1400, pointerEvents: "none" }}
        >
          <Paper elevation={0} data-testid="version-tip" sx={TIP_SX}>
            <VersionTip version={tipPoint.version} release={tipPoint.number} live={tipPoint.b === "live"} state={tipPoint.state} />
          </Paper>
        </Popper>
      )}
      {newer > 0 && pinned !== "right" && (
        <Box data-testid="newer" sx={{ position: "absolute", right: 0, top: LABEL_Y - 7, pl: "8px", bgcolor: "#fff", fontSize: 10.5, color: "#64748b", lineHeight: "16px", pointerEvents: "none" }}>
          {`${newer} newer ›`}
        </Box>
      )}
      {pinned && chosen && (
        <svg
          data-testid="pinned-handle"
          role="button"
          aria-label={`Scroll back to ${chipText}`}
          width={pinWidth}
          height={HEIGHT}
          onPointerDown={(event) => event.stopPropagation()}
          onClick={() => scrollTo(chosen.x)}
          style={{ position: "absolute", top: 0, [pinned]: 0, cursor: "pointer", background: "#fff" }}
        >
          {pinned === "left" ? (
            <>
              <path d={`M10 ${AXIS_Y}l5-4.5v9z`} fill="#334155" />
              <Knob x={26} point={chosen} shadow={false} />
              <Chip x={8 + chipHalf(chipText)} text={chipText} colour={lookOf(chosen).colour} />
            </>
          ) : (
            <>
              <path d={`M${pinWidth - 10} ${AXIS_Y}l-5-4.5v9z`} fill="#334155" />
              <Knob x={pinWidth - 26} point={chosen} shadow={false} />
              <Chip x={pinWidth - 8 - chipHalf(chipText)} text={chipText} colour={lookOf(chosen).colour} />
            </>
          )}
        </svg>
      )}
    </Box>
  );
}

/**
 * The names under the track, by point: a version's own point by its number (``0.8.0``), as the mockup names it,
 * and Live. Nothing else is named — no dates: a point after a version with no tag of its own belongs to it, and a
 * history without version tags has only its points and the chosen one's chip. Names thin out where they collide.
 */
function trackLabels(points: readonly Point[], allowed: (point: Point) => boolean): Map<string, string> {
  const candidates = points.flatMap((point, at) => {
    if (!allowed(point)) return [];
    const release = point.release && !point.state && point.b !== "live" && point.number !== null;
    const text = point.b === "live" ? point.name : release ? point.number : null;
    return text === null ? [] : [{ b: point.b, x: point.x, text, kept: point.b === "live" || at === 0, release: true }];
  });
  const kept = thinLabels(candidates);
  return new Map(candidates.filter((candidate) => kept.has(candidate.b)).map((candidate) => [candidate.b, candidate.text]));
}

/** ``value`` kept within ``low`` and ``high``. */
function clamp(value: number, low: number, high: number): number {
  return Math.min(Math.max(value, low), high);
}
