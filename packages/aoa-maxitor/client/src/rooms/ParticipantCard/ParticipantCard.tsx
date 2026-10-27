// src/rooms/ParticipantCard/ParticipantCard.tsx
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Popper from "@mui/material/Popper";
import { useEffect } from "react";
import { Avatar } from "@/rooms/Circles/Avatar";
import type { Participant } from "@/rooms/protocol";
import { CARD_BUTTON_SX, CARD_PAPER_SX, HINT_SX } from "@/rooms/roomStyles";

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
  /** The pointer entered or left the card, so a hover-opened card stays while it is used. */
  onHover?: (inside: boolean) => void;
};

/**
 * The card of a circle: full name, the page they are on, and on your own card **Change name**.
 * Opens on hover, on Enter and on a long press; Esc and a click elsewhere close it. It is not modal,
 * so the diagram stays usable while it is open. **Go to** and **Follow** join it with going to
 * someone and following (spec 028, commits 13 and 14).
 */
export function ParticipantCard({ participant, anchor, pageLabel, isYou, followers, onClose, onRename, onHover }: ParticipantCardProps) {
  const open = anchor !== null;

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
            <Avatar participant={participant} size={30} surface="#fff" />
            <Box sx={{ minWidth: 0 }}>
              <Box sx={{ fontWeight: 600, fontSize: 13, overflowWrap: "anywhere" }}>
                {participant.name}
                {isYou ? " (you)" : ""}
              </Box>
              <Box sx={{ color: "rgb(100, 116, 139)", fontSize: 12, mt: "1px" }}>
                {participant.away ? "Reconnecting…" : pageLabel}
              </Box>
            </Box>
          </Box>
          {isYou && followers > 0 && (
            <Box sx={{ ...HINT_SX, mt: "8px" }}>
              {followers === 1 ? "1 person follows you." : `${followers} people follow you.`}
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
