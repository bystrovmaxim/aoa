// src/lib/versionNames.ts
/**
 * Names on the track (spec 037, FR-017 – FR-019, research R10).
 *
 * A release is a version carrying a tag that has a release; it is named by that tag. A version after
 * a release is ``<release> · #<pr>``; one before any release is ``#<pr>``, or its short commit when it
 * had no pull request; Live is ``Live``. Tags without a release are flags. A version is named in the
 * address and in a room by the first 12 hex characters of its commit.
 */

import type { HistoryVersion } from "@/api/history";

/** How many hex characters name a version in an address and a room. */
export const SHORT_SHA = 12;

/** The id of ``version`` in an address and a room. */
export function shortSha(version: HistoryVersion): string {
  return version.sha.slice(0, SHORT_SHA);
}

/** The tag of the release ``version`` carries, or ``null``. */
export function releaseOf(version: HistoryVersion): string | null {
  return version.tags.find((tag) => tag.release !== null)?.name ?? null;
}

/** The tags of ``version`` that are not releases: its flags. */
export function flagsOf(version: HistoryVersion): string[] {
  return version.tags.filter((tag) => tag.release === null).map((tag) => tag.name);
}

/** The name of each version, in the list's order (oldest first). */
export function versionNames(versions: readonly HistoryVersion[]): string[] {
  let release: string | null = null;
  return versions.map((version) => {
    const own = releaseOf(version);
    if (own) {
      release = own;
      return own;
    }
    const pr = version.pr ? `#${version.pr.number}` : version.sha.slice(0, 7);
    return release ? `${release} · ${pr}` : pr;
  });
}

/** The name of the version a short sha or ``live`` names, or ``null`` when the list has none. */
export function nameOf(versions: readonly HistoryVersion[], b: string | null): string | null {
  if (b === "live") return "Live";
  if (!b) return null;
  const index = versions.findIndex((version) => version.sha.startsWith(b));
  return index < 0 ? null : versionNames(versions)[index];
}

/** A point's tooltip: pull request, date, size, tags, and the refusal reason. */
export function tooltipOf(version: HistoryVersion): string {
  const lines = [
    version.pr ? `#${version.pr.number} ${version.pr.title}` : (version.message ?? "").split("\n")[0],
    version.date.slice(0, 10),
    `${version.nodes} nodes · ${version.edges} edges`,
  ];
  if (version.tags.length) lines.push(version.tags.map((tag) => tag.name).join(", "));
  if (version.refused) lines.push(`refused: ${version.refused}`);
  return lines.filter(Boolean).join("\n");
}

/** The version a history opens on (FR-021): Live, else the newest unrefused one, else the newest; ``null`` in M7. */
export function defaultVersion(versions: readonly HistoryVersion[], live: string | null): string | null {
  if (live) return "live";
  const usable = versions.filter((version) => !version.refused);
  const newest = (usable.length ? usable : versions).at(-1);
  return newest ? shortSha(newest) : null;
}
