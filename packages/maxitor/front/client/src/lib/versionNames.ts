// src/lib/versionNames.ts
/**
 * Names on the track (spec 037, FR-017 – FR-019, research R10).
 *
 * A release is a version carrying a tag that has a release on its host, or a tag that is a version
 * number (``v0.8.0``, ``0.8.0``) — a local repository has tags but no releases; it is named by that tag without its
 * leading ``v`` (``0.11.0``). A version after a release is ``<release> · #<pr>``; one before any release
 * is ``#<pr>``. A version with no pull request — a direct commit — is named by its place in the history,
 * the oldest version being 1 (``0.8.0 · #57``, or ``#57`` before any release): a number that is easy to
 * say aloud and never changes as newer versions come. A commit's hash means nothing to a reader and is
 * never a name. Live is ``Live``. Every tag is a flag above its point, a release's tag included. A version
 * is still named in the address and in a room by the first 12 hex characters of its commit.
 */

import type { HistoryVersion } from "@/api/history";

/** How many hex characters name a version in an address and a room. */
export const SHORT_SHA = 12;

/** The id of ``version`` in an address and a room. */
export function shortSha(version: HistoryVersion): string {
  return version.sha.slice(0, SHORT_SHA);
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** A release's name: its tag without the ``v`` before a number (``v0.11.0`` → ``0.11.0``). */
export function releaseName(tag: string): string {
  return /^v\d/.test(tag) ? tag.slice(1) : tag;
}

/** The day of an ISO ``date`` in the reader's own time, as a track names it: ``Oct 22``. */
export function dayLabel(date: string): string {
  const at = new Date(date);
  return `${MONTHS[at.getMonth()]} ${at.getDate()}`;
}

/** The month of an ISO ``date`` in the reader's own time: ``Oct``, or ``Oct 2026`` when a track spans years. */
export function monthLabel(date: string, withYear: boolean): string {
  const at = new Date(date);
  return withYear ? `${MONTHS[at.getMonth()]} ${at.getFullYear()}` : MONTHS[at.getMonth()];
}

/** A tag that is a version number: ``v0.8.0``, ``0.8.0``, ``v2.1``. */
const VERSION_TAG = /^v?\d+\.\d+(\.\d+)?([-+.][\w.]+)?$/;

/** Whether ``tag`` makes a release: a release on its host, or a version number. */
function isRelease(tag: HistoryVersion["tags"][number]): boolean {
  return tag.release !== null || VERSION_TAG.test(tag.name);
}

/** The tag of the release ``version`` carries, or ``null``. */
export function releaseOf(version: HistoryVersion): string | null {
  return version.tags.find(isRelease)?.name ?? null;
}

/** The tags of ``version``, each a small flag above its point — a release's tag too, as the mockup draws it. */
export function flagsOf(version: HistoryVersion): string[] {
  return version.tags.map((tag) => tag.name);
}

/**
 * The name of each version, in the list's order (oldest first), from what every history has: its pull request's
 * number (``#147``), or, without one, its place in the history, the oldest being 1 (``#57``). A version number is
 * not in every history, so it is never part of a name; ``numbersOf`` gives it where there is one.
 */
export function versionNames(versions: readonly HistoryVersion[]): string[] {
  return versions.map((version, index) => `#${version.pr ? version.pr.number : index + 1}`);
}

/** Each version's version number — its own release, or the last one before it — or ``null`` where there is none. */
export function numbersOf(versions: readonly HistoryVersion[]): (string | null)[] {
  let release: string | null = null;
  return versions.map((version) => {
    const own = releaseOf(version);
    if (own) release = releaseName(own);
    return release;
  });
}

/** The name of the version a short sha or ``live`` names, or ``null`` when the list has none. */
export function nameOf(versions: readonly HistoryVersion[], b: string | null): string | null {
  if (b === "live") return "Live";
  if (!b) return null;
  const index = versions.findIndex((version) => version.sha.startsWith(b));
  return index < 0 ? null : versionNames(versions)[index];
}

/** What a point's tooltip says, as the mockup lays it out. */
export type VersionTip = { commit: string; kind: string; when: string; title: string; size: string; refused: string | null };

/** A pull request as the mockup's tooltip writes it: ``<repo>#<number>``, or ``#<number>`` without an address. */
function pullRequestRef(pr: NonNullable<HistoryVersion["pr"]>): string {
  const repo = /github\.com\/[^/]+\/([^/]+)\/pull\//.exec(pr.url)?.[1];
  return `${repo ?? ""}#${pr.number}`;
}

/** A point's tooltip: its commit and how it came, its date and tags, its title, its size and pull request. */
export function tipOf(version: HistoryVersion): VersionTip {
  const at = new Date(version.date);
  const tags = version.tags.map((tag) => tag.name);
  return {
    commit: version.sha.slice(0, 7),
    kind: version.pr ? "pull request" : "direct commit",
    when: [`${MONTHS[at.getMonth()]} ${at.getDate()}, ${at.getFullYear()}`, tags.length ? `tag ${tags.join(", ")}` : ""].filter(Boolean).join(" · "),
    title: version.pr ? version.pr.title : (version.message ?? "").split("\n")[0],
    size: [`${version.nodes} nodes`, `${version.edges} edges`, version.pr ? pullRequestRef(version.pr) : ""].filter(Boolean).join(" · "),
    refused: version.refused ?? null,
  };
}

/** The version a history opens on (FR-021): Live, else the newest unrefused one, else the newest; ``null`` in M7. */
export function defaultVersion(versions: readonly HistoryVersion[], live: string | null): string | null {
  if (live) return "live";
  const usable = versions.filter((version) => !version.refused);
  const newest = (usable.length ? usable : versions).at(-1);
  return newest ? shortSha(newest) : null;
}
