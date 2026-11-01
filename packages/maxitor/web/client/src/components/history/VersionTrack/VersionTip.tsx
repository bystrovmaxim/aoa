// src/components/history/VersionTrack/VersionTip.tsx
import Box from "@mui/material/Box";
import type { HistoryVersion, ProposalState } from "@/api/history";
import { releaseNoteOf } from "@/lib/versionNames";
import { DIRECT_LOOK, LIVE_LOOK, MERGED_LOOK, PROPOSAL_LOOK } from "./proposalLook";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MUTED = "#64748b";

/** When ``date`` was, as a reader says it: ``20 min ago``, ``3 days ago``; a date further back, or ahead, in full. */
export function whenOf(date: string, now: number = Date.now()): string {
  const at = new Date(date);
  const minutes = Math.round((now - at.getTime()) / 60_000);
  if (minutes >= 0 && minutes < 60) return `${Math.max(minutes, 1)} min ago`;
  if (minutes >= 0 && minutes < 24 * 60) return `${Math.round(minutes / 60)} h ago`;
  if (minutes >= 0 && minutes < 30 * 24 * 60) {
    const days = Math.round(minutes / (24 * 60));
    return `${days} day${days === 1 ? "" : "s"} ago`;
  }
  return `${MONTHS[at.getMonth()]} ${at.getDate()}, ${at.getFullYear()}`;
}

/** ``n`` of a graph's kind in words: ``2 entities``, ``1 entity field``, ``3 actions``. */
export function kindCount(kind: string, n: number): string {
  const words = kind.replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase();
  const plural = n === 1 ? words : words.endsWith("y") ? `${words.slice(0, -1)}ies` : `${words}s`;
  return `${n} ${plural}`;
}

/** What a version did to the graph, in words: ``+2 entities · +6 fields · −1 field · 3 changed · +4 links``. */
export function changeOf(change: HistoryVersion["change"]): string[] {
  if (!change) return [];
  return [
    ...Object.entries(change.added).map(([kind, n]) => `+${kindCount(kind, n)}`),
    ...Object.entries(change.removed).map(([kind, n]) => `−${kindCount(kind, n)}`),
    ...(change.changed ? [`${change.changed} changed`] : []),
    ...(change.links?.added ? [`+${change.links.added} link${change.links.added === 1 ? "" : "s"}`] : []),
    ...(change.links?.removed ? [`−${change.links.removed} link${change.links.removed === 1 ? "" : "s"}`] : []),
  ];
}

/** Two letters for a person with no picture: ``Anna Petrova`` → ``AP``. */
export function initialsOf(name: string): string {
  const words = name.trim().split(/[\s._-]+/).filter(Boolean);
  return ((words[0]?.[0] ?? "?") + (words.length > 1 ? words[words.length - 1][0] : "")).toUpperCase();
}

const TINTS = ["#e0e7ff", "#dcfce7", "#fef3c7", "#fce7f3", "#e0f2fe", "#ede9fe"];

/** A person's picture: their avatar where the host gives one, else their initials on a soft colour of their own. */
function Person({ name, avatar }: { name: string; avatar?: string }) {
  const tint = TINTS[[...name].reduce((sum, letter) => sum + letter.charCodeAt(0), 0) % TINTS.length];
  return (
    <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: "6px", minWidth: 0 }}>
      {avatar ? (
        <Box component="img" src={avatar} alt="" sx={{ width: 22, height: 22, borderRadius: "50%", flexShrink: 0 }} />
      ) : (
        <Box component="span" aria-hidden sx={{ width: 22, height: 22, borderRadius: "50%", bgcolor: tint, color: "#334155", fontSize: 10, fontWeight: 700, display: "inline-flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          {initialsOf(name)}
        </Box>
      )}
      <Box component="span" sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {name}
      </Box>
    </Box>
  );
}

/** A small pill: a merged pull request, a version number, a size. */
function Pill({ children, tone }: { children: React.ReactNode; tone: "live" | "merged" | "direct" | "release" | "plain" }) {
  const colours = {
    direct: { bgcolor: DIRECT_LOOK.tint, color: "#59636e" },
    live: { bgcolor: "#fff", color: "#59636e", boxShadow: `inset 0 0 0 1.2px ${LIVE_LOOK.colour}` },
    merged: { bgcolor: MERGED_LOOK.tint, color: MERGED_LOOK.colour },
    release: { bgcolor: "#0f172a", color: "#fff" },
    plain: { bgcolor: "#f1f5f9", color: "#475569" },
  }[tone];
  return (
    <Box component="span" sx={{ ...colours, display: "inline-flex", alignItems: "center", gap: "4px", height: 20, px: "8px", borderRadius: "10px", fontSize: 11.5, fontWeight: 500, whiteSpace: "nowrap", flexShrink: 0 }}>
      {children}
    </Box>
  );
}

/** The release flag, as the track draws it. */
export function FlagIcon() {
  return (
    <svg viewBox="0 0 12 14" width={10} height={12} aria-hidden>
      <path d="M2 13V1.5" stroke="currentColor" strokeWidth={1.3} />
      <path d="M2 1.5h7l-2 2.4 2 2.4H2z" fill="currentColor" />
    </svg>
  );
}

/** The git-commit mark: one commit on a line — a change pushed straight to the branch. */
function CommitIcon() {
  return (
    <svg viewBox="0 0 16 16" width={12} height={12} aria-hidden>
      <g fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round">
        <circle cx={8} cy={8} r={2.6} />
        <path d="M1.5 8h3.9M10.6 8h3.9" />
      </g>
    </svg>
  );
}

