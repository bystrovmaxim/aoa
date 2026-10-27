// src/rooms/ParticipantCard/ParticipantCard.tsx
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Popper from "@mui/material/Popper";
import { useEffect } from "react";
import { Avatar } from "@/rooms/Circles/Avatar";
import type { Participant } from "@/rooms/protocol";
import { CARD_BUTTON_QUIET_SX, CARD_BUTTON_SX, CARD_PAPER_SX, HINT_SX } from "@/rooms/roomStyles";

/**
 * What **Follow** can do on this card: follow, switch from someone else, stop, or nothing because it
 * would close a circle (FR-053, FR-054).
 */
export type FollowChoice =
  | { kind: "follow" }
  | { kind: "instead" }
  | { kind: "following" }
  | { kind: "circle"; through: string | null };

export type ParticipantCardProps = {
  participant: Participant;
  anchor: HTMLElement | null;
  /** The participant's page in words. */
  pageLabel: string;
  isYou: boolean;
  /** How many follow this participant; shown on your own card. */
  followers: number;
  onClose: () => void;
  /** **Change name**, on your own card only. */
  onRename: () => void;
  /** **Go to**, on someone else's card. */
  onGoTo: () => void;
  /** What **Follow** does on someone else's card. */
  followChoice: FollowChoice;
  /** How they follow you: ``null``, directly, or through someone (by name). */
  followsYou: { through: string | null } | null;
  onFollow: () => void;
  onStopFollowing: () => void;
  /** The pointer entered or left the card, so a hover-opened card stays while it is used. */
  onHover?: (inside: boolean) => void;
};

/**
 * The card of a circle: full name, the page they are on, whether they follow you, **Go to** and
 * **Follow** (or **Follow <name> instead**, or **Stop following**) on someone else's card, **Change
 * name** on your own. **Follow** that would close a circle is disabled with its reason. Opens on
 * hover, on Enter and on a long press; Esc and a click elsewhere close it. It is not modal, so the
 * diagram stays usable while it is open (spec 028, FR-023, FR-050 … FR-056; mockup screens 9, 12, 13).
 */
export function ParticipantCard({
  participant,
  anchor,
  pageLabel,
  isYou,
  followers,
  onClose,
  onRename,
  onGoTo,
  followChoice,
  followsYou,
  onFollow,
  onStopFollowing,
  onHover,
}: ParticipantCardProps) {
  const open = anchor !== null;
  const first = participant.name.trim().split(/\s+/)[0];

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <Popper open={open} anchorEl={anchor} placement="bottom-end" sx={{ zIndex: 1300 }}>
      <ClickAwayListener onClickAway={onClose}>
        <Box
          role="dialog"
          aria-label={participant.name}
          onMouseEnter={() => onHover?.(true)}
          onMouseLeave={() => onHover?.(false)}
          sx={{ ...CARD_PAPER_SX, width: 260, p: "12px", mt: "6px" }}
        >
          <Box sx={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <Avatar participant={participant} size={24} surface="#fff" />
            <Box sx={{ minWidth: 0 }}>
              <Box sx={{ fontWeight: 600, fontSize: 13, overflowWrap: "anywhere" }}>
                {participant.name}
                {isYou ? " (you)" : ""}
              </Box>
              <Box sx={{ color: "rgb(100, 116, 139)", fontSize: 12, mt: "1px" }}>
                {participant.away ? "Reconnecting…" : pageLabel}
                {followsYou && (
                  <Box component="b" sx={{ fontWeight: 600, color: "rgb(71, 85, 105)" }}>
                    {followsYou.through ? ` · following you through ${followsYou.through}` : " · following you"}
                  </Box>
                )}
              </Box>
            </Box>
          </Box>
          {isYou && followers > 0 && (
            <Box sx={{ ...HINT_SX, mt: "8px" }}>
              {followers === 1 ? "1 person follows you." : `${followers} people follow you.`}
            </Box>
          )}
          {!isYou && (
            <Box sx={{ display: "flex", gap: "4px", mt: "10px", ml: "-6px" }}>
              <Button
                sx={CARD_BUTTON_SX}
                disabled={participant.away || participant.page === null}
                onClick={() => {
                  onClose();
                  onGoTo();
                }}
              >
                Go to {first}
              </Button>
              {followChoice.kind === "following" ? (
                <Button sx={CARD_BUTTON_QUIET_SX} onClick={onStopFollowing}>
                  Stop following
                </Button>
              ) : (
                <Button
                  sx={CARD_BUTTON_QUIET_SX}
                  disabled={followChoice.kind === "circle" || participant.away}
                  onClick={() => {
                    onClose();
                    onFollow();
                  }}
                >
                  {followChoice.kind === "instead" ? `Follow ${first} instead` : "Follow"}
                </Button>
              )}
            </Box>
          )}
          {!isYou && (
            <Box sx={{ ...HINT_SX, mt: "6px" }}>
              {followChoice.kind === "circle"
                ? `${first} is following you${followChoice.through ? ` through ${followChoice.through}` : ""}, so you can't follow ${first}: your screens would chase each other.`
                : followChoice.kind === "instead"
                  ? `You stop following the other person and follow ${first} from now on.`
                  : followChoice.kind === "following"
                    ? "Your screen goes where theirs goes, at your own zoom."
                    : "A click on the circle goes there too. Your zoom stays yours."}
            </Box>
          )}
          {isYou && (
            <Box sx={{ display: "flex", gap: "4px", mt: "10px", ml: "-6px" }}>
              <Button
                sx={CARD_BUTTON_SX}
                onClick={() => {
                  onClose();
                  onRename();
                }}
              >
                Change name
              </Button>
            </Box>
          )}
        </Box>
      </ClickAwayListener>
    </Popper>
  );
}
