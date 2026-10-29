// src/components/history/VersionTrack/VersionTrack.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Tooltip from "@mui/material/Tooltip";
import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type WheelEvent } from "react";
import type { HistoryVersion } from "@/api/history";
import { flagsOf, releaseOf, shortSha, tooltipOf, versionNames } from "@/lib/versionNames";
import { thinLabels } from "./thinLabels";

/** Height of the track's drawing. */
const HEIGHT = 64;
/** Room on each side of the axis. */
const PAD = 18;
/** The dashed gap between the newest version and Live. */
const LIVE_GAP = 36;
/** Where the axis runs. */
const AXIS_Y = 38;
/** The least distance between two points (FR-023). */
export const MIN_STEP = 24;
/** The least distance, and the touch target, on a phone (FR-031). */
export const TOUCH_STEP = 44;
/** How wide the fades are where more is hidden. */
const FADE = 28;

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
};

type Point = { b: string; x: number; name: string; release: boolean; refused: boolean; flags: string[]; tooltip: string };

/** Where each version and Live stand, oldest left, at least ``MIN_STEP`` apart, Live last after a dashed gap. */
export function layOut(versions: readonly HistoryVersion[], live: string | null, width: number, minStep: number = MIN_STEP): { points: Point[]; length: number } {
  const names = versionNames(versions);
  const gap = live ? Math.max(LIVE_GAP, minStep) : 0;
  const room = width - 2 * PAD - gap;
  const step = versions.length > 1 ? Math.max(minStep, room / (versions.length - 1)) : 0;
  const lastX = versions.length > 1 ? PAD + (versions.length - 1) * step : PAD + (versions.length === 1 ? room / 2 : 0);
  const points: Point[] = versions.map((version, index) => ({
    b: shortSha(version),
    x: versions.length > 1 ? PAD + index * step : lastX,
    name: names[index],
    release: releaseOf(version) !== null,
    refused: Boolean(version.refused),
    flags: flagsOf(version),
    tooltip: tooltipOf(version),
  }));
  const liveX = versions.length ? lastX + gap : PAD;
  if (live) points.push({ b: "live", x: Math.max(liveX, versions.length > 1 ? liveX : width - PAD), name: "Live", release: true, refused: false, flags: [], tooltip: "Live: what the service runs now, not merged yet" });
  const length = Math.max(width, (points.at(-1)?.x ?? 0) + PAD);
  return { points, length };
}

/**
 * One time axis of a history (spec 037, FR-016 – FR-027): a point per version, releases named and
 * larger, merges as small dots, other tags as flags, refused versions hollow, Live after a dashed gap.
 * A long history scrolls sideways — a sideways swipe or wheel, the vertical wheel over the track, a drag
 * on it — with no scrollbar: the edges fade where more is hidden, the right edge counts the newer
 * versions out of view, and a handle out of view is pinned to its edge. The track is a slider: ← → step,
 * Home and End jump to the ends.
 */
