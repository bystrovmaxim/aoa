// src/components/history/VersionButton/VersionButton.tsx
import ButtonBase from "@mui/material/ButtonBase";
import { forwardRef } from "react";

export type VersionButtonProps = {
  /** The name of the version shown: ``Live``, ``#147`` (its pull request), ``#57`` (its place in the history). */
  name: string;
  open: boolean;
  /** Called with the button itself, which the picker opens under. */
  onClick: (button: HTMLElement) => void;
  /** In Diff, what the diagram on screen counts (spec 038, FR-025); ``null`` or absent shows no counts. */
  counts?: { added: number; removed: number; changed: number } | null;
  /** On a phone (spec 038, FR-033): the button never grows past its row, its name cut with an ellipsis before the counts are. */
  compact?: boolean;
};

/** The colours of the counts, the ERD's marks' own. */
const COUNT_COLOUR = { added: "#16a34a", removed: "#dc2626", changed: "#d97706" } as const;

/** The counts as the button says them: ``+15 −1 ~3``, or ``no changes``. */
export function countsText(counts: { added: number; removed: number; changed: number }): string {
  return counts.added + counts.removed + counts.changed === 0 ? "no changes" : `+${counts.added} −${counts.removed} ~${counts.changed}`;
}

/** The mockup's history icon: a clock with the arrow of time turned back. */
export function HistoryIcon() {
  return (
    <svg viewBox="0 0 24 24" width={15} height={15} aria-hidden style={{ flexShrink: 0, color: "#64748b" }}>
      <g fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
        <path d="M3.75 12a8.25 8.25 0 1 0 2.42-5.83" />
        <path d="M3.75 4.5v3.75H7.5" />
        <path d="M12 7.75V12l2.75 1.75" />
      </g>
    </svg>
  );
}

/**
 * The one button that says which version is shown (spec 037, FR-013), as the mockup draws it: at the
 * left of the top row, the history's clock, the version's name in bold, a chevron. It opens the picker;
 * it exists only while a history with something to pick is open (M2–M6). In Diff it names both versions and
 * carries the diagram's counts — ``◷ A 0.8.0 → B 0.9.0  +15 −1 ~3 ▾`` — or "no changes" (spec 038, FR-025, FR-026); on a
 * phone the page gives it the short names (``A #128 → B #129``) and it cuts the name, never the counts (FR-033).
 */
export const VersionButton = forwardRef<HTMLButtonElement, VersionButtonProps>(function VersionButton({ name, open, onClick, counts = null, compact = false }, ref) {
  return (
    <ButtonBase
      ref={ref}
      onClick={(event) => onClick(event.currentTarget)}
      aria-haspopup="dialog"
      aria-expanded={open}
      aria-label={counts ? `Versions: ${name}, ${countsText(counts)}` : `Version: ${name}`}
      sx={{
        height: 28,
        pl: "8px",
        pr: "6px",
        gap: "6px",
        borderRadius: "8px",
        bgcolor: open ? "rgba(15, 23, 42, 0.1)" : "rgba(15, 23, 42, 0.05)",
        fontSize: 12.5,
        color: "#334155",
        whiteSpace: "nowrap",
        ...(compact && { maxWidth: "100%", minWidth: 0 }),
        "&:hover": { bgcolor: "rgba(15, 23, 42, 0.1)" },
      }}
    >
      <HistoryIcon />
      <b data-testid="version-name" style={{ color: "#0f172a", fontWeight: 600, ...(compact && { minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }) }}>
        {name}
      </b>
      {counts &&
        (countsText(counts) === "no changes" ? (
          <span data-testid="diff-counts" style={{ color: "#64748b", marginLeft: 4, flexShrink: 0 }}>
            no changes
          </span>
        ) : (
          <span data-testid="diff-counts" style={{ marginLeft: 4, fontWeight: 600, display: "inline-flex", gap: 5, flexShrink: 0 }}>
            <span style={{ color: COUNT_COLOUR.added }}>+{counts.added}</span>
            <span style={{ color: COUNT_COLOUR.removed }}>−{counts.removed}</span>
            <span style={{ color: COUNT_COLOUR.changed }}>~{counts.changed}</span>
          </span>
        ))}
      <svg viewBox="0 0 24 24" width={15} height={15} aria-hidden style={{ color: "#64748b", flexShrink: 0 }}>
        <path fill="currentColor" d="M16.59 8.59 12 13.17 7.41 8.59 6 10l6 6 6-6z" />
      </svg>
    </ButtonBase>
  );
});
