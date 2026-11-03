// src/rooms/InviteCard/InviteCard.tsx
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Popover from "@mui/material/Popover";
import DoneIcon from "@mui/icons-material/Done";
import { useEffect, useRef, useState } from "react";
import { CARD_BUTTON_QUIET_SX, CARD_PAPER_SX, HINT_SX, LABEL_CAPS_SX } from "@/rooms/roomStyles";
import { mask } from "@/lib/historyAddress";

export type InviteCardProps = {
  anchor: HTMLElement | null;
  /** The address to hand out: the page being looked at, with ``room``. */
  link: string;
  /**
   * Copy as the card opens — when **Copy link** opened it. The card that greets a newly opened room
   * does not: a browser lets a page write the clipboard only right after a click.
   */
  copyOnOpen: boolean;
  onClose: () => void;
};

/** Where copying ended: copied, shared through the phone's sheet, or left to the reader to copy. */
type CopyResult = "copied" | "shared" | "manual" | null;

/**
 * Copy the link: the share sheet on a phone that has one, else the clipboard. Without either, the
 * card shows the link selected in a field so it can be copied by hand (FR-018).
 */
export async function copyRoomLink(link: string): Promise<CopyResult> {
  const coarse = typeof window.matchMedia === "function" && window.matchMedia("(pointer: coarse)").matches;
  if (coarse && typeof navigator.share === "function") {
    try {
      await navigator.share({ url: link });
      return "shared";
    } catch {
      // Dismissed share sheet: fall through to the clipboard.
    }
  }
  try {
    await navigator.clipboard.writeText(link);
    return "copied";
  } catch {
    return "manual";
  }
}

/** The card **Copy link** opens: the link, *Copied*, and who can use it (mockup screen 3). */
export function InviteCard({ anchor, link, copyOnOpen, onClose }: InviteCardProps) {
  const [result, setResult] = useState<CopyResult>(null);
  const field = useRef<HTMLInputElement | null>(null);
  const open = anchor !== null;

  useEffect(() => {
    if (!open) return;
    setResult(null);
    if (copyOnOpen) void copyRoomLink(link).then(setResult);
  }, [open, link, copyOnOpen]);

  useEffect(() => {
    if (result === "manual") field.current?.select();
  }, [result]);

  return (
    <Popover
      open={open}
      anchorEl={anchor}
      onClose={onClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      transformOrigin={{ vertical: "top", horizontal: "right" }}
      slotProps={{ paper: { sx: { ...CARD_PAPER_SX, width: 360, maxWidth: "calc(100% - 24px)", p: "12px 14px 14px", mt: "6px" } } }}
    >
      <Box sx={{ ...LABEL_CAPS_SX, mb: "8px" }}>Invite to this room</Box>
      <Box sx={{ display: "flex", gap: "6px", alignItems: "center" }}>
        <Box
          component="input"
          ref={field}
          readOnly
          // The key is dots (spec 037, FR-010) — except when the clipboard is missing and the link must be copied by hand.
          value={result === "manual" ? link : mask(link)}
          aria-label="Room link"
          onFocus={(event: React.FocusEvent<HTMLInputElement>) => event.currentTarget.select()}
          sx={{
            flex: 1,
            minWidth: 0,
            border: "1px solid rgba(15, 23, 42, 0.18)",
            borderRadius: "4px",
            bgcolor: "rgba(255, 255, 255, 0.7)",
            p: "7px 10px",
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            fontSize: 12,
            color: "rgb(71, 85, 105)",
            textOverflow: "ellipsis",
          }}
        />
        <Button
          sx={CARD_BUTTON_QUIET_SX}
          startIcon={result === "copied" || result === "shared" ? <DoneIcon sx={{ fontSize: 14 }} /> : undefined}
          onClick={() => void copyRoomLink(link).then(setResult)}
        >
          {result === "copied" ? "Copied" : result === "shared" ? "Shared" : "Copy link"}
        </Button>
      </Box>
      <Box role="status" sx={{ ...HINT_SX, mt: "8px" }}>
        {result === "manual"
          ? "The clipboard is not available here: the link is selected, copy it by hand."
          : "Anyone with this link can join and see your pointer and this service's diagrams."}
      </Box>
    </Popover>
  );
}
