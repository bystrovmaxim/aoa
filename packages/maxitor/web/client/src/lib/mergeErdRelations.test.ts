// src/lib/mergeErdRelations.test.ts
import { describe, expect, it } from "vitest";
import type { ErdRelation } from "@/lib/buildDotSource";
import { mergeRelationsOnScreen } from "@/lib/mergeErdRelations";

const rel = (source: string, target: string, relationship_kind = "association", label = "f"): ErdRelation => ({
  source,
  target,
  label,
  relationship_kind,
});

describe("mergeRelationsOnScreen", () => {
  it("draws a line whose ends came from two different slices", () => {
    // OfferCore came with the Players slice, IndustryEnum with the Showcases slice: no slice holds the line.
    const sliceRelations = [rel("Player", "OfferCore"), rel("Showcase", "IndustryEnum")];
    const requestRelations = [...sliceRelations, rel("OfferCore", "IndustryEnum", "association", "industries")];
    const onScreen = new Set(["Player", "OfferCore", "Showcase", "IndustryEnum"]);

    const lines = mergeRelationsOnScreen(requestRelations, sliceRelations, onScreen);

    expect(lines).toContainEqual(rel("OfferCore", "IndustryEnum", "association", "industries"));
  });

  it("drops a line with an end off screen", () => {
    const lines = mergeRelationsOnScreen([rel("A", "B"), rel("A", "Hidden")], [], new Set(["A", "B"]));

    expect(lines).toEqual([rel("A", "B")]);
  });

  it("keeps the slices' container links, which point at a container, not a table", () => {
    const container = rel("Head", "Head:kind", "specialization", "by kind");
    const lines = mergeRelationsOnScreen([], [container], new Set(["Head"]));

    expect(lines).toEqual([container]);
  });

  it("falls back to the slices' lines when the server sends no request-wide list", () => {
    const lines = mergeRelationsOnScreen(undefined, [rel("A", "B"), rel("A", "B")], new Set(["A", "B"]));

    expect(lines).toEqual([rel("A", "B")]);
  });
});
