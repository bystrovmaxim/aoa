// src/components/history/VersionPicker/VersionPicker.tsx
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import Popover from "@mui/material/Popover";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import { useState, type ReactNode } from "react";
import type { HistoryVersion } from "@/api/history";
import { VersionTrack } from "@/components/history/VersionTrack";
import { pickerSubtitle } from "@/model/historyMode";

/** Width of the picker and of its track. */
const WIDTH = 520;

export type VersionPickerProps = {
  /** The button the picker opens under; ``null`` keeps it closed. */
  anchor: HTMLElement | null;
  onClose: () => void;
  title: string;
  versions: readonly HistoryVersion[];
  live: string | null;
  value: string | null;
  onChange: (b: string) => void;
  /** The link **Copy link** hands out: this version, the key after ``#key=``. */
  link: string;
  /** Under the track: the chosen version's message. */
  children?: ReactNode;
  /** On a phone the picker is a sheet from the bottom, its track as wide as the screen (FR-031). */
  phone?: boolean;
};

/**
 * The picker (spec 037, FR-014, FR-015): over the diagram, under the version button; it starts
 * closed, a click outside or Escape closes it, and choosing a version leaves it open. The head names
 * the service, counts its versions, offers **Copy link**, and shows the mode switch — One active,
 * Diff and Side by side greyed out, "comes later". On a phone it is a sheet from the bottom with the
 * same head, track and message, every point a 44 px touch target.
 */
export function VersionPicker({ anchor, onClose, title, versions, live, value, onChange, link, children, phone = false }: VersionPickerProps) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard unavailable: nothing to confirm.
    }
  }

  const trackWidth = phone ? Math.max(240, window.innerWidth - 32) : WIDTH;
  const content = (
    <>
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5, mb: 1.5 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box sx={{ fontSize: 14, fontWeight: 600, color: "rgb(30, 41, 59)" }}>{title}</Box>
          <Box sx={{ fontSize: 12, color: "rgb(100, 116, 139)" }}>{pickerSubtitle(versions.length, Boolean(live))}</Box>
        </Box>
        <Button size="small" onClick={() => void copy()} sx={{ textTransform: "none", fontSize: 12 }}>
          {copied ? "Link copied" : "Copy link"}
        </Button>
        <ToggleButtonGroup size="small" exclusive value="one" aria-label="Mode">
          <ToggleButton value="one" sx={{ textTransform: "none", fontSize: 12, py: 0.25 }}>
            One
          </ToggleButton>
          {["Diff", "Side by side"].map((mode) => (
            <Tooltip key={mode} title="comes later">
              <span>
                <ToggleButton value={mode} disabled aria-disabled="true" sx={{ textTransform: "none", fontSize: 12, py: 0.25 }}>
                  {mode}
                </ToggleButton>
              </span>
            </Tooltip>
          ))}
        </ToggleButtonGroup>
      </Box>
      <VersionTrack versions={versions} live={live} value={value} onChange={onChange} width={trackWidth} touch={phone} />
      {children}
    </>
  );

  if (phone) {
    return (
      <Drawer anchor="bottom" open={anchor !== null} onClose={onClose} slotProps={{ paper: { role: "dialog", "aria-label": "Pick a version", sx: { p: 2, borderTopLeftRadius: 12, borderTopRightRadius: 12 } } }}>
        {content}
      </Drawer>
    );
  }

  return (
    <Popover
      open={anchor !== null}
      anchorEl={anchor}
      onClose={onClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      transformOrigin={{ vertical: "top", horizontal: "right" }}
      slotProps={{ paper: { role: "dialog", "aria-label": "Pick a version", sx: { width: WIDTH + 32, maxWidth: "calc(100% - 24px)", p: 2, mt: "6px" } } }}
    >
      {content}
    </Popover>
  );
}
