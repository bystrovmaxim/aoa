// src/rooms/RoomBar/RoomBanner.tsx
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import BlockIcon from "@mui/icons-material/Block";
import CloseIcon from "@mui/icons-material/Close";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import type { RoomBanner as RoomBannerState } from "@/rooms/useRoomSession";

export type RoomBannerProps = {
  banner: RoomBannerState | null;
  onOpenRoom: () => void;
  onDismiss: () => void;
};

const LOOK = {
  info: { bgcolor: "#fff", border: "1px solid rgba(15, 23, 42, 0.12)", color: "#1e293b" },
  warn: { bgcolor: "#fffbeb", border: "1px solid #fcd34d", color: "#78350f" },
  error: { bgcolor: "#fef2f2", border: "1px solid #fca5a5", color: "#7f1d1d" },
} as const;

/**
 * A sentence across the top of the workspace: why the tab could not stay in a room — *This room has
 * ended* with **Open room**, *this room already has 20 people*, a foreign page (mockup screens 18,
 * 19) — or what is wrong with its picture: Maxitor reloading, pointers off (screens 15, 17).
 */
export function RoomBanner({ banner, onOpenRoom, onDismiss }: RoomBannerProps) {
  if (!banner) return null;
  const Icon = banner.kind === "info" ? InfoOutlinedIcon : banner.kind === "warn" ? WarningAmberIcon : BlockIcon;
  return (
    <Box
      role="alert"
      sx={{
        position: "absolute",
        top: 12,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 59,
        display: "flex",
        alignItems: "center",
        gap: "10px",
        maxWidth: "calc(100% - 24px)",
        p: "9px 10px 9px 12px",
        borderRadius: "8px",
        fontSize: 12.5,
        lineHeight: 1.4,
        boxShadow: "0 2px 10px rgba(0, 0, 0, 0.08)",
        ...LOOK[banner.kind],
      }}
    >
      <Icon sx={{ fontSize: 16, flexShrink: 0 }} />
      <span>{banner.text}</span>
      {banner.open && (
        <Button
          onClick={onOpenRoom}
          sx={{ height: 26, minWidth: 0, px: "10px", borderRadius: "6px", fontSize: 12, fontWeight: 600, textTransform: "none", whiteSpace: "nowrap", bgcolor: "rgba(15, 23, 42, 0.08)", color: "inherit" }}
        >
          Open room
        </Button>
      )}
      <IconButton aria-label="Dismiss" size="small" onClick={onDismiss} sx={{ color: "inherit", p: "2px" }}>
        <CloseIcon sx={{ fontSize: 16 }} />
      </IconButton>
    </Box>
  );
}
