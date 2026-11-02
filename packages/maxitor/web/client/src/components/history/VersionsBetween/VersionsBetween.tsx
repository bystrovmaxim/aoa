// src/components/history/VersionsBetween/VersionsBetween.tsx
import Box from "@mui/material/Box";
import { useState } from "react";
import type { HistoryVersion } from "@/api/history";
import { messageOf, VersionMessage } from "@/components/history/VersionMessage";
import { trackKeys, type Range } from "@/lib/versionRange";
import { shortSha, shownNameOf } from "@/lib/versionNames";

export type VersionsBetweenProps = {
  versions: readonly HistoryVersion[];
  live: string | null;
  /** The newest version's sha when Live runs exactly its graph: the two are one point. */
  liveIs?: string | null;
  proposals?: readonly HistoryVersion[];
  range: Range;
  /** ``owner/repo`` when ``#123`` is a pull request on GitHub, else ``null``. */
  repository: string | null;
};

/** The history's versions strictly between A and B on the track, newest first: open pull requests are not on the way from A to B. */
export function versionsBetween(
  versions: readonly HistoryVersion[],
  live: string | null,
  liveIs: string | null,
  proposals: readonly HistoryVersion[],
  range: Range,
): HistoryVersion[] {
  const points = trackKeys(versions, live, liveIs, proposals);
  const from = points.indexOf(range.a);
  const to = points.indexOf(range.b);
  if (from < 0 || to <= from) return [];
  const inner = points.slice(from + 1, to).map((key) => versions.find((version) => shortSha(version) === key));
  return inner.filter((version): version is HistoryVersion => version !== undefined).reverse();
}

/**
 * The versions between A and B (spec 038, FR-031): one line, "N versions between", absent when A and B are
 * neighbours; it opens them newest first, each closed row its name and its message's first line, a click on
 * a row opening its whole message.
 */
export function VersionsBetween({ versions, live, liveIs = null, proposals = [], range, repository }: VersionsBetweenProps) {
  const [open, setOpen] = useState(false);
  const [shown, setShown] = useState<string | null>(null);
  const between = versionsBetween(versions, live, liveIs, proposals, range);
  if (between.length === 0) return null;

  return (
    <Box sx={{ mt: 1 }}>
      <Box
        component="button"
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((was) => !was)}
        sx={{ border: 0, p: 0, bgcolor: "transparent", cursor: "pointer", fontSize: 12, color: "#475569", "&:hover": { color: "#0f172a" } }}
      >
        {open ? "▾" : "▸"} {between.length === 1 ? "1 version between" : `${between.length} versions between`}
      </Box>
      {open && (
        <Box component="ul" aria-label="Versions between" sx={{ listStyle: "none", m: "6px 0 0", p: 0 }}>
          {between.map((version) => {
            const key = shortSha(version);
            const whole = shown === key;
            return (
              <Box component="li" key={key} sx={{ borderTop: "1px solid rgba(15, 23, 42, 0.06)" }}>
                <Box
                  component="button"
                  type="button"
                  aria-expanded={whole}
                  onClick={() => setShown(whole ? null : key)}
                  sx={{ display: "flex", gap: 1, width: "100%", border: 0, p: "5px 0", bgcolor: "transparent", cursor: "pointer", textAlign: "left", fontSize: 12, color: "#334155", minWidth: 0 }}
                >
                  <Box component="span" sx={{ fontWeight: 600, color: "#0f172a", whiteSpace: "nowrap" }}>
                    {shownNameOf(versions, key, proposals)}
                  </Box>
                  <Box component="span" sx={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {messageOf(version).split("\n")[0]}
                  </Box>
                </Box>
                {whole && <VersionMessage version={version} repository={repository} />}
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
}
