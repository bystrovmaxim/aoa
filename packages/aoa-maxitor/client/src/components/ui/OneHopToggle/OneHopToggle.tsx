// src/components/ui/OneHopToggle/OneHopToggle.tsx
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";

export type OneHopToggleProps = {
  checked: boolean;
  onChange: (next: boolean) => void;
};

/** Same strip as former ``#neighborhood-filter`` / 13px checkbox + label. */
export function OneHopToggle({ checked, onChange }: OneHopToggleProps) {
  return (
    <FormControlLabel
      sx={{
        m: 0,
        ml: 0,
        mr: 0,
        gap: "5px",
        height: 30,
        px: "8px",
        borderRadius: "8px",
        bgcolor: "transparent",
        cursor: "pointer",
        alignItems: "center",
        userSelect: "none",
        "&:hover": { bgcolor: "rgba(15, 23, 42, 0.06)" },
        "& .MuiFormControlLabel-label": {
          fontSize: 11,
          fontWeight: 500,
          letterSpacing: "0.01em",
          color: "#64748b",
        },
      }}
      control={
        <Checkbox
          checked={checked}
          onChange={(_, v) => onChange(v)}
          disableRipple
          size="small"
          sx={{
            p: 0,
            m: 0,
            width: 13,
            height: 13,
            color: "#94a3b8",
            "&.Mui-checked": { color: "#3b82f6" },
            "& .MuiSvgIcon-root": {
              width: 13,
              height: 13,
              fontSize: 13,
            },
          }}
        />
      }
      label="1-hop"
    />
  );
}
