// src/rooms/Circles/Avatar.tsx
import Box from "@mui/material/Box";
import { WORKSPACE_SURFACE } from "@/rooms/roomStyles";
import { initials, inkOn } from "@/rooms/initials";
import type { Participant } from "@/rooms/protocol";

export type AvatarProps = {
  participant: Pick<Participant, "name" | "colour">;
  size?: number;
  /** Your own circle carries a ring in your colour. */
  ringed?: boolean;
  /** The surface around the circle, for the gap inside the ring. */
  surface?: string;
  /** The participant's active tab is hidden: the circle is pale (FR-044). */
  pale?: boolean;
  /** A grey dot when they are on another page than yours. */
  elsewhere?: boolean;
};

/** A participant's circle: their colour, their initials in a contrasting colour. */
export function Avatar({ participant, size = 26, ringed = false, surface = WORKSPACE_SURFACE, pale = false, elsewhere = false }: AvatarProps) {
  return (
    <Box
      component="span"
      aria-hidden
      sx={{
        width: size,
        height: size,
        borderRadius: "50%",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        position: "relative",
        userSelect: "none",
        fontSize: Math.round(size * 0.42),
        fontWeight: 600,
        letterSpacing: "0.01em",
        bgcolor: participant.colour,
        color: inkOn(participant.colour),
        opacity: pale ? 0.45 : 1,
        boxShadow: ringed ? `0 0 0 2px ${surface}, 0 0 0 3.5px ${participant.colour}` : "none",
        "&::after": elsewhere
          ? {
              content: '""',
              position: "absolute",
              right: -1,
              bottom: -1,
              width: 9,
              height: 9,
              borderRadius: "50%",
              bgcolor: "#cbd5e1",
              border: `2px solid ${surface}`,
            }
          : undefined,
      }}
    >
      {initials(participant.name)}
    </Box>
  );
}