/** The git-merge mark: two branches joining. */
function MergeIcon() {
  return (
    <svg viewBox="0 0 16 16" width={12} height={12} aria-hidden>
      <g fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round">
        <circle cx={4.5} cy={3.5} r={1.6} />
        <circle cx={4.5} cy={12.5} r={1.6} />
        <circle cx={11.5} cy={9} r={1.6} />
        <path d="M4.5 5.1v5.8M4.5 5.6c0 2.4 2.2 3.4 5.4 3.4" />
      </g>
    </svg>
  );
}

export type VersionTipProps = {
  /** The version, or ``null`` for Live. */
  version: HistoryVersion | null;
  /** Its version number where the history has one — its own release or the one it follows — else ``null``. */
  release: string | null;
  /** The point is Live; with a ``version``, Live runs exactly that version's graph. */
  live?: boolean;
  /** A pull request still open: where it stands, instead of "Merged". */
  state?: ProposalState;
};

/**
 * A point's tooltip (spec 037, FR-019), laid out as a pull request card: "Merged" for a merged pull request, "Direct
 * push" for a change pushed straight to the branch, the state of one still open, its
 * version number as a dark chip where the history has one, who made it, its number and when; its title; who made
 * it and who merged it; its size in lines and files; what it did to the graph; and why it was refused, if it was.
 */
export function VersionTip({ version, release, live = false, state }: VersionTipProps) {
  if (!version) {
    return (
      <>
        <Box sx={{ fontWeight: 600, fontSize: 13, color: "#0f172a" }}>Live</Box>
        <Box sx={{ mt: "4px" }}>What the service runs now, not merged yet.</Box>
      </>
    );
  }
  const who = version.contribution;
  const title = version.pr ? version.pr.title : (version.message ?? "").split("\n")[0];
  const change = changeOf(version.change);
  const note = releaseNoteOf(version);
  // Tags that are neither the version number nor the release: named here only, never drawn on the track.
  const others = version.tags.map((tag) => tag.name).filter((name) => name !== note?.title && !/^v?\d+\.\d+/.test(name) && !/^release($|[-_/.])/i.test(name));
  return (
    <>
      <Box sx={{ display: "flex", alignItems: "center", gap: "6px", color: MUTED, fontSize: 12, minWidth: 0 }}>
        {live && <Pill tone="live">Live</Pill>}
        {state && (
          <Box component="span" sx={{ bgcolor: PROPOSAL_LOOK[state].tint, color: PROPOSAL_LOOK[state].colour, display: "inline-flex", alignItems: "center", gap: "4px", height: 20, px: "8px", borderRadius: "10px", fontSize: 11.5, fontWeight: 500, whiteSpace: "nowrap", flexShrink: 0 }}>
            {PROPOSAL_LOOK[state].name}
          </Box>
        )}
        {!version.pr && !state && (
          <Pill tone="direct">
            <CommitIcon />
            Direct push
          </Pill>
        )}
        {version.pr && !state && (
          <Pill tone="merged">
            <MergeIcon />
            Merged
          </Pill>
        )}
        {release && <Pill tone="release">{release}</Pill>}
        {version.pr && <span>#{version.pr.number}</span>}
        <Box component="span" sx={{ ml: "auto", whiteSpace: "nowrap" }}>
          {whenOf(version.date)}
        </Box>
      </Box>
      {note && (
        <Box sx={{ mt: "8px", display: "flex", alignItems: "center", gap: "6px", fontSize: 12, color: "#334155", minWidth: 0 }}>
          <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: "4px", height: 20, px: "8px", borderRadius: "10px", bgcolor: "#f1f5f9", color: "#334155", fontSize: 11.5, fontWeight: 600, flexShrink: 0 }}>
            <FlagIcon />
            Release
          </Box>
          <Box component="span" sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{note.title}</Box>
        </Box>
      )}
      {/* The title only, at most two lines: the whole description is under the track, for the chosen point. */}
      {title && (
        <Box sx={{ mt: "8px", fontSize: 13, fontWeight: 500, color: "#0f172a", lineHeight: 1.4, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {title}
        </Box>
      )}
      {others.length > 0 && <Box sx={{ mt: "4px", color: MUTED, fontSize: 11.5 }}>tags: {others.join(", ")}</Box>}
      {who && (
        <Box sx={{ mt: "8px", display: "flex", alignItems: "center", gap: "6px", color: MUTED, fontSize: 12, minWidth: 0 }}>
          <Person name={version.pr?.author || who.author} avatar={version.pr?.avatar} />
          {who.co_authors > 0 && <span>+{who.co_authors}</span>}
          {who.merged_by && who.merged_by !== who.author && (
            <>
              <span>→</span>
              <Person name={who.merged_by} />
            </>
          )}
        </Box>
      )}
      {(who || change.length > 0) && (
        <Box sx={{ mt: "6px", display: "flex", alignItems: "center", gap: "4px", flexWrap: "wrap", color: MUTED, fontSize: 11.5 }}>
          {who && (
            <>
              <Pill tone="plain">
                <Box component="span" sx={{ color: "#16a34a" }}>+{who.additions}</Box>
                <Box component="span" sx={{ color: "#dc2626" }}>−{who.deletions}</Box>
              </Pill>
              <Pill tone="plain">
                {who.files} file{who.files === 1 ? "" : "s"}
              </Pill>
            </>
          )}
          {change.length > 0 && <Box component="span" sx={{ ml: "4px" }}>{change.join(" · ")}</Box>}
        </Box>
      )}
      {version.refused && <Box sx={{ mt: "4px", color: "#dc2626", fontSize: 11.5 }}>refused: {version.refused}</Box>}
    </>
  );
}
