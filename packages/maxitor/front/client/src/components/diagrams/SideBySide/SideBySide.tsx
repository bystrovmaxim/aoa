// src/components/diagrams/SideBySide/SideBySide.tsx
import Box from "@mui/material/Box";
import type { ReactNode } from "react";
import { HalfProvider, type Half } from "@/lib/half";

type SideBySideProps = {
  a: Half;
  b: Half;
  /** The diagram, drawn once under each half: a half is told apart by ``useHalf``. */
  children: ReactNode;
};

/** One half: the name of its version over its own diagram. */
function HalfPane({ half, children }: { half: Half; children: ReactNode }) {
  return (
    <Box
      data-half={half.side}
      sx={{ flex: "1 1 0", minWidth: 0, minHeight: 0, display: "flex", flexDirection: "column", position: "relative", "& + &": { borderLeft: "1px solid rgba(15, 23, 42, 0.14)" } }}
    >
      <Box sx={{ flexShrink: 0, height: 30, display: "flex", alignItems: "center", gap: 1, px: 1.5, fontSize: 12, color: "#334155", bgcolor: "#fff", borderBottom: "1px solid rgba(15, 23, 42, 0.08)" }}>
        <Box component="span" sx={{ fontWeight: 700, color: half.side === "a" ? "#b45309" : "#1d4ed8" }}>
          {half.side.toUpperCase()}
        </Box>
        <Box component="b" sx={{ color: "#0f172a", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {half.name}
        </Box>
      </Box>
      <HalfProvider half={half}>{children}</HalfProvider>
    </Box>
  );
}

/** Two versions of one diagram (spec 044): A on the left, B on the right, each in its own layout. */
export function SideBySide({ a, b, children }: SideBySideProps) {
  return (
    <Box sx={{ flex: 1, minWidth: 0, minHeight: 0, display: "flex" }}>
      <HalfPane half={a}>{children}</HalfPane>
      <HalfPane half={b}>{children}</HalfPane>
    </Box>
  );
}
