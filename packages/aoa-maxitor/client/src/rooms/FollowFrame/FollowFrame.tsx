// src/rooms/FollowFrame/FollowFrame.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import { inkOn } from "@/rooms/initials";
import { useParticipantCardOpen } from "@/rooms/participantCardOpen";
import type { Participant } from "@/rooms/protocol";

export type FollowFrameProps = {
  /** The person followed, or ``null`` when following nobody. */
  following: Participant | null;
  onStop: () => void;
};

/**
 * While following, a frame in the followed person's colour around the workspace and a pill
 * *Following <name>* with **Stop** — at the top on a desktop, above the zoom bar on a phone
 * (spec 028, FR-052; mockup screen 11). The pill steps aside while a participant's card is open.
 */
export function FollowFrame({ following, onStop }: FollowFrameProps) {
  const theme = useTheme();
  const phone = useMediaQuery(theme.breakpoints.down("sm"));
  // A participant's card opens over the pill's place; the pill steps aside meanwhile (spec 029, FR-052).
  const cardOpen = useParticipantCardOpen();
  if (!following) return null;
  const ink = inkOn(following.colour);
  return (
    <>
      <Box aria-hidden sx={{ position: "absolute", inset: 0, zIndex: 58, border: `3px solid ${following.colour}`, pointerEvents: "none" }} />
      <Box
        role="status"
        sx={{
          position: "absolute",
          left: "50%",
          transform: "translateX(-50%)",
          ...(phone ? { bottom: 64 } : { top: 8 }),
          zIndex: 59,
          display: "flex",
          visibility: cardOpen ? "hidden" : "visible",
          alignItems: "center",
          gap: "8px",
          height: 28,
          pl: "10px",
          pr: "6px",
          borderRadius: "14px",
          fontSize: 12,
          fontWeight: 600,
          whiteSpace: "nowrap",
          boxShadow: "0 2px 8px rgba(0, 0, 0, 0.18)",
          bgcolor: following.colour,
          color: ink,
        }}
      >
        Following {following.name}
        <ButtonBase
          onClick={onStop}
          sx={{ borderRadius: "10px", px: "9px", py: "3px", fontSize: 11.5, fontWeight: 600, bgcolor: "rgba(255, 255, 255, 0.25)", color: "inherit" }}
        >
          Stop
        </ButtonBase>
      </Box>
    </>
  );
}
