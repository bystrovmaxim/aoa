// src/components/navigation/LeftSidebar/ServiceUrlInput.tsx
import LinkIcon from "@mui/icons-material/Link";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import OutlinedInput from "@mui/material/OutlinedInput";
import Typography from "@mui/material/Typography";
import { useState } from "react";
import { loadGraph } from "@/api/load";
import { getServiceUrlHistory, pushServiceUrl } from "@/lib/serviceUrlHistory";

const SB = {
  text: "rgb(30, 41, 59)",
  textSecondary: "rgb(71, 85, 105)",
  icon: "rgb(100, 116, 139)",
  hover: "rgba(15, 23, 42, 0.07)",
  border: "rgba(15, 23, 42, 0.18)",
  borderFocus: "rgba(15, 23, 42, 0.45)",
} as const;

type Props = {
  onLoaded: () => void;
};

export function ServiceUrlInput({ onLoaded }: Props) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const history = getServiceUrlHistory();

  async function submit(value: string) {
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    try {
      await loadGraph(trimmed);
      pushServiceUrl(trimmed);
      onLoaded();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box sx={{ px: 1.25, pt: 1.5, pb: 1 }}>
      <Typography
        variant="body2"
        sx={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", color: SB.icon, mb: 0.75, textTransform: "uppercase" }}
      >
        AOA Service URL
      </Typography>

      <OutlinedInput
        fullWidth
        size="small"
        placeholder="http://127.0.0.1:8001"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") void submit(url);
        }}
        disabled={loading}
        error={Boolean(error)}
        endAdornment={
          <InputAdornment position="end">
            {loading ? (
              <CircularProgress size={16} thickness={4} sx={{ color: SB.icon }} />
            ) : (
              <IconButton
                size="small"
                disabled={!url.trim()}
                onClick={() => void submit(url)}
                aria-label="Load graph"
                sx={{ p: 0.25, color: SB.icon, "&:hover": { color: SB.text } }}
              >
                <LinkIcon sx={{ fontSize: 18 }} />
              </IconButton>
            )}
          </InputAdornment>
        }
        sx={{
          fontSize: 12.5,
          bgcolor: "rgba(255,255,255,0.7)",
          "& .MuiOutlinedInput-notchedOutline": { borderColor: SB.border },
          "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: SB.borderFocus },
          "&.Mui-focused .MuiOutlinedInput-notchedOutline": { borderColor: SB.borderFocus },
        }}
      />

      {error && (
        <Typography variant="body2" sx={{ fontSize: 11.5, color: "error.main", mt: 0.75, lineHeight: 1.4 }}>
          {error}
        </Typography>
      )}

      {history.length > 0 && (
        <Box sx={{ mt: 1.25 }}>
          <Typography
            variant="body2"
            sx={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", color: SB.icon, mb: 0.5, textTransform: "uppercase" }}
          >
            Recent
          </Typography>
          <List dense disablePadding>
            {history.map((h) => (
              <ListItemButton
                key={h}
                disabled={loading}
                onClick={() => {
                  setUrl(h);
                  void submit(h);
                }}
                sx={{
                  borderRadius: 1.5,
                  py: 0.3,
                  minHeight: 30,
                  "&:hover": { bgcolor: SB.hover },
                }}
              >
                <ListItemText
                  primary={h}
                  primaryTypographyProps={{
                    noWrap: true,
                    sx: { fontSize: 12, color: SB.textSecondary, fontFamily: "ui-monospace, monospace" },
                  }}
                />
              </ListItemButton>
            ))}
          </List>
        </Box>
      )}
    </Box>
  );
}
