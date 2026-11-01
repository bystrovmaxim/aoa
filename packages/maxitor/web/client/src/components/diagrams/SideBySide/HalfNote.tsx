// src/components/diagrams/SideBySide/HalfNote.tsx
import Box from "@mui/material/Box";

/** What a half says of the selection, over its diagram. */
export function HalfNote({ text }: { text: string | null }) {
  if (!text) return null;
  return (
    <Box role="status" data-testid="half-note" sx={{ position: "absolute", top: 12, left: "50%", transform: "translateX(-50%)", zIndex: 20, px: 1.5, py: 0.5, borderRadius: "8px", fontSize: 12.5, fontWeight: 600, color: "#fff", bgcolor: "rgba(15, 23, 42, 0.86)", whiteSpace: "nowrap", pointerEvents: "none" }}>
      {text}
    </Box>
  );
}
