// src/components/navigation/LeftSidebar/ReloadServiceButton.tsx
import RefreshIcon from "@mui/icons-material/Refresh";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";

type Props = {
  onReload: () => void;
  reloading: boolean;
};

/** "Reload from service": rebuild the open source, one explicit request per click. */
export function ReloadServiceButton({ onReload, reloading }: Props) {
  return (
    <Tooltip title={reloading ? "Reloading from service…" : "Reload from service"} placement="right" enterDelay={400}>
      <span>
        <IconButton
          type="button"
          onClick={onReload}
          disabled={reloading}
          aria-label="Reload from service"
          disableRipple
          disableFocusRipple
          sx={{
            m: 0,
            ml: 0.5,
            p: 0,
            width: 32,
            minWidth: 32,
            height: 32,
            color: "rgb(100, 116, 139)",
            borderRadius: 1.5,
            "&:hover": { bgcolor: "rgba(15, 23, 42, 0.07)" },
            "&.Mui-disabled": { color: "rgba(100, 116, 139, 0.5)" },
          }}
        >
          <RefreshIcon sx={{ fontSize: 17.6 }} />
        </IconButton>
      </span>
    </Tooltip>
  );
}
