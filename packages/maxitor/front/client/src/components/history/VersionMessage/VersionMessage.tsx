// src/components/history/VersionMessage/VersionMessage.tsx
import Box from "@mui/material/Box";
import { useEffect, useRef, useState } from "react";
import type { HistoryVersion } from "@/api/history";
import { linkify } from "@/lib/linkify";

/** How many lines the box shows before it scrolls inside (FR-029). */
export const MESSAGE_LINES = 9;
const LINE_HEIGHT = 18;

export type VersionMessageProps = {
  /** The chosen version, or ``null`` for Live. */
  version: HistoryVersion | null;
  /** ``owner/repo`` when ``#123`` is a pull request on GitHub, else ``null``. */
  repository: string | null;
  /** For Live: its closing line. */
  liveLine?: string;
};

/** The message of ``version``: its pull request's title and body, or its commit's message. */
export function messageOf(version: HistoryVersion): string {
  return version.pr ? `${version.pr.title}\n\n${version.pr.body}`.trimEnd() : (version.message ?? "").trimEnd();
}

/**
 * The chosen version's message under the track (spec 037, FR-028 – FR-030): whole, with nothing above
 * it, line breaks kept, long lines wrapped by words; plain text whose only links are addresses and
 * ``#123``, each opening in a new tab without telling the page it opens where it came from. The box
 * stops at nine lines and scrolls inside with a thin scrollbar, its lower edge fading while more is
 * below. Live has no message: a closing line says when it was checked, or since when it cannot be reached.
 */
export function VersionMessage({ version, repository, liveLine }: VersionMessageProps) {
  const box = useRef<HTMLDivElement | null>(null);
  const [moreBelow, setMoreBelow] = useState(false);
  const text = version ? messageOf(version) : "";

  const measure = () => {
    const element = box.current;
    if (element) setMoreBelow(element.scrollTop + element.clientHeight < element.scrollHeight - 1);
  };
  useEffect(measure, [text]);

  if (!version) {
    return (
      <Box data-testid="live-line" sx={{ mt: 1.25, fontSize: 12, color: "rgb(100, 116, 139)" }}>
        {liveLine}
      </Box>
    );
  }

  return (
    <Box
      ref={box}
      data-testid="message"
      data-more-below={moreBelow || undefined}
      onScroll={measure}
      sx={{
        mt: 1.25,
        maxHeight: MESSAGE_LINES * LINE_HEIGHT,
        overflowY: "auto",
        whiteSpace: "pre-wrap",
        overflowWrap: "anywhere",
        fontSize: 12.5,
        lineHeight: `${LINE_HEIGHT}px`,
        color: "rgb(30, 41, 59)",
        userSelect: "text",
        scrollbarWidth: "thin",
        maskImage: moreBelow ? "linear-gradient(to bottom, black calc(100% - 28px), transparent 100%)" : "none",
        WebkitMaskImage: moreBelow ? "linear-gradient(to bottom, black calc(100% - 28px), transparent 100%)" : "none",
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
  );
}
