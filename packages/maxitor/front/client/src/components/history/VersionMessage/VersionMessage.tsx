// src/components/history/VersionMessage/VersionMessage.tsx
import Box from "@mui/material/Box";
import type { HistoryVersion } from "@/api/history";
import { linkify } from "@/lib/linkify";

/** The thin line above what stands under the track. */
const DIVIDER = "1px solid rgba(15, 23, 42, 0.06)";

export type VersionMessageProps = {
  /** The chosen version, or ``null`` for Live. */
  version: HistoryVersion | null;
  /** ``owner/repo`` when ``#123`` is a pull request on GitHub, else ``null``. */
  repository: string | null;
  /** For Live: its closing line — alone, or under the newest version's message when Live runs exactly that version. */
  liveLine?: string;
};

/** The message of ``version``: its pull request's title and body, or its commit's message. */
export function messageOf(version: HistoryVersion): string {
  return version.pr ? `${version.pr.title}\n\n${version.pr.body}`.trimEnd() : (version.message ?? "").trimEnd();
}

/** The mockup's Live icon: a point with waves on both sides. */
export function LiveIcon() {
  return (
    <svg viewBox="0 0 24 24" width={15} height={15} aria-hidden style={{ display: "block" }}>
      <g fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round">
        <circle cx={12} cy={12} r={2} fill="currentColor" />
        <path d="M8.3 8.3a5.2 5.2 0 0 0 0 7.4M15.7 8.3a5.2 5.2 0 0 1 0 7.4M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8" />
      </g>
    </svg>
  );
}

/**
 * The chosen version's message under the track (spec 037, FR-028 – FR-030), as the mockup draws it:
 * below a thin line, in a light grey box, whole, with nothing above it, line breaks kept, long lines
 * wrapped by words; plain text whose only links are addresses and ``#123``, each opening in a new tab
 * without telling the page it opens where it came from. The box stops at nine lines and scrolls inside
 * with a thin scrollbar that shows how much more there is; nothing is faded. Live has no message: a closing line
 * with its icon says when it was checked, or since when it cannot be reached.
 */
export function VersionMessage({ version, repository, liveLine }: VersionMessageProps) {
  const text = version ? messageOf(version) : "";

  const foot = liveLine !== undefined && (
    <Box
      data-testid="live-line"
      sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", columnGap: 1, rowGap: "2px", mt: 1, pt: "10px", borderTop: DIVIDER, fontSize: 12, color: "#475569" }}
    >
      <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: "5px", fontWeight: 600, color: "#0f172a", whiteSpace: "nowrap" }}>
        <LiveIcon />
        Live
      </Box>
      <span>{liveLine}</span>
    </Box>
  );

  if (!version) return foot || null;

  return (
    <Box sx={{ mt: 1, pt: "6px", borderTop: DIVIDER }}>
      <Box
        data-testid="message"
        sx={{
          m: "2px 0 6px",
          p: "8px 10px",
          // The mockup's 180 px of text, its padding and border outside it.
          maxHeight: 180,
          boxSizing: "content-box",
          overflowY: "auto",
          whiteSpace: "pre-wrap",
          overflowWrap: "anywhere",
          fontSize: 12,
          lineHeight: 1.5,
          color: "#334155",
          bgcolor: "#f8fafc",
          border: "1px solid rgba(15, 23, 42, 0.06)",
          borderRadius: "6px",
          userSelect: "text",
          "&::-webkit-scrollbar": { width: 6 },
          "&::-webkit-scrollbar-thumb": { background: "#cbd5e1", borderRadius: 3 },
          "&::-webkit-scrollbar-track": { background: "transparent", margin: "4px 0" },
          "& a": { color: "#2563eb" },
        }}
      >
        {linkify(text, repository).map((part, index) =>
          part.kind === "text" ? (
            <span key={index}>{part.text}</span>
          ) : (
            <a key={index} href={part.href} target="_blank" rel="noopener noreferrer">
              {part.text}
            </a>
          ),
        )}
      </Box>
      {foot}
    </Box>
  );
}
