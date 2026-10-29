// src/lib/icons/entity_kind_glyphs.test.ts
import { describe, expect, it } from "vitest";
import { KIND_DISK_FILL, kindGlyphSvg, kindLegendDiskUri } from "@/lib/icons";

describe("kindGlyphSvg", () => {
  it.each(["core", "assoc", "detail", "spec", "enum", "state", "unknown"])("draws a pictogram for %s", (word) => {
    const svg = kindGlyphSvg(word, "#fff", 2.4);

    expect(svg).toMatch(/^<g/);
    expect(svg).not.toContain("<text");
  });

  it("draws a two-letter monogram for a word it does not know", () => {
    const svg = kindGlyphSvg("aggregate", "#fff", 2.4);

    expect(svg).toContain(">ag</text>");
  });

  it("escapes a monogram that is not plain text", () => {
    expect(kindGlyphSvg("<x", "#fff", 2.4)).toContain(">&lt;x</text>");
  });

  it("draws spec at 80 % with the same line weight", () => {
    const svg = kindGlyphSvg("spec", "#fff", 2.4);

    expect(svg).toContain("scale(0.8)");
    expect(svg).toContain('stroke-width="3.000"');
  });
});

describe("kindLegendDiskUri", () => {
  it("is a grey disk of a domain disk's size with a white glyph", () => {
    const svg = decodeURIComponent(kindLegendDiskUri("core"));

    expect(svg).toContain(`<circle cx="12" cy="12" r="11" fill="${KIND_DISK_FILL}"/>`);
    expect(svg).toContain('stroke="#ffffff"');
    expect(svg).toContain("scale(0.58)");
  });
});
