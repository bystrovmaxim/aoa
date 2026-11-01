// src/rooms/RoomBar/LeaveForServiceDialog.tsx
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import { CARD_BUTTON_QUIET_SX, CARD_BUTTON_SX, CARD_PAPER_SX } from "@/rooms/roomStyles";

export type LeaveForServiceDialogProps = {
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

/** *Load a different service* inside a room asks first: the room is for this service only (FR-064). */
export function LeaveForServiceDialog({ open, onCancel, onConfirm }: LeaveForServiceDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onCancel}
      aria-labelledby="leave-for-service-title"
      slotProps={{
        paper: { sx: { ...CARD_PAPER_SX, width: 340, maxWidth: "calc(100% - 24px)", m: "12px", p: "16px" } },
        backdrop: { sx: { bgcolor: "rgba(15, 23, 42, 0.18)" } },
      }}
    >
      <Box id="leave-for-service-title" sx={{ fontSize: 14, fontWeight: 600, mb: "4px" }}>
        Leave the room and open another service?
      </Box>
      <Box component="p" sx={{ m: 0, fontSize: 12.5, color: "rgb(71, 85, 105)", lineHeight: 1.45 }}>
        This room shows this service only. The others stay in it.
      </Box>
      <Box sx={{ display: "flex", justifyContent: "flex-end", gap: "4px", mt: "16px" }}>
        <Button sx={CARD_BUTTON_SX} onClick={onCancel}>
          Stay
        </Button>
        <Button sx={CARD_BUTTON_QUIET_SX} onClick={onConfirm} autoFocus>
          Leave room
        </Button>
      </Box>
    </Dialog>
  );
}
