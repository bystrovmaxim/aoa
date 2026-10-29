// src/components/history/VersionTrack/VersionTrack.tsx
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import type { KeyboardEvent } from "react";
import type { HistoryVersion } from "@/api/history";
import { flagsOf, releaseOf, shortSha, tooltipOf, versionNames } from "@/lib/versionNames";

/** Height of the track's drawing. */
const HEIGHT = 64;
/** Room on each side of the axis. */
const PAD = 18;
/** The dashed gap between the newest version and Live. */
const LIVE_GAP = 36;
/** Where the axis runs. */
const AXIS_Y = 38;

export type VersionTrackProps = {
  versions: readonly HistoryVersion[];
  /** The running service whose graph is Live, or ``null``. */
  live: string | null;
  /** The chosen version: a short sha, ``live``, or ``null``. */
  value: string | null;
  onChange: (b: string) => void;
  /** Width of the drawing. */
  width: number;
};

type Point = { b: string; x: number; name: string; release: boolean; refused: boolean; flags: string[]; tooltip: string };

/** Where each version and Live stand on the axis, oldest left, Live last after a dashed gap. */
function pointsOf(versions: readonly HistoryVersion[], live: string | null, width: number): Point[] {
  const names = versionNames(versions);
  const right = width - PAD - (live ? LIVE_GAP : 0);
  const step = versions.length > 1 ? (right - PAD) / (versions.length - 1) : 0;
  const points: Point[] = versions.map((version, index) => ({
    b: shortSha(version),
    x: versions.length > 1 ? PAD + index * step : PAD + (right - PAD) / 2,
    name: names[index],
    release: releaseOf(version) !== null,
    refused: Boolean(version.refused),
    flags: flagsOf(version),
    tooltip: tooltipOf(version),
  }));
  if (live) points.push({ b: "live", x: width - PAD, name: "Live", release: true, refused: false, flags: [], tooltip: "Live: what the service runs now, not merged yet" });
  return points;
}

/**
 * One time axis of a history (spec 037, FR-016 – FR-020): a point per version, releases named and
 * larger, merges as small dots, other tags as flags, refused versions hollow, Live after a dashed gap.
 * The track is a slider whose handle is the chosen version: a click on a point, ← → step, Home and End
 * jump to the ends; where there is nothing to step to, the keys do nothing.
 */
export function VersionTrack({ versions, live, value, onChange, width }: VersionTrackProps) {
  const points = pointsOf(versions, live, width);
  const index = points.findIndex((point) => point.b === value);
  const chosen = index >= 0 ? points[index] : null;
  const lastVersionX = versions.length ? points[versions.length - 1].x : PAD;

  function onKeyDown(event: KeyboardEvent<SVGSVGElement>) {
    if (points.length < 2) return;
    const at = Math.max(index, 0);
    const next = { ArrowLeft: at - 1, ArrowRight: at + 1, Home: 0, End: points.length - 1 }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    const clamped = Math.min(Math.max(next, 0), points.length - 1);
    if (clamped !== index) onChange(points[clamped].b);
  }

  return (
    <Box
      component="svg"
      width={width}
      height={HEIGHT}
      viewBox={`0 0 ${width} ${HEIGHT}`}
      role="slider"
      tabIndex={0}
      aria-label="Version"
      aria-valuemin={0}
      aria-valuemax={Math.max(points.length - 1, 0)}
      aria-valuenow={Math.max(index, 0)}
      aria-valuetext={chosen?.name ?? "none"}
      onKeyDown={onKeyDown}
      onMouseDown={(event) => event.currentTarget.focus()}
      sx={{ display: "block", overflow: "visible", outline: "none", "&:focus-visible": { outline: "2px solid rgba(37, 99, 235, 0.4)" } }}
    >
      {versions.length > 0 && <line x1={PAD} x2={lastVersionX} y1={AXIS_Y} y2={AXIS_Y} stroke="rgb(148, 163, 184)" strokeWidth={1.5} />}
      {live && (
        <line x1={versions.length ? lastVersionX : PAD} x2={width - PAD} y1={AXIS_Y} y2={AXIS_Y} stroke="rgb(148, 163, 184)" strokeWidth={1.5} strokeDasharray="4 4" data-testid="live-gap" />
      )}
      {points.map((point) => (
        <Tooltip key={point.b} title={<Box sx={{ whiteSpace: "pre-line" }}>{point.tooltip}</Box>} placement="top">
          <g data-testid={`point-${point.b}`} data-refused={point.refused || undefined} onClick={() => onChange(point.b)} style={{ cursor: "pointer" }}>
            <circle cx={point.x} cy={AXIS_Y} r={12} fill="transparent" />
            <circle
              cx={point.x}
              cy={AXIS_Y}
              r={point.release ? 5 : 3}
              fill={point.refused ? "white" : point.b === "live" ? "rgb(22, 163, 74)" : "rgb(71, 85, 105)"}
              stroke={point.refused ? "rgb(220, 38, 38)" : "none"}
              strokeWidth={1.5}
            />
            {point.release && (
              <text x={point.x} y={AXIS_Y + 18} fontSize={10.5} textAnchor="middle" fill="rgb(100, 116, 139)">
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
    </Box>
  );
}
