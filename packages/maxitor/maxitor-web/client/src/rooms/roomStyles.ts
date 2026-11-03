// src/rooms/roomStyles.ts
/**
 * The room controls' look, taken from the design mockup (specs/028-maxitor-rooms/mockup): slate text,
 * small uppercase labels, quiet buttons like the zoom bar, no blue accent.
 */

/** The workspace surface the top row sits on. */
export const WORKSPACE_SURFACE = "#f4f5f7";

/** Height of the desktop row: the left panel's header row, so the two lines meet. */
export const ROOM_ROW_HEIGHT = 38;

/** A text button of the row: *Open room*, *Copy link*, *Leave room*. */
export const ROW_BUTTON_SX = {
  height: 28,
  minWidth: 0,
  px: "10px",
  gap: "6px",
  borderRadius: "8px",
  color: "#475569",
  fontSize: 12.5,
  fontWeight: 500,
  textTransform: "none",
  whiteSpace: "nowrap",
  // Icons as in the left panel's rows (spec 029, FR-050).
  "& svg": { fontSize: 16 },
  "&:hover": { bgcolor: "rgba(15, 23, 42, 0.08)", color: "#0f172a" },
} as const;

/** The emphasised row button: *Open room* outside a room. */
export const ROW_BUTTON_PRIMARY_SX = { ...ROW_BUTTON_SX, color: "#0f172a", bgcolor: "rgba(15, 23, 42, 0.06)" } as const;

/** A button inside a card or dialog. */
export const CARD_BUTTON_SX = {
  height: 30,
  minWidth: 0,
  px: "12px",
  borderRadius: "8px",
  fontSize: 12.5,
  fontWeight: 500,
  textTransform: "none",
  whiteSpace: "nowrap",
  color: "#64748b",
} as const;

/** The card or dialog button that does the thing: *Open room*, *Join*, *Copy link*. */
export const CARD_BUTTON_QUIET_SX = {
  ...CARD_BUTTON_SX,
  bgcolor: "rgba(15, 23, 42, 0.08)",
  color: "#0f172a",
  fontWeight: 600,
  "&:hover": { bgcolor: "rgba(15, 23, 42, 0.12)" },
} as const;

/** Popovers and dialogs. */
export const CARD_PAPER_SX = {
  bgcolor: "#fff",
  border: "1px solid rgba(15, 23, 42, 0.1)",
  borderRadius: "8px",
  boxShadow: "0 8px 30px rgba(15, 23, 42, 0.14), 0 1px 2px rgba(15, 23, 42, 0.06)",
  color: "rgb(30, 41, 59)",
} as const;

/** A small uppercase label: *Your name*, *Invite to this room*. */
export const LABEL_CAPS_SX = {
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  color: "rgb(100, 116, 139)",
} as const;

/** Muted help text under a field or in a card. */
export const HINT_SX = { fontSize: 11.5, color: "rgb(100, 116, 139)", lineHeight: 1.45 } as const;
