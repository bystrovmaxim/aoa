// src/components/history/VersionPicker/TrackLegend.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Tooltip from "@mui/material/Tooltip";
import type { ReactNode } from "react";
import { PROPOSAL_LOOK } from "@/components/history/VersionTrack/proposalLook";

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

/** What the track's marks mean: what is on it, how the chosen point looks, what stands after the history. */
function Legend() {
  return (
    <Box sx={{ display: "grid", gap: "16px" }}>
      <Group title="On the track">
        <Row
          term="A point"
          sample={
            <Sample>
              <line x1={2} y1={10} x2={38} y2={10} stroke="#e2e8f0" strokeWidth={2} />
              <circle cx={14} cy={10} r={2.2} fill="#dbe2ea" />
              <circle cx={28} cy={10} r={3.4} fill="#cbd5e1" />
            </Sample>
          }
        >
          A change that reached the branch and changed the graph — a merged pull request, or a direct push. A larger point starts a version and carries its number below; a smaller one belongs to that version.
        </Row>
        <Row
          term="A flag"
          sample={
            <Sample>
              <path d="M20 14V3" stroke={MUTED} strokeWidth={1.2} />
              <path d="M20 3h7l-2 2.4 2 2.4h-7z" fill={MUTED} />
              <circle cx={20} cy={14} r={2.6} fill="#cbd5e1" />
            </Sample>
          }
        >
          That version was released: a GitHub Release, or a tag named <code>release…</code>.
        </Row>
      </Group>
      <Group title="The chosen point">
        <Row
          term="Its colour"
          sample={
            <Sample>
              <circle cx={7} cy={10} r={4.5} fill={INK} />
              <circle cx={20} cy={10} r={4.5} fill={PROPOSAL_LOOK.open.colour} />
              <circle cx={33} cy={10} r={3.8} fill="#fff" stroke={INK} strokeWidth={1.8} />
            </Sample>
          }
        >
          Dark when merged, its state's colour when still open, hollow for Live.
        </Row>
        <Row
          term="Its name"
          sample={
            <Sample>
              <rect x={2} y={3} width={36} height={14} rx={7} fill={INK} />
              <text x={20} y={13.2} fontSize={8.5} fontWeight={600} fill="#fff" textAnchor="middle" fontFamily="ui-sans-serif, system-ui, sans-serif">
                #147
              </text>
            </Sample>
          }
        >
          <code>0.11.0 · #147</code> — its version and pull request; <code>#57</code> — its place in the history, when it had no pull request.
        </Row>
      </Group>
      <Group title="After the history">
        <Row
          term="Open pull requests"
          sample={
            <Sample>
              {STATES.map((state, at) => (
                <circle key={state} cx={8 + at * 12} cy={10} r={3} fill={PROPOSAL_LOOK[state].colour} stroke={PROPOSAL_LOOK[state].colour} strokeWidth={1.2} />
              ))}
            </Sample>
          }
        >
          <Box component="span" sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 12px", mt: "4px" }}>
            {STATES.map((state) => (
              <Box key={state} component="span" sx={{ display: "inline-flex", alignItems: "center", gap: "6px", color: PROPOSAL_LOOK[state].colour, fontWeight: 600 }}>
                {/* The point exactly as the track draws it. */}
                <svg viewBox="0 0 10 10" width={10} height={10} aria-hidden style={{ display: "block", flexShrink: 0 }}>
                  <circle
                    cx={5}
                    cy={5}
                    r={3.6}
                    fill={PROPOSAL_LOOK[state].colour}
                    stroke={PROPOSAL_LOOK[state].colour}
                    strokeWidth={1.4}
                  />
                </svg>
                {PROPOSAL_LOOK[state].name}
              </Box>
            ))}
          </Box>
        </Row>
        <Row
          term="Live"
          sample={
            <Sample>
              <line x1={2} y1={10} x2={28} y2={10} stroke="#e2e8f0" strokeWidth={2} strokeDasharray="2 4" />
              <circle cx={33} cy={10} r={4} fill="#fff" stroke={MUTED} strokeWidth={1.5} />
            </Sample>
          }
        >
          What the service runs now — always last. One point with the newest version when their graphs are the same.
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
