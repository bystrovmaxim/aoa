// src/components/navigation/LeftSidebar/ServiceUrlInput.tsx
import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import LinkIcon from "@mui/icons-material/Link";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import OutlinedInput from "@mui/material/OutlinedInput";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useState } from "react";
import { type OpenedHistory, openHistory } from "@/api/history";
import { loadGraph } from "@/api/load";
import { type History, mask, parseHistory } from "@/lib/historyAddress";
import { rememberKey } from "@/lib/historyKey";
import { describeRecent, getRecent, pushRecent, pushServiceUrl, removeRecent } from "@/lib/serviceUrlHistory";

const SB = {
  text: "rgb(30, 41, 59)",
  textSecondary: "rgb(71, 85, 105)",
  icon: "rgb(100, 116, 139)",
  hover: "rgba(15, 23, 42, 0.07)",
  border: "rgba(15, 23, 42, 0.18)",
  borderFocus: "rgba(15, 23, 42, 0.45)",
} as const;

type Props = {
  onLoaded: (serviceUrl: string) => void;
  /** A history was opened from the field or from Recent (spec 037); without it, histories are only recorded. */
  onHistoryOpened?: (history: OpenedHistory, key: string) => void;
};

const COPY_FEEDBACK_MS = 1500;

/**
 * The address field and Recent. A read key in an address is shown as eight dots unless the field is
 * being edited, and the eye reveals it until it is clicked again or the field loses focus (spec 037,
 * FR-010); Recent says what each address turned out to be and lets each be removed, key and all (FR-012).
 */
export function ServiceUrlInput({ onLoaded, onHistoryOpened }: Props) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [, setRecentVersion] = useState(0);
  const history = getRecent();
  const hasKey = url.includes("#key=");
  const shown = editing || revealed || !hasKey ? url : mask(url);

  async function copyToClipboard(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedUrl(value);
      setTimeout(() => setCopiedUrl((cur) => (cur === value ? null : cur)), COPY_FEEDBACK_MS);
    } catch {
      // Clipboard permission denied or unavailable — silently ignore, row click still loads the URL.
    }
  }

  async function open(found: History) {
    const key = found.kind === "private" ? found.key : "";
    const opened = await openHistory(found.name, key);
    if (key) rememberKey(found.name, key);
    pushRecent({ address: found.kind === "private" ? `${found.name}#key=${key}` : found.link, kind: "history", name: opened.title, versions: opened.count, live: Boolean(opened.live) });
    onHistoryOpened?.(opened, key);
  }

  async function submit(value: string) {
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    try {
      const found = parseHistory(trimmed);
      if (found) {
        await open(found);
      } else {
        await loadGraph(trimmed);
        pushServiceUrl(trimmed);
        onLoaded(trimmed);
      }
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
        value={shown}
        onChange={(e) => setUrl(e.target.value)}
        onFocus={() => setEditing(true)}
        onBlur={() => {
          setEditing(false);
          setRevealed(false);
        }}
        inputProps={{ "aria-label": "Service or history address" }}
        onKeyDown={(e) => {
          if (e.key === "Enter") void submit(url);
        }}
        disabled={loading}
        error={Boolean(error)}
        endAdornment={
          <InputAdornment position="end">
            {hasKey && !editing && (
              <IconButton
                size="small"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => setRevealed((value) => !value)}
                aria-label={revealed ? "Hide the key" : "Show the key"}
                aria-pressed={revealed}
                sx={{ p: 0.25, mr: 0.25, color: SB.icon, "&:hover": { color: SB.text } }}
              >
                {revealed ? <VisibilityOffIcon sx={{ fontSize: 16 }} /> : <VisibilityIcon sx={{ fontSize: 16 }} />}
              </IconButton>
            )}
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
            {history.map((record) => {
              const h = record.address;
              return (
                <ListItem
                  key={h}
                  disablePadding
                  sx={{
                    borderRadius: 1.5,
                    "&:hover": { bgcolor: SB.hover },
                    "&:hover .row-copy-btn, &:focus-within .row-copy-btn": { opacity: 1 },
                  }}
                  secondaryAction={
                    <Box sx={{ display: "flex" }}>
                      <Tooltip title={copiedUrl === h ? "Copied" : "Copy address"} placement="top">
                        <IconButton
                          className="row-copy-btn"
                          size="small"
                          disabled={loading}
                          onClick={(e) => {
                            e.stopPropagation();
                            void copyToClipboard(h);
                          }}
                          aria-label="Copy address"
                          sx={{
                            opacity: 0,
                            transition: "opacity .15s",
                            color: copiedUrl === h ? "success.main" : SB.icon,
                            "&:hover": { color: copiedUrl === h ? "success.main" : SB.text },
                          }}
                        >
                          {copiedUrl === h ? <CheckIcon sx={{ fontSize: 15 }} /> : <ContentCopyIcon sx={{ fontSize: 15 }} />}
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Remove from Recent" placement="top">
                        <IconButton
                          className="row-copy-btn"
                          size="small"
                          disabled={loading}
                          onClick={(e) => {
                            e.stopPropagation();
                            removeRecent(h);
                            setRecentVersion((value) => value + 1);
                          }}
                          aria-label="Remove from Recent"
                          sx={{ opacity: 0, transition: "opacity .15s", color: SB.icon, "&:hover": { color: SB.text } }}
                        >
                          <CloseIcon sx={{ fontSize: 15 }} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  }
                >
                  <ListItemButton
                    disabled={loading}
                    onClick={() => {
                      setUrl(h);
                      void submit(h);
                    }}
                    sx={{
                      borderRadius: 1.5,
                      py: 0.3,
                      pr: 8,
                      minHeight: 30,
                      "&:hover": { bgcolor: "transparent" },
                    }}
                  >
                    <ListItemText
                      primary={mask(h)}
                      secondary={describeRecent(record)}
                      primaryTypographyProps={{
                        noWrap: true,
                        sx: { fontSize: 12, color: SB.textSecondary, fontFamily: "ui-monospace, monospace" },
                      }}
                      secondaryTypographyProps={{ noWrap: true, sx: { fontSize: 10.5, color: SB.icon } }}
                    />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        </Box>
      )}
    </Box>
  );
}
