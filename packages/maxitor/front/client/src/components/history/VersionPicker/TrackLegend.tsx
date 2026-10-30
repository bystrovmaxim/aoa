// src/components/history/VersionPicker/TrackLegend.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Tooltip from "@mui/material/Tooltip";
import type { ReactNode } from "react";
import { DIRECT_LOOK, LIVE_LOOK, MERGED_LOOK, PROPOSAL_LOOK } from "@/components/history/VersionTrack/proposalLook";

const INK = "#0f172a";
const MUTED = "#94a3b8";
const STATES = ["open", "approved", "changes_requested"] as const;

/** A 40 × 20 sample of what the track draws. */
function Sample({ children }: { children: ReactNode }) {
  return (
    <svg viewBox="0 0 40 20" width={40} height={20} aria-hidden style={{ display: "block" }}>
      {children}
    </svg>
  );
}

/** One mark: its sample, its name, and what it means. */
function Row({ sample, term, children }: { sample: ReactNode; term: string; children: ReactNode }) {
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: "40px 1fr", columnGap: "12px", alignItems: "start" }}>
      <Box sx={{ pt: "1px" }}>{sample}</Box>
      <Box>
        <Box sx={{ fontSize: 12.5, fontWeight: 600, color: INK }}>{term}</Box>
        <Box sx={{ fontSize: 12, color: "#475569", mt: "1px" }}>{children}</Box>
      </Box>
    </Box>
  );
}

/** A group of marks under a small heading. */
function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Box sx={{ display: "grid", gap: "10px" }}>
      <Box sx={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: MUTED }}>{title}</Box>
      {children}
    </Box>
  );
}

/** A point as the track draws it, with the stretch of line that leads to it, in its colour. */
function PointSample({ colour, hollow = false, dash }: { colour: string; hollow?: boolean; dash?: string }) {
  return (
    <Sample>
      <line x1={4} y1={10} x2={28} y2={10} stroke={colour} strokeOpacity={0.35} strokeWidth={2} strokeDasharray={dash} strokeLinecap="round" />
      {hollow ? <circle cx={30} cy={10} r={3.8} fill="#fff" stroke={colour} strokeWidth={1.5} /> : <circle cx={30} cy={10} r={3.4} fill={colour} />}
    </Sample>
  );
}

/** What the track's marks mean: one row per kind of point, in the order they stand, then the other marks. */
function Legend() {
  return (
    <Box sx={{ display: "grid", gap: "16px" }}>
      <Group title="Points">
        <Row term="Direct push" sample={<PointSample colour={DIRECT_LOOK.colour} />}>
          A change pushed straight to the branch, with no pull request.
        </Row>
        <Row term="Merged" sample={<PointSample colour={MERGED_LOOK.colour} />}>
          A merged pull request.
        </Row>
        {STATES.map((state) => (
          <Row key={state} term={PROPOSAL_LOOK[state].name} sample={<PointSample colour={PROPOSAL_LOOK[state].colour} dash="2 4" />}>
            {
              {
                open: "An open pull request no reviewer has answered yet: no approval, no request for changes.",
                approved: "An open pull request a reviewer approved: it can be merged.",
                changes_requested: "An open pull request a reviewer asked to fix: it cannot be merged as it is.",
              }[state]
            }
          </Row>
        ))}
        <Row term="Live" sample={<PointSample colour={LIVE_LOOK.colour} hollow dash="2 4" />}>
          What the service runs now — always last; one point with the newest version when their graphs are the same.
        </Row>
      </Group>
      <Group title="Marks">
        <Row
          term="Size"
          sample={
            <Sample>
              <circle cx={13} cy={10} r={2.4} fill={MERGED_LOOK.colour} />
              <circle cx={27} cy={10} r={3.4} fill={MERGED_LOOK.colour} />
            </Sample>
          }
        >
          A larger point starts a version and carries its number below; a smaller one belongs to that version.
        </Row>
        <Row
          term="Flag"
          sample={
            <Sample>
              <path d="M20 14V3" stroke={MUTED} strokeWidth={1.2} />
              <path d="M20 3h7l-2 2.4 2 2.4h-7z" fill={MUTED} />
              <circle cx={20} cy={14} r={2.6} fill={MERGED_LOOK.colour} />
            </Sample>
          }
        >
          That version was released: a GitHub Release, or a tag named <code>release…</code>.
        </Row>
        <Row
          term="The chosen point"
          sample={
            <Sample>
              <rect x={2} y={3} width={36} height={14} rx={7} fill={MERGED_LOOK.colour} />
              <text x={20} y={13.2} fontSize={8.5} fontWeight={600} fill="#fff" textAnchor="middle" fontFamily="ui-sans-serif, system-ui, sans-serif">
                #147
              </text>
            </Sample>
          }
        >
          Larger, in its own colour, its name in a chip: <code>0.11.0 · #147</code> — version and pull request; <code>#57</code> — its place, when it had no pull request.
        </Row>
      </Group>
    </Box>
  );
}

/**
 * What the track's marks mean, behind a small "i" before the picker's mode switch: what is on the track, how
 * the chosen point looks, what stands after the history — each beside the mark itself.
 */
export function TrackLegend() {
  return (
    <Tooltip
      placement="bottom-end"
      slotProps={{
        tooltip: {
          sx: {
            width: 400,
            maxWidth: 400,
            bgcolor: "#fff",
            color: "#1e293b",
            border: "1px solid rgba(15, 23, 42, 0.1)",
            borderRadius: "10px",
            boxShadow: "0 12px 40px rgba(15, 23, 42, 0.16), 0 1px 2px rgba(15, 23, 42, 0.06)",
            p: "14px 16px 16px",
            lineHeight: 1.45,
            fontWeight: 400,
            "& code": { fontSize: 11.5, bgcolor: "#f1f5f9", px: "4px", py: "1px", borderRadius: "4px", color: INK },
          },
        },
      }}
      title={<Legend />}
    >
      <ButtonBase aria-label="Reading the track" sx={{ width: 28, height: 28, borderRadius: "8px", color: "#64748b", flexShrink: 0, "&:hover": { bgcolor: "rgba(15, 23, 42, 0.06)", color: INK } }}>
        <svg viewBox="0 0 24 24" width={16} height={16} aria-hidden style={{ display: "block" }}>
          <g fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round">
            <circle cx={12} cy={12} r={8.5} />
            <path d="M12 11v5.2" />
          </g>
          <circle cx={12} cy={7.9} r={1.05} fill="currentColor" />
        </svg>
      </ButtonBase>
    </Tooltip>
  );
}
