// src/components/history/VersionTrack/VersionTrack.tsx
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Popper from "@mui/material/Popper";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import type { HistoryVersion, ProposalState } from "@/api/history";
import { flagsOf, numbersOf, releaseOf, shortSha, versionNames } from "@/lib/versionNames";
import { reportHover, reportPanels, useMirroredFocus } from "@/rooms/focusStore";
import { homeEnd, moveTo, shiftBoth, shiftBy, stepHandle, type Moved, type Range, type Side } from "@/lib/versionRange";
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
  /** In Diff: the two picked points, A before B (spec 038, FR-009 – FR-012); ``value`` is then not drawn. */
  range?: Range | null;
  /** A new range picked by a drag, a click, or the keys on a handle. */
  onRange?: (range: Range) => void;
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
 *
 * In Diff (``range``) it holds two handles, A and B, the stretch between them dark (spec 038, FR-009 –
 * FR-012): each is a slider of its own, dragged, clicked toward or stepped by the keys, past the other one
 * too — roles follow position, so they swap as one passes the other —; Shift + ← → moves both; a click on a
 * point moves the nearer handle; a handle dragged to an edge scrolls the track along.
 */
export function VersionTrack({ versions, live, value, onChange, width, touch = false, liveIs = null, proposals = EMPTY, range = null, onRange }: VersionTrackProps) {
  const { points, length } = useMemo(
    () => layOut(versions, live, width, touch ? TOUCH_STEP : MIN_STEP, liveIs, proposals),
    [versions, live, width, touch, liveIs, proposals],
  );
  const keys = useMemo(() => points.map((point) => point.b), [points]);
  const hitRadius = (touch ? TOUCH_STEP : MIN_STEP) / 2;
  const maxOffset = Math.max(0, length - width);
  // While a handle is dragged, the range it would leave is drawn; it is picked when the handle is let go.
  const [preview, setPreview] = useState<Range | null>(null);
  // A follower draws the range the person they follow is dragging, and scrolls the track as they do (spec 038).
  const mirrored = useMirroredFocus();
  const followedTrack = mirrored?.panels.track ?? null;
  const followedPreview = followedTrack?.a && followedTrack.b ? { a: followedTrack.a, b: followedTrack.b } : null;
  const shownRange = range ? ((mirrored ? followedPreview : preview) ?? range) : null;
  const pointOf = (b: string | null) => points.find((point) => point.b === b) ?? null;
  const index = points.findIndex((point) => point.b === (shownRange ? shownRange.b : value));
  const chosen = index >= 0 ? points[index] : null;
  const older = shownRange ? pointOf(shownRange.a) : null;
  const scroller = useRef<HTMLDivElement | null>(null);
  const [offset, setOffset] = useState(() => openingOffset(chosen, older, width, maxOffset));
  const drag = useRef<{ x: number; left: number; moved: boolean; pointer: number } | null>(null);
  const handleDrag = useRef<{ side: Side; start: Range; lastX: number; direction: number; moved: Moved | null } | null>(null);
  /** The whole range being dragged by its stretch: where it started, the point under the pointer then, where it is now. */
  const stretchDrag = useRef<{ start: Range; from: number; moved: Range | null } | null>(null);
  const handles = useRef<Record<Side, SVGGElement | null>>({ a: null, b: null });
  const [focusSide, setFocusSide] = useState<Side | null>(null);
  const frame = useRef(0);
  // One tooltip for the track: the point under the pointer and where it stood on the screen. It stays where it
  // is while the track scrolls under a still pointer; when the track stops, it moves to the point now under the
  // pointer, or closes when there is none.
  const [tip, setTip] = useState<{ b: string; rect: DOMRect } | null>(null);
  const pointer = useRef<{ x: number; y: number } | null>(null);
  const scrolling = useRef(false);
  const settle = useRef(0);
  // A follower sees the tooltip of the version the person they follow has under the pointer (spec 038).
  const hovered = mirrored ? (mirrored.hover?.kind === "version" ? mirrored.hover.id : null) : (tip?.b ?? null);
  const ownTip = tip?.b ?? null;
  const reported = useRef(false);
  useEffect(() => {
    if (mirrored) return;
    if (ownTip !== null) reportHover({ kind: "version", id: ownTip });
    else if (reported.current) reportHover(null);
    reported.current = ownTip !== null;
  }, [ownTip, mirrored]);
  useEffect(
    () => () => {
      if (reported.current) reportHover(null);
      reportPanels({ track: null });
    },
    [],
  );
  // The range being dragged and the scroll go to the people who follow; theirs come back as ``followedTrack``.
  useEffect(() => {
    if (mirrored) return;
    reportPanels({ track: { a: preview?.a ?? null, b: preview?.b ?? null, offset: Math.round(offset) } });
  }, [preview, offset, mirrored]);
  const followedOffset = followedTrack?.offset ?? null;
  useEffect(() => {
    if (followedOffset !== null && scroller.current) scroller.current.scrollLeft = followedOffset;
  }, [followedOffset]);

  const scrollTo = (x: number, smooth = true) => scroller.current?.scrollTo({ left: clamp(x - width / 2, 0, maxOffset), behavior: smooth ? "smooth" : "auto" });

  // The track opens where the chosen version is — in Diff, with A in view too when both fit.
  useLayoutEffect(() => {
    if (scroller.current) scroller.current.scrollLeft = offset;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // The chosen version stays in view as it changes by keys (FR-027).
  useEffect(() => {
    if (chosen && (chosen.x < offset + PAD || chosen.x > offset + width - PAD)) scrollTo(chosen.x);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, range?.b]);

  // The handle that moved keeps the focus, whichever side it ended on (spec 038, FR-012).
  useEffect(() => {
    if (focusSide) handles.current[focusSide]?.focus();
  }, [focusSide, range?.a, range?.b]);

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
    return { b: near.b, rect: rectOfPoint(near, element) };
  }

  /** Where point ``point``'s target stands on the screen. */
  function rectOfPoint(point: Point, element: HTMLElement): DOMRect {
    const box = element.getBoundingClientRect();
    return new DOMRect(box.left + point.x - element.scrollLeft - hitRadius, box.top + AXIS_Y - hitRadius, hitRadius * 2, hitRadius * 2);
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
    if (scrolling.current || drag.current?.moved || handleDrag.current) return;
    const next = tipUnderPointer();
    if (next?.b !== tip?.b) setTip(next);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (range || points.length < 2) return;
    const at = Math.max(index, 0);
    const next = { ArrowLeft: at - 1, ArrowRight: at + 1, Home: 0, End: points.length - 1 }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    const clamped = Math.min(Math.max(next, 0), points.length - 1);
    if (clamped !== index) onChange(points[clamped].b);
  }

  /** Pick ``next``, and keep the focus on the handle that moved, on whichever side it now is. */
  function pickRange(next: Range, side: Side | null) {
    if (side) setFocusSide(side);
    if (range && (next.a !== range.a || next.b !== range.b)) onRange?.(next);
  }

  /** The keys on one handle: ← → step it, Shift + ← → move both, Home and End take it to the ends. */
  function onHandleKey(side: Side, event: KeyboardEvent<SVGGElement>) {
    if (!range) return;
    const delta = event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0;
    if (delta !== 0) {
      event.preventDefault();
      event.stopPropagation();
      if (event.shiftKey) pickRange(shiftBoth(keys, range, delta), side);
      else {
        const moved = stepHandle(keys, range, side, delta);
        pickRange(moved.range, moved.side);
      }
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      event.stopPropagation();
      const moved = homeEnd(keys, range, side, event.key === "Home" ? "home" : "end");
      pickRange(moved.range, moved.side);
    }
  }

  /** A click on a point: in One it is chosen; in Diff the nearer handle moves to it. */
  function onPoint(b: string) {
    if (drag.current?.moved) return;
    if (!range) {
      onChange(b);
      return;
    }
    const at = keys.indexOf(b);
    const [a, z] = [keys.indexOf(range.a), keys.indexOf(range.b)];
    if (at === a || at === z) return;
    const side: Side = Math.abs(at - a) <= Math.abs(at - z) ? "a" : "b";
    pickRange(moveTo(keys, range, side, at, Math.sign(at - (side === "a" ? a : z))).range, null);
  }

  /** The point nearest to where the pointer stands on the track, by index. */
  function nearestAt(clientX: number): number {
    const element = scroller.current;
    const x = clientX - (element?.getBoundingClientRect().left ?? 0) + (element?.scrollLeft ?? 0);
    return points.reduce((best, point, at) => (Math.abs(point.x - x) < Math.abs(points[best].x - x) ? at : best), 0);
  }

  function onHandleDown(side: Side, event: PointerEvent<SVGGElement>) {
    if (!range) return;
    event.stopPropagation();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    handleDrag.current = { side, start: range, lastX: event.clientX, direction: 0, moved: null };
    setTip(null);
  }

  function onHandleMove(event: PointerEvent<SVGGElement>) {
    const current = handleDrag.current;
    if (!current) return;
    if (event.clientX !== current.lastX) current.direction = Math.sign(event.clientX - current.lastX);
    current.lastX = event.clientX;
    const target = nearestAt(event.clientX);
    const direction = current.direction || Math.sign(target - keys.indexOf(current.start[current.side]));
    current.moved = moveTo(keys, current.start, current.side, target, direction);
    setPreview(current.moved.range);
    // A handle dragged to an edge of a long track scrolls it along (spec 038, FR-017).
    const element = scroller.current;
    if (element) {
      const box = element.getBoundingClientRect();
      if (event.clientX < box.left + PAD) element.scrollLeft -= MIN_STEP / 2;
      else if (event.clientX > box.left + width - PAD) element.scrollLeft += MIN_STEP / 2;
    }
  }

  function onHandleUp() {
    const current = handleDrag.current;
    handleDrag.current = null;
    if (!current) return;
    setPreview(null);
    if (current.moved) pickRange(current.moved.range, current.moved.side);
  }

  // The stretch between A and B drags the whole range: both handles move by the points the pointer crossed.
  function onStretchDown(event: PointerEvent<SVGLineElement>) {
    if (!range) return;
    event.stopPropagation();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    stretchDrag.current = { start: range, from: nearestAt(event.clientX), moved: null };
    setTip(null);
  }

  function onStretchMove(event: PointerEvent<SVGLineElement>) {
    const current = stretchDrag.current;
    if (!current) return;
    const moved = shiftBy(keys, current.start, nearestAt(event.clientX) - current.from);
    current.moved = moved === current.start ? null : moved;
    setPreview(current.moved);
  }

  function onStretchUp() {
    const current = stretchDrag.current;
    stretchDrag.current = null;
    if (!current) return;
    setPreview(null);
    if (current.moved) pickRange(current.moved, null);
  }

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (!range) event.currentTarget.focus();
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
  const sideOf = (point: Point | null) => (point && point.x < shownOffset ? "left" : point && point.x > shownOffset + width ? "right" : null);
  const pinned = sideOf(chosen);
  const olderPinned = sideOf(older);
  // The chosen point's chip, as the mockup writes it: its version and its name (``0.11.0 · #147``), or its name alone.
  // In Diff each handle's chip says which it is: ``A 0.8.0``, ``B 0.9.0 · #129``.
  const chipText = chosen ? `${shownRange ? "B " : ""}${nameOnChip(chosen)}` : "";
  const olderText = older ? `A ${nameOnChip(older)}` : "";
  const pinWidth = chosen ? chipHalf(chipText) * 2 + 16 : 0;
  // The two chips never cover each other: when they would, each moves aside by half of what they share.
  const [olderChipX, chipX] = older && chosen ? apart(older.x, chipHalf(olderText), chosen.x, chipHalf(chipText), length) : [0, chosen ? clamp(chosen.x, chipHalf(chipText) + 1, length - chipHalf(chipText) - 1) : 0];

  // The points are drawn once per choice, hover or pin — not once per scrolled pixel.
  const body = useMemo(() => {
    // No name stands where a chosen version's chip does.
    const underChip = (x: number) =>
      (chosen !== null && !pinned && Math.abs(x - chosen.x) < chipHalf(chipText) + 20) || (older !== null && !olderPinned && Math.abs(x - older.x) < chipHalf(olderText) + 20);
    // Names under the track: a version's own point by its number (``0.8.0``), as the mockup names it, and Live;
    // no dates. Names thin out where they would collide, never under the chip.
    const shown = trackLabels(points, (point) => point.b !== chosen?.b && point.b !== older?.b && !underChip(point.x));
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
        {/* In Diff the stretch between A and B is dark. */}
        {older && chosen && <line data-testid="range-stretch" x1={older.x} y1={AXIS_Y} x2={chosen.x} y2={AXIS_Y} stroke={INK} strokeWidth={3} strokeLinecap="round" style={{ pointerEvents: "none" }} />}
        {older && chosen && onRange && (
          // A wide, invisible grip over the stretch: dragging it moves the whole range.
          <line
            data-testid="range-grip"
            aria-hidden
            x1={older.x}
            y1={AXIS_Y}
            x2={chosen.x}
            y2={AXIS_Y}
            stroke="transparent"
            strokeWidth={hitRadius}
            style={{ cursor: stretchDrag.current ? "grabbing" : "grab" }}
            onPointerDown={onStretchDown}
            onPointerMove={onStretchMove}
            onPointerUp={onStretchUp}
            onPointerCancel={onStretchUp}
          />
        )}
        {points.map((point) => (
          <g
            key={point.b}
            data-testid={`point-${point.b}`}
            data-x={point.x}
            data-refused={point.refused || undefined}
            onClick={() => onPoint(point.b)}
            style={{ cursor: "pointer" }}
          >
            <circle data-testid={`target-${point.b}`} cx={point.x} cy={AXIS_Y} r={hitRadius} fill="transparent" />
            {hovered === point.b && point.b !== chosen?.b && point.b !== older?.b && <circle data-testid="hover-ring" cx={point.x} cy={AXIS_Y} r={KNOB + 1} fill="none" stroke={MUTED} strokeWidth={1.4} style={{ pointerEvents: "none" }} />}
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
        {!shownRange && chosen && !pinned && (
          <g data-testid="handle" style={{ pointerEvents: "none" }}>
            <Knob x={chosen.x} point={chosen} />
            <Chip x={chipX} text={chipText} colour={lookOf(chosen).colour} />
          </g>
        )}
        {shownRange &&
          ([
            ["a", older, olderText, olderChipX, olderPinned],
            ["b", chosen, chipText, chipX, pinned],
          ] as const).map(([side, point, text, x, out]) =>
            point && !out ? (
              <g
                key={side}
                ref={(element) => void (handles.current[side] = element)}
                data-testid={`handle-${side}`}
                role="slider"
                tabIndex={0}
                aria-label={side === "a" ? "A, the older version" : "B, the newer version"}
                aria-valuemin={0}
                aria-valuemax={points.length - 1}
                aria-valuenow={keys.indexOf(point.b)}
                aria-valuetext={`${side === "a" ? "A" : "B"}, ${nameOnChip(point)}, ${side === "a" ? "older" : "newer"} version`}
                onKeyDown={(event) => onHandleKey(side, event)}
                onFocus={() => setFocusSide(side)}
                onPointerDown={(event) => onHandleDown(side, event)}
                onPointerMove={onHandleMove}
                onPointerUp={onHandleUp}
                onPointerCancel={onHandleUp}
                style={{ cursor: "grab", outline: "none" }}
              >
                <circle cx={point.x} cy={AXIS_Y} r={hitRadius} fill="transparent" />
                <Knob x={point.x} point={point} />
                <Chip x={x} text={text} colour={INK} />
              </g>
            ) : null,
          )}
      </svg>
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, length, value, chosen, older, pinned, olderPinned, hovered, hitRadius, live, onChange, shownRange, chipX, olderChipX]);

  const tipPoint = hovered ? (points.find((point) => point.b === hovered) ?? null) : null;
  // Your own tooltip stays where it opened while the track scrolls under it; a followed one stands at its point.
  const tipRect = () => (!mirrored && tip ? tip.rect : tipPoint && scroller.current ? rectOfPoint(tipPoint, scroller.current) : new DOMRect());
  // A handle out of view is pinned to its edge: on each side the one nearer to the view.
  const pins = (["left", "right"] as const).flatMap((edge) => {
    const out = [older && olderPinned === edge ? { point: older, text: olderText } : null, chosen && pinned === edge ? { point: chosen, text: chipText } : null].filter((each) => each !== null);
    const nearest = edge === "left" ? out.at(-1) : out[0];
    return nearest ? [{ edge, ...nearest }] : [];
  });

  return (
    <Box
      role={range ? "group" : "slider"}
      tabIndex={range ? undefined : 0}
      aria-label={range ? "Versions" : "Version"}
      aria-valuemin={range ? undefined : 0}
      aria-valuemax={range ? undefined : Math.max(points.length - 1, 0)}
      aria-valuenow={range ? undefined : Math.max(index, 0)}
      aria-valuetext={range ? undefined : (chosen?.name ?? "none")}
      onKeyDown={onKeyDown}
      data-testid="track"
      data-offset={shownOffset}
      sx={{ position: "relative", width, height: HEIGHT, outline: "none", userSelect: "none", "&:focus-visible": { outline: "2px solid rgba(15, 23, 42, 0.2)", borderRadius: "6px" } }}
    >
      <Box
        ref={scroller}
        data-testid="track-view"
        // A pointer over the track names the same version for a follower, however far each scrolled it (spec 038).
        data-pointer-frame="version-track"
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
      {tipPoint && (
        <Popper
          open
          anchorEl={{ getBoundingClientRect: tipRect }}
          placement="bottom-start"
          modifiers={[{ name: "offset", options: { offset: TIP_OFFSET } }]}
          sx={{ zIndex: 1400, pointerEvents: "none" }}
        >
          <Paper elevation={0} data-testid="version-tip" sx={TIP_SX}>
            <VersionTip version={tipPoint.version} release={tipPoint.number} live={tipPoint.b === "live"} state={tipPoint.state} />
          </Paper>
        </Popper>
      )}
      {newer > 0 && !pins.some((pin) => pin.edge === "right") && (
        <Box data-testid="newer" sx={{ position: "absolute", right: 0, top: LABEL_Y - 7, pl: "8px", bgcolor: "#fff", fontSize: 10.5, color: "#64748b", lineHeight: "16px", pointerEvents: "none" }}>
          {`${newer} newer ›`}
        </Box>
      )}
      {pins.map(({ edge, point, text }) => {
        const widthOfPin = chipHalf(text) * 2 + 16;
        return (
          <svg
            key={edge}
            data-testid={range ? `pinned-${point === older ? "a" : "b"}` : "pinned-handle"}
            role="button"
            aria-label={`Scroll back to ${text}`}
            width={range ? widthOfPin : pinWidth}
            height={HEIGHT}
            onPointerDown={(event) => event.stopPropagation()}
            onClick={() => scrollTo(point.x)}
            style={{ position: "absolute", top: 0, [edge]: 0, cursor: "pointer", background: "#fff" }}
          >
            {edge === "left" ? (
              <>
                <path d={`M10 ${AXIS_Y}l5-4.5v9z`} fill="#334155" />
                <Knob x={26} point={point} shadow={false} />
                <Chip x={8 + chipHalf(text)} text={text} colour={range ? INK : lookOf(point).colour} />
              </>
            ) : (
              <>
                <path d={`M${widthOfPin - 10} ${AXIS_Y}l-5-4.5v9z`} fill="#334155" />
                <Knob x={widthOfPin - 26} point={point} shadow={false} />
                <Chip x={widthOfPin - 8 - chipHalf(text)} text={text} colour={range ? INK : lookOf(point).colour} />
              </>
            )}
          </svg>
        );
      })}
    </Box>
  );
}

/** A point's name on its chip: its version and its name (``0.11.0 · #147``), or its name alone. */
function nameOnChip(point: Point): string {
  return point.number && point.b !== "live" && !point.state ? `${point.number} · ${point.name}` : point.name;
}

/** Where the track opens: the chosen point in the middle — in Diff, the middle of A and B when both fit. */
function openingOffset(chosen: Point | null, older: Point | null, width: number, maxOffset: number): number {
  if (!chosen) return maxOffset;
  const centre = older && chosen.x - older.x <= width - 2 * PAD ? (older.x + chosen.x) / 2 : chosen.x;
  return clamp(centre - width / 2, 0, maxOffset);
}

/** Two chips' centres moved apart by half of what they would share, each kept on the track. */
function apart(left: number, leftHalf: number, right: number, rightHalf: number, length: number): [number, number] {
  const overlap = leftHalf + rightHalf + 4 - (right - left);
  const shift = overlap > 0 ? overlap / 2 : 0;
  return [clamp(left - shift, leftHalf + 1, length - leftHalf - 1), clamp(right + shift, rightHalf + 1, length - rightHalf - 1)];
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
