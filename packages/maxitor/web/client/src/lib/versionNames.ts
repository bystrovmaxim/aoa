// src/lib/versionNames.ts
/**
 * Names on the track (spec 037, FR-017, FR-018, FR-033, research R10).
 *
 * A version is named from what every history has: its pull request's number (``#147``), or, with no pull
 * request, its place in the history, the oldest being 1 (``#57``) — never its commit's hash. Its version
 * number is the last version-number tag at or before it (``v0.11.0`` → ``0.11.0``), where there is one; the
 * version button and the chosen point's chip write it before the name (``0.11.0 · #147``). A flag marks a
 * release: a tag published as a GitHub Release, or a tag named ``release…``; any other tag is only in the
 * point's card. In the address and in a room a version is the first 12 hex characters of its commit.
 */

import type { HistoryVersion } from "@/api/history";

/** How many hex characters name a version in an address and a room. */
export const SHORT_SHA = 12;

/** The id of ``version`` in an address and a room. */
export function shortSha(version: HistoryVersion): string {
  return version.sha.slice(0, SHORT_SHA);
}

/** A release's name: its tag without the ``v`` before a number (``v0.11.0`` → ``0.11.0``). */
export function releaseName(tag: string): string {
  return /^v\d/.test(tag) ? tag.slice(1) : tag;
}

/** A tag that is a version number: ``v0.8.0``, ``0.8.0``, ``v2.1``. */
const VERSION_TAG = /^v?\d+\.\d+(\.\d+)?([-+.][\w.]+)?$/;

/** A tag that marks a release by its name, in a repository with no host to publish releases: ``release``, ``release-1.4``, ``release/2026-10-30``. */
const RELEASE_TAG = /^release($|[-_/.])/i;

type Tag = HistoryVersion["tags"][number];

/** Whether ``tag`` marks a release: published as a release on its host (a GitHub Release), or named ``release…``. */
function marksRelease(tag: Tag): boolean {
  return tag.release !== null || RELEASE_TAG.test(tag.name);
}

/** The version-number tag ``version`` carries (``v0.8.0``), or ``null``: it names the point under the track. */
export function releaseOf(version: HistoryVersion): string | null {
  return version.tags.find((tag) => VERSION_TAG.test(tag.name))?.name ?? null;
}

/** The tags of ``version`` that make it a release, each a flag above its point; any other tag is only in its card. */
export function flagsOf(version: HistoryVersion): string[] {
  return version.tags.filter(marksRelease).map((tag) => tag.name);
}

/** The release ``version`` became, for its card: the GitHub Release's title and link, or a ``release…`` tag's name; ``null`` when it is none. */
export function releaseNoteOf(version: HistoryVersion): { title: string; url: string } | null {
  const tag = version.tags.find(marksRelease);
  if (!tag) return null;
  return tag.release ? { title: tag.release.title || tag.name, url: tag.release.url } : { title: tag.name, url: "" };
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

/**
 * How the version button and the chosen point's chip write the version a short sha or ``live`` names: its version
 * number and its name (``0.11.0 · #147``) where the history has a number, its name alone otherwise (``#147``), an
 * open pull request by its number; ``null`` when none of them has it.
 */
export function shownNameOf(versions: readonly HistoryVersion[], b: string | null, proposals: readonly HistoryVersion[] = []): string | null {
  if (b === "live") return "Live";
  if (!b) return null;
  const index = versions.findIndex((version) => version.sha.startsWith(b));
  if (index >= 0) {
    const number = numbersOf(versions)[index];
    const name = versionNames(versions)[index];
    return number ? `${number} · ${name}` : name;
  }
  const proposal = proposals.find((each) => each.sha.startsWith(b));
  return proposal?.pr ? `#${proposal.pr.number}` : null;
}

/** The name of the version a short sha or ``live`` names, or ``null`` when the list has none. */
export function nameOf(versions: readonly HistoryVersion[], b: string | null): string | null {
  if (b === "live") return "Live";
  if (!b) return null;
  const index = versions.findIndex((version) => version.sha.startsWith(b));
  return index < 0 ? null : versionNames(versions)[index];
}

/** The short name a phone's version button writes (spec 038, FR-033): the name alone, never the version number — ``#147``, ``Live``, an open pull request's ``#160``; ``—`` when the list has none. */
export function shortNameOf(versions: readonly HistoryVersion[], key: string | null, proposals: readonly HistoryVersion[] = []): string {
  return nameOf(versions, key) ?? shownNameOf(versions, key, proposals) ?? "—";
}

/** The version a history opens on (FR-021): Live, else the newest unrefused one, else the newest; ``null`` in M7. */
export function defaultVersion(versions: readonly HistoryVersion[], live: string | null): string | null {
  if (live) return "live";
  const usable = versions.filter((version) => !version.refused);
  const newest = (usable.length ? usable : versions).at(-1);
  return newest ? shortSha(newest) : null;
}
