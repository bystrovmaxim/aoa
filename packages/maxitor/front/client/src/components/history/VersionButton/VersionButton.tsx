// src/components/history/VersionButton/VersionButton.tsx
import ButtonBase from "@mui/material/ButtonBase";
import { forwardRef } from "react";

export type VersionButtonProps = {
  /** The name of the version shown: ``Live``, ``v0.11.0``, ``v0.11.0 · #147``, ``#12``, a short commit. */
  name: string;
  open: boolean;
  /** Called with the button itself, which the picker opens under. */
  onClick: (button: HTMLElement) => void;
};

/**
 * The one button that says which version is shown (spec 037, FR-013): ``◷ <name> ▾``. It opens the
 * picker; it exists only while a history with something to pick is open (M2–M6).
 */
export const VersionButton = forwardRef<HTMLButtonElement, VersionButtonProps>(function VersionButton({ name, open, onClick }, ref) {
  return (
    <ButtonBase
      ref={ref}
      onClick={(event) => onClick(event.currentTarget)}
      aria-haspopup="dialog"
      aria-expanded={open}
      aria-label={`Version: ${name}`}
      sx={{
        height: 28,
        px: 1.25,
        borderRadius: "6px",
        border: "1px solid rgba(15, 23, 42, 0.18)",
        bgcolor: open ? "rgba(37, 99, 235, 0.08)" : "rgba(255, 255, 255, 0.7)",
        fontSize: 12.5,
        fontWeight: 600,
        color: "rgb(30, 41, 59)",
        gap: 0.75,
        whiteSpace: "nowrap",
        "&:hover": { bgcolor: "rgba(15, 23, 42, 0.05)" },
      }}
    >
      <span aria-hidden>◷</span>
      <span>{name}</span>
      <span aria-hidden style={{ fontSize: 10 }}>▾</span>
    </ButtonBase>
  );
});
