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
  /** Take the room a ring needs even without one, so circles in a row line up. */
  boxed?: boolean;
};

/** The width of a ring round a circle, and the gap between the ring and the circle. */
export const RING_PX = 1.5;
export const RING_GAP_PX = 2;

/** The room a circle takes with its ring: the ring is drawn inside it, never beyond (spec 029, FR-051). */
export function ringedBox(size: number): number {
  return size + 2 * (RING_PX + RING_GAP_PX);
}

/**
 * A participant's circle: their colour, their initials in a contrasting colour. ``boxed`` gives it the
 * room its ring needs, so a ring — yours, or a focus ring drawn by the button around it — stays inside
 * the box and never reaches a neighbouring circle.
 */
export function Avatar({ participant, size = 22, ringed = false, surface = WORKSPACE_SURFACE, pale = false, elsewhere = false, boxed = false }: AvatarProps) {
  const circle = (
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
        "&::after": elsewhere
          ? {
              content: '""',
              position: "absolute",
              right: -1,
              bottom: -1,
              width: 8,
              height: 8,
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
  if (!boxed && !ringed) return circle;
  const box = ringedBox(size);
  return (
    <Box
      component="span"
      aria-hidden
      sx={{
        width: box,
        height: box,
        borderRadius: "50%",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        boxShadow: ringed ? `inset 0 0 0 ${RING_PX}px ${participant.colour}` : "none",
      }}
    >
      {circle}
    </Box>
  );
}
