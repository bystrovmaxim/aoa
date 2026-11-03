// src/components/history/VersionTrack/thinLabels.test.ts
import { describe, expect, it } from "vitest";
import { labelWidth, thinLabels, type LabelCandidate } from "./thinLabels";

describe("names under the track (FR-026)", () => {
  it("keeps the kept names, then releases newest first where they overlap none", () => {
    const candidates: LabelCandidate[] = [
      { b: "a", x: 20, text: "v0.1.0", kept: true },
      { b: "b", x: 40, text: "v0.2.0", kept: false },
      { b: "c", x: 90, text: "v0.3.0", kept: false },
      { b: "d", x: 110, text: "v0.4.0", kept: false },
      { b: "e", x: 200, text: "Live", kept: true },
    ];
    expect([...thinLabels(candidates)].sort()).toEqual(["a", "d", "e"]);
  });

  it("never lets two names overlap, however dense the releases", () => {
    const candidates = Array.from({ length: 500 }, (_, i): LabelCandidate => ({ b: `${i}`, x: 18 + i * 24, text: `v${i}.0.0`, kept: i === 0 || i === 499 }));
    const shown = candidates.filter((candidate) => thinLabels(candidates).has(candidate.b)).sort((a, b) => a.x - b.x);
    for (let i = 1; i < shown.length; i += 1) {
      expect(shown[i].x - labelWidth(shown[i].text) / 2).toBeGreaterThanOrEqual(shown[i - 1].x + labelWidth(shown[i - 1].text) / 2);
    }
    expect(thinLabels(candidates).has("0") && thinLabels(candidates).has("499")).toBe(true);
  });
});
