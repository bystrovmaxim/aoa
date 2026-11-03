// src/components/diagrams/SideBySide/SideBySide.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import { useMediaQuery, useTheme } from "@mui/material";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { HalfProvider, type Half, type Side } from "@/lib/half";
import { setHalfTracking, useHalfTracking } from "@/lib/halfPicking";

type SideBySideProps = {
  a: Half;
  b: Half;
  /** The diagram, drawn once under each half: a half is told apart by ``useHalf``. */
  children: ReactNode;
};

const COLOUR: Record<Side, string> = { a: "#b45309", b: "#1d4ed8" };

/** One half: the name of its version over its own diagram; ``head`` stands at the end of that line. */
function HalfPane({ half, head, children }: { half: Half; head?: ReactNode; children: ReactNode }) {
  return (
    <Box
      data-half={half.side}
      sx={{ flex: "1 1 0", minWidth: 0, minHeight: 0, display: "flex", flexDirection: "column", position: "relative", "& + &": { borderLeft: "1px solid rgba(15, 23, 42, 0.14)" } }}
    >
      <Box sx={{ flexShrink: 0, height: 30, display: "flex", alignItems: "center", gap: 1, px: 1.5, fontSize: 12, color: "#334155", bgcolor: "#fff", borderBottom: "1px solid rgba(15, 23, 42, 0.08)" }}>
        <Box component="span" sx={{ fontWeight: 700, color: COLOUR[half.side] }}>
          {half.side.toUpperCase()}
        </Box>
        <Box component="b" sx={{ flex: 1, minWidth: 0, color: "#0f172a", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {half.name}
        </Box>
        {head}
      </Box>
      <HalfProvider half={half}>{children}</HalfProvider>
    </Box>
  );
}

/** The switch of tracking: whether a half's camera goes to what the pointer rests on in the other. */
function TrackSwitch() {
  const on = useHalfTracking();
  return (
    <ButtonBase role="switch" aria-checked={on} aria-label="Track" onClick={() => setHalfTracking(!on)} sx={{ flexShrink: 0, height: 20, px: 1, fontSize: 11.5, fontWeight: 600, borderRadius: "6px", color: on ? "#1d4ed8" : "#64748b", bgcolor: on ? "rgba(37, 99, 235, 0.1)" : "transparent" }}>
      Track
    </ButtonBase>
  );
}

/** The switch of a phone: one diagram, flipped between the two versions. */
function FlipSwitch({ side, onSide }: { side: Side; onSide: (side: Side) => void }) {
  return (
    <Box role="radiogroup" aria-label="Version shown" sx={{ display: "inline-flex", flexShrink: 0, gap: "2px", p: "2px", border: "1px solid rgba(15, 23, 42, 0.12)", borderRadius: "8px" }}>
      {(["a", "b"] as const).map((each) => (
        <ButtonBase key={each} role="radio" aria-checked={each === side} onClick={() => onSide(each)} sx={{ width: 30, height: 20, fontSize: 12, fontWeight: 700, borderRadius: "6px", color: each === side ? "#fff" : "#334155", bgcolor: each === side ? COLOUR[each] : "transparent" }}>
          {each.toUpperCase()}
        </ButtonBase>
      ))}
    </Box>
  );
}

/**
 * Two versions of one diagram (spec 044): A on the left, B on the right, each in its own layout. A phone has room for
 * one: an A / B switch flips it, opening on B; which side a person looks at is their own, never the room's.
 */
export function SideBySide({ a, b, children }: SideBySideProps) {
  const phone = useMediaQuery(useTheme().breakpoints.down("sm"));
  const [side, setSide] = useState<Side>("b");
  useEffect(() => {
    if (!phone) setSide("b");
  }, [phone]);
  const shown = useMemo(() => ({ ...(side === "a" ? a : b), phone: true }), [a, b, side]);
  if (phone) {
    return (
      <Box sx={{ flex: 1, minWidth: 0, minHeight: 0, display: "flex" }}>
        <HalfPane key={side} half={shown} head={<FlipSwitch side={side} onSide={setSide} />}>
          {children}
        </HalfPane>
      </Box>
    );
  }
  return (
    <Box sx={{ flex: 1, minWidth: 0, minHeight: 0, display: "flex" }}>
      <HalfPane half={a}>{children}</HalfPane>
      <HalfPane half={b} head={<TrackSwitch />}>
        {children}
      </HalfPane>
    </Box>
  );
}