export function VersionTrack({ versions, live, value, onChange, width, touch = false }: VersionTrackProps) {
  const { points, length } = layOut(versions, live, width, touch ? TOUCH_STEP : MIN_STEP);
  const hitRadius = (touch ? TOUCH_STEP : MIN_STEP) / 2;
  const maxOffset = Math.max(0, length - width);
  const index = points.findIndex((point) => point.b === value);
  const chosen = index >= 0 ? points[index] : null;
  const [offset, setOffset] = useState(() => (chosen ? clamp(chosen.x - width / 2, 0, maxOffset) : maxOffset));
  const drag = useRef<{ x: number; offset: number; moved: boolean } | null>(null);
  const clampedOffset = clamp(offset, 0, maxOffset);
  const scrollTo = (x: number) => setOffset(clamp(x - width / 2, 0, maxOffset));

  // The chosen version stays in view as it changes by keys (FR-027).
  useEffect(() => {
    if (chosen && (chosen.x < clampedOffset + PAD || chosen.x > clampedOffset + width - PAD)) scrollTo(chosen.x);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const lastVersionX = versions.length ? points[versions.length - 1].x : PAD;
  const newestB = versions.length ? points[versions.length - 1].b : null;
  const hiddenLeft = clampedOffset > 0;
  const hiddenRight = clampedOffset < maxOffset;
  const newerHidden = points.filter((point) => point.b !== "live" && point.x > clampedOffset + width).length;
  const liveHidden = live !== null && points.at(-1)!.x > clampedOffset + width;
  const pinned = chosen && chosen.x < clampedOffset ? "left" : chosen && chosen.x > clampedOffset + width ? "right" : null;
  const shown = thinLabels(
    points
      .map((point, at) => ({ point, at }))
      .filter(({ point, at }) => point.release || at === 0 || at === versions.length - 1)
      .map(({ point, at }) => ({ b: point.b, x: point.x, text: point.name, kept: point.b === value || point.b === "live" || at === 0 || at === versions.length - 1 })),
  );

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (points.length < 2) return;
    const at = Math.max(index, 0);
    const next = { ArrowLeft: at - 1, ArrowRight: at + 1, Home: 0, End: points.length - 1 }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    const clamped = Math.min(Math.max(next, 0), points.length - 1);
    if (clamped !== index) onChange(points[clamped].b);
  }

  function onWheel(event: WheelEvent<HTMLDivElement>) {
    // A sideways swipe or wheel scrolls as it is; the vertical wheel over the track turns sideways.
    const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
    if (maxOffset === 0 || delta === 0) return;
    setOffset((current) => clamp(current + delta, 0, maxOffset));
  }

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    event.currentTarget.focus();
    drag.current = { x: event.clientX, offset: clampedOffset, moved: false };
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!drag.current) return;
    const moved = event.clientX - drag.current.x;
    if (Math.abs(moved) > 3) drag.current.moved = true;
    if (drag.current.moved) setOffset(clamp(drag.current.offset - moved, 0, maxOffset));
  }

  const fadeLeft = hiddenLeft ? `transparent 0, black ${FADE}px` : "black 0";
  const fadeRight = hiddenRight ? `black calc(100% - ${FADE}px), transparent 100%` : "black 100%";

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
      onWheel={onWheel}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={() => (drag.current = null)}
      onPointerLeave={() => (drag.current = null)}
      data-testid="track"
      data-offset={clampedOffset}
      sx={{ position: "relative", width, height: HEIGHT, overflow: "hidden", outline: "none", touchAction: "pan-y", "&:focus-visible": { outline: "2px solid rgba(37, 99, 235, 0.4)" } }}
    >
      <Box
        data-testid="track-view"
        data-fade-left={hiddenLeft || undefined}
        data-fade-right={hiddenRight || undefined}
        sx={{ width, height: HEIGHT, maskImage: `linear-gradient(to right, ${fadeLeft}, ${fadeRight})`, WebkitMaskImage: `linear-gradient(to right, ${fadeLeft}, ${fadeRight})` }}
      >
        <svg width={length} height={HEIGHT} viewBox={`0 0 ${length} ${HEIGHT}`} style={{ display: "block", transform: `translateX(${-clampedOffset}px)` }}>
          {versions.length > 0 && <line x1={PAD} x2={lastVersionX} y1={AXIS_Y} y2={AXIS_Y} stroke="rgb(148, 163, 184)" strokeWidth={1.5} />}
          {live && (
            <line x1={versions.length ? lastVersionX : PAD} x2={points.at(-1)!.x} y1={AXIS_Y} y2={AXIS_Y} stroke="rgb(148, 163, 184)" strokeWidth={1.5} strokeDasharray="4 4" data-testid="live-gap" />
          )}
          {points.map((point) => (
            <Tooltip key={point.b} title={<Box sx={{ whiteSpace: "pre-line" }}>{point.tooltip}</Box>} placement="top">
              <g
                data-testid={`point-${point.b}`}
                data-x={point.x}
                data-refused={point.refused || undefined}
                onClick={() => {
                  if (!drag.current?.moved) onChange(point.b);
                }}
                style={{ cursor: "pointer" }}
              >
                <circle data-testid={`target-${point.b}`} cx={point.x} cy={AXIS_Y} r={hitRadius} fill="transparent" />
                <circle
                  cx={point.x}
                  cy={AXIS_Y}
                  r={point.release ? 5 : 3}
                  fill={point.refused ? "white" : point.b === "live" ? "rgb(22, 163, 74)" : "rgb(71, 85, 105)"}
                  stroke={point.refused ? "rgb(220, 38, 38)" : "none"}
                  strokeWidth={1.5}
                />
                {shown.has(point.b) && (
                  // Beside Live, the newest version's name ends at its point, so the two kept names never meet.
                  <text
                    data-testid={`label-${point.b}`}
                    x={live && point.b === newestB ? point.x + 6 : point.x}
                    y={AXIS_Y + 18}
                    fontSize={10.5}
                    textAnchor={live && point.b === newestB ? "end" : "middle"}
                    fill="rgb(100, 116, 139)"
                  >
                    {point.name}
                  </text>
                )}
                {point.flags.length > 0 && (
                  <text x={point.x} y={AXIS_Y - 12} fontSize={9.5} textAnchor="middle" fill="rgb(148, 163, 184)">
                    ⚑ {point.flags.join(", ")}
                  </text>
                )}
              </g>
            </Tooltip>
          ))}
          {chosen && (
            <g data-testid="handle">
              <circle cx={chosen.x} cy={AXIS_Y} r={8} fill="none" stroke="rgb(37, 99, 235)" strokeWidth={2.5} />
              <text x={chosen.x} y={12} fontSize={11} fontWeight={600} textAnchor="middle" fill="rgb(37, 99, 235)">
                {chosen.name}
              </text>
            </g>
          )}
        </svg>
      </Box>
      {(newerHidden > 0 || liveHidden) && (
        <Box data-testid="newer" sx={{ position: "absolute", right: 4, bottom: 2, fontSize: 10.5, color: "rgb(100, 116, 139)", pointerEvents: "none" }}>
          {newerHidden > 0 ? `+${newerHidden} newer${liveHidden ? " and Live" : ""}` : "+ Live"}
        </Box>
      )}
      {pinned && chosen && (
        <ButtonBase
          data-testid="pinned-handle"
          aria-label={`Scroll back to ${chosen.name}`}
          onPointerDown={(event) => event.stopPropagation()}
          onClick={() => scrollTo(chosen.x)}
          sx={{
            position: "absolute",
            top: AXIS_Y - 9,
            [pinned]: 2,
            width: 18,
            height: 18,
            borderRadius: "50%",
            border: "2.5px solid rgb(37, 99, 235)",
            bgcolor: "white",
          }}
        />
      )}
    </Box>
  );
}

/** ``value`` kept within ``low`` and ``high``. */
function clamp(value: number, low: number, high: number): number {
  return Math.min(Math.max(value, low), high);
}
