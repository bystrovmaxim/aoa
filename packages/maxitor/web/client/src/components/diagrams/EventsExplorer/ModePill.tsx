// src/components/diagrams/EventsExplorer/ModePill.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import type { Mode } from "@/lib/eventsExplorer";
import { useReserveTopCentre } from "@/lib/topCentre";
import { KIND_ICON } from "./explorerLook";

const MODES: { value: Mode; label: string; kind: "domain" | "event" | "action" }[] = [
  { value: "domains", label: "Domains", kind: "domain" },
  { value: "events", label: "Events", kind: "event" },
  { value: "actions", label: "Actions", kind: "action" },
];

/** Where the pill stands and how tall it is: a banner keeps below it the same gap the pill keeps from the top. */
const PILL_TOP = 14;
const PILL_HEIGHT = 32;

/** The light pill at the top of the canvas: what the screen starts from, each mode with its count (FR-002). */
export function ModePill({ mode, counts, onMode }: { mode: Mode; counts: Record<Mode, number>; onMode: (mode: Mode) => void }) {
  useReserveTopCentre(PILL_TOP + PILL_HEIGHT + PILL_TOP - 12);
  return (
    <Box role="radiogroup" aria-label="Start from" sx={{ position: "absolute", top: PILL_TOP, left: "50%", transform: "translateX(-50%)", zIndex: 45, display: "flex", p: "2px", gap: "1px", bgcolor: "rgba(241,245,249,0.88)", backdropFilter: "blur(8px)", borderRadius: 999, border: "1px solid rgba(15,23,42,0.07)" }}>
      {MODES.map(({ value, label, kind }) => {
        const on = value === mode;
        return (
          <ButtonBase
            key={value}
            role="radio"
            aria-checked={on}
            data-testid={`explorer-mode-${value}`}
            onClick={() => onMode(value)}
            sx={{ display: "flex", alignItems: "center", gap: "6px", px: "12px", height: 26, borderRadius: 999, fontSize: 12, fontWeight: 500, color: on ? "#0f172a" : "#64748b", bgcolor: on ? "#ffffff" : "transparent", boxShadow: on ? "0 1px 2px rgba(15,23,42,0.10), 0 0 0 0.5px rgba(15,23,42,0.06)" : "none", transition: "background-color 180ms, color 180ms, box-shadow 180ms", "&:hover": { color: "#0f172a" } }}
          >
            <img src={KIND_ICON[kind]} width={13} height={13} alt="" style={{ borderRadius: "50%", opacity: on ? 1 : 0.55, filter: on ? "none" : "saturate(0.4)" }} />
            {label}
            <Box component="span" sx={{ fontSize: 10.5, fontWeight: 400, color: "#94a3b8", fontVariantNumeric: "tabular-nums" }}>
              {counts[value]}
            </Box>
          </ButtonBase>
        );
      })}
    </Box>
  );
}
