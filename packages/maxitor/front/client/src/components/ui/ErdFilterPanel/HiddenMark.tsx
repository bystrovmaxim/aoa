// src/components/ui/ErdFilterPanel/HiddenMark.tsx
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Paper from "@mui/material/Paper";
import Popper from "@mui/material/Popper";
import { useEffect, useRef } from "react";

/** What keeps a dimmed row off the screen, and the way to switch that on. */
export type RowHidden = { by: { key: string; label: string; iconSrc: string }[]; onReveal: () => void };

/** How long the pointer may leave the mark before its card closes: long enough to reach the card. */
const LEAVE_MS = 180;

function Disk({ iconSrc, label }: { iconSrc: string; label: string }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0 }}>
      <Box component="img" src={iconSrc} alt="" width={18} height={18} sx={{ flexShrink: 0, borderRadius: "50%" }} />
      <Box component="span" sx={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "#0f172a" }}>
        {label}
      </Box>
    </Box>
  );
}

type HiddenMarkProps = {
  row: string;
  label: string;
  iconSrc: string;
  hidden: RowHidden;
  /** The row whose card is open. */
  why: string | null;
  onWhy: (row: string | null) => void;
};

/**
 * The quiet mark of a row that is switched on and still has nothing on screen (spec 040, FR-028c). It opens a card in
 * the look of the change card: what is switched off above the row, an arrow down to the row, and one button that
 * switches those on.
 */
export function HiddenMark({ row, label, iconSrc, hidden, why, onWhy }: HiddenMarkProps) {
  const mark = useRef<HTMLButtonElement | null>(null);
  const leaving = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const open = why === row;
  const stay = () => clearTimeout(leaving.current);
  const leave = () => {
    clearTimeout(leaving.current);
    leaving.current = setTimeout(() => onWhy(null), LEAVE_MS);
  };
  useEffect(() => () => clearTimeout(leaving.current), []);
  const [only] = hidden.by;
  return (
    <>
      <ButtonBase
        ref={mark}
        aria-label={`What hides ${label}`}
        aria-expanded={open}
        data-testid="erd-filter-hidden-mark"
        onClick={() => onWhy(open ? null : row)}
        onMouseEnter={() => {
          stay();
          onWhy(row);
        }}
        onMouseLeave={leave}
        sx={{ position: "absolute", right: 0, top: "50%", transform: "translateY(-50%)", width: 16, height: 16, borderRadius: "4px", color: open ? "#475569" : "#94a3b8", "&:hover": { color: "#475569" } }}
      >
        <VisibilityOffOutlinedIcon sx={{ fontSize: 13 }} />
      </ButtonBase>
      <Popper open={open} anchorEl={() => mark.current ?? document.body} placement="right-start" modifiers={[{ name: "offset", options: { offset: [-10, 12] } }]} sx={{ zIndex: 1300 }}>
        <ClickAwayListener onClickAway={(event) => !mark.current?.contains(event.target as Node) && onWhy(null)}>
          <Paper
            role="dialog"
            aria-label={`What hides ${label}`}
            data-pointer-frame="filter-why"
            data-testid="erd-filter-hidden-card"
            elevation={0}
            onMouseEnter={stay}
            onMouseLeave={leave}
            sx={{ width: 212, boxSizing: "border-box", p: "10px 12px", fontSize: 12, lineHeight: 1.45, color: "#334155", bgcolor: "#fff", border: "1px solid rgba(15, 23, 42, 0.1)", borderRadius: "8px", boxShadow: "0 8px 30px rgba(15, 23, 42, 0.14), 0 1px 2px rgba(15, 23, 42, 0.06)" }}
          >
            <Box sx={{ fontWeight: 600, color: "#0f172a", mb: "2px" }}>{label} is hidden</Box>
            <Box sx={{ color: "#64748b", mb: "8px" }}>It depends on what is switched off:</Box>
            <Box sx={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              {hidden.by.map((reason) => (
                <Disk key={reason.key} iconSrc={reason.iconSrc} label={reason.label} />
              ))}
              <Box aria-hidden sx={{ width: 18, display: "flex", justifyContent: "center", color: "#94a3b8" }}>
                <svg viewBox="0 0 12 16" width={12} height={16}>
                  <path fill="none" stroke="currentColor" strokeWidth={1.4} strokeLinecap="round" strokeLinejoin="round" d="M6 1v13M2.5 10.5 6 14l3.5-3.5" />
                </svg>
              </Box>
              <Box sx={{ opacity: 0.5 }}>
                <Disk iconSrc={iconSrc} label={label} />
              </Box>
            </Box>
            <ButtonBase
              data-testid="erd-filter-reveal"
              onClick={() => {
                hidden.onReveal();
                onWhy(null);
              }}
              sx={{ mt: "10px", width: "100%", height: 28, borderRadius: "8px", fontSize: 12.5, fontWeight: 600, color: "#0f172a", bgcolor: "rgba(15, 23, 42, 0.05)", "&:hover": { bgcolor: "rgba(15, 23, 42, 0.1)" } }}
            >
              {hidden.by.length === 1 ? `Show ${only.label}` : `Show all ${hidden.by.length}`}
            </ButtonBase>
          </Paper>
        </ClickAwayListener>
      </Popper>
    </>
  );
}
