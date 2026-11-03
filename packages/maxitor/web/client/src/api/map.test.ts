// src/api/map.test.ts
import { describe, expect, it } from "vitest";
import { comparesTwo, type MapOverview } from "./map";

/** An overview with nothing drawn but the count of changed links. */
function overview(links_changed?: number | null): MapOverview {
  return { state: "ready", types: [], type_colours: {}, chains: [], areas: [], bundles: [], shared: [], ...(links_changed === undefined ? {} : { links_changed }) } as MapOverview;
}

describe("a map overview of one version or of two", () => {
  it("is one version's when it counts no changed links, absent or null", () => {
    expect(comparesTwo(overview())).toBe(false);
    expect(comparesTwo(overview(null))).toBe(false);
  });

  it("is a comparison's when it counts them, zero included", () => {
    expect(comparesTwo(overview(0))).toBe(true);
    expect(comparesTwo(overview(4))).toBe(true);
  });
});
