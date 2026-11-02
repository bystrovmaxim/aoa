// src/components/history/VersionTrack/thinLabels.ts
/**
 * Which names stay under the track (spec 037, FR-026): every point is named, as in the mockup, and names thin
 * out only where they would collide — the oldest's and Live's stay always, then releases newest first, then
 * the other points newest first, each only where it overlaps none kept before.
 */

/** A name that could stand under the track: where its point is, how wide it is drawn, and why it is there. */
export type LabelCandidate = { b: string; x: number; text: string; kept: boolean; release?: boolean };

/** How wide a name of ``text`` is drawn, in pixels, at the track's 10.5 px, with 4 px of air around it. */
export function labelWidth(text: string): number {
  return text.length * 5.9 + 4;
}

/** The ``b`` of every name that stays; ``candidates`` come in track order (oldest first). */
export function thinLabels(candidates: readonly LabelCandidate[]): Set<string> {
  const placed: { left: number; right: number }[] = [];
  const shown = new Set<string>();
  const place = (candidate: LabelCandidate) => {
    const half = labelWidth(candidate.text) / 2;
    placed.push({ left: candidate.x - half, right: candidate.x + half });
    shown.add(candidate.b);
  };
  const overlaps = (candidate: LabelCandidate) => {
    const half = labelWidth(candidate.text) / 2;
    return placed.some((other) => candidate.x - half < other.right && candidate.x + half > other.left);
  };
  for (const candidate of candidates) if (candidate.kept) place(candidate);
  for (const release of [true, false]) {
    for (const candidate of [...candidates].reverse()) {
      if (!candidate.kept && Boolean(candidate.release) === release && !overlaps(candidate)) place(candidate);
    }
  }
  return shown;
}
