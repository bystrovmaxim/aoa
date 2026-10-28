// src/rooms/NameDialog/NameDialog.tsx
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import InputBase from "@mui/material/InputBase";
import { useEffect, useState } from "react";
import type { NameDialogMode } from "@/rooms/useRoomSession";
import { nameIsValid } from "@/rooms/useRoomSession";
import { CARD_BUTTON_QUIET_SX, CARD_BUTTON_SX, CARD_PAPER_SX, HINT_SX, LABEL_CAPS_SX } from "@/rooms/roomStyles";

export type NameDialogProps = {
  mode: NameDialogMode | null;
  /** The name to start with: the last one used in this browser, or the current one. */
  initialName: string;
  /** The page being joined, in words (the join dialog's lead). */
  pageLabel: string;
  /** Why the server refused the name, when it did. */
  error: string | null;
  onCancel: () => void;
  onConfirm: (name: string) => void;
};

const MAX_NAME = 40;

const TEXT: Record<NameDialogMode, { title: string; lead: (page: string) => string; action: string }> = {
  open: {
    title: "Open a room",
    lead: () => "Look at this service together with others: they see your pointer, and filters and layout modes are shared.",
    action: "Open room",
  },
  join: { title: "Join the room", lead: (page) => page, action: "Join" },
  rename: { title: "Change name", lead: () => "Everyone in the room sees the new name.", action: "Save" },
};

/**
 * Asks for the name a participant is shown with: 1–40 characters after trimming, the last one used
 * filled in, and the plain notice that everyone with the link sees it (spec 028, FR-011, FR-024).
 */
export function NameDialog({ mode, initialName, pageLabel, error, onCancel, onConfirm }: NameDialogProps) {
  const [value, setValue] = useState(initialName);

  useEffect(() => {
    if (mode) setValue(initialName);
  }, [mode, initialName]);

  if (!mode) return null;
  const text = TEXT[mode];
  const length = [...value.trim()].length;
  const valid = nameIsValid(value);

  return (
    <Dialog
      open
      onClose={onCancel}
      aria-labelledby="room-name-title"
      slotProps={{
        paper: { sx: { ...CARD_PAPER_SX, width: 340, maxWidth: "calc(100% - 24px)", m: "12px", p: "16px" } },
        backdrop: { sx: { bgcolor: "rgba(15, 23, 42, 0.18)" } },
      }}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (valid) onConfirm(value);
        }}
      >
        <Box id="room-name-title" sx={{ fontSize: 14, fontWeight: 600, mb: "4px" }}>
          {text.title}
        </Box>
        <Box component="p" sx={{ m: "0 0 14px", fontSize: 12.5, color: "rgb(71, 85, 105)", lineHeight: 1.45 }}>
          {text.lead(pageLabel)}
        </Box>
        <Box component="label" htmlFor="room-name-input" sx={{ ...LABEL_CAPS_SX, display: "block", mb: "6px" }}>
          Your name
        </Box>
        <InputBase
          id="room-name-input"
          autoFocus
          fullWidth
          value={value}
          onChange={(event) => setValue(event.target.value)}
          inputProps={{ maxLength: MAX_NAME + 20, "aria-describedby": "room-name-help", autoComplete: "nickname" }}
          sx={{
            border: "1px solid rgba(15, 23, 42, 0.18)",
            borderRadius: "4px",
            bgcolor: "rgba(255, 255, 255, 0.7)",
            px: "10px",
            py: "3px",
            fontSize: 12.5,
            color: "rgb(30, 41, 59)",
            "&.Mui-focused": { borderColor: "rgba(15, 23, 42, 0.45)" },
          }}
        />
        <Box id="room-name-help" sx={{ ...HINT_SX, mt: "6px", display: "flex", justifyContent: "space-between", gap: "12px" }}>
          <span>{error ?? "Everyone with the link sees your name and your pointer. Names are not checked."}</span>
          <Box component="span" sx={{ color: length > MAX_NAME ? "#b91c1c" : undefined, whiteSpace: "nowrap" }}>
            {length}/{MAX_NAME}
          </Box>
        </Box>
        <Box sx={{ display: "flex", justifyContent: "flex-end", gap: "4px", mt: "16px" }}>
          <Button sx={CARD_BUTTON_SX} onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" sx={CARD_BUTTON_QUIET_SX} disabled={!valid}>
            {text.action}
          </Button>
        </Box>
      </form>
    </Dialog>
  );
}
