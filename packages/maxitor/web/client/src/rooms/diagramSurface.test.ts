// src/rooms/diagramSurface.test.ts
import { describe, expect, it } from "vitest";
import { registerDiagramSurface, surfaceOfHalf, type DiagramSurface } from "@/rooms/diagramSurface";

const surface = () => ({}) as DiagramSurface;

describe("a surface per half", () => {
  it("keeps each half's apart and takes away only its own", () => {
    const [a, b] = [surface(), surface()];
    const dropA = registerDiagramSurface(a, "a");
    const dropB = registerDiagramSurface(b, "b");
    expect(surfaceOfHalf("a")).toBe(a);
    expect(surfaceOfHalf("b")).toBe(b);
    dropA();
    expect(surfaceOfHalf("a")).toBeNull();
    expect(surfaceOfHalf("b")).toBe(b);
    dropB();
  });

  it("does not let an old surface's goodbye take a newer one", () => {
    const [old, fresh] = [surface(), surface()];
    const dropOld = registerDiagramSurface(old, "b");
    const dropFresh = registerDiagramSurface(fresh, "b");
    dropOld();
    expect(surfaceOfHalf("b")).toBe(fresh);
    dropFresh();
  });
});
