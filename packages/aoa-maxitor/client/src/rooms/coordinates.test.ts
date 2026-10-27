// src/rooms/coordinates.test.ts
import { describe, expect, it } from "vitest";
import { g6ClientToDiagram, g6DiagramToClient, svgClientToDiagram, svgDiagramToClient, viewportOf } from "@/rooms/coordinates";
import { place } from "@/rooms/PointerLayer";

/** An SVG whose screen transform is ``scale`` then a shift, as a pan and zoom make it. */
function svgAt(scale: number, e: number, f: number) {
  return { getScreenCTM: () => ({ a: scale, b: 0, c: 0, d: scale, e, f }) as DOMMatrixReadOnly };
}

describe("SVG diagram coordinates", () => {
  it("map a diagram point to the screen and back at any zoom", () => {
    for (const svg of [svgAt(1, 0, 0), svgAt(0.25, 300, -40), svgAt(2.5, -1200, 80)]) {
      const point = { x: 165.5, y: 52.25 };
      const client = svgDiagramToClient(svg, point)!;
      const back = svgClientToDiagram(svg, client)!;
      expect(back.x).toBeCloseTo(point.x, 9);
      expect(back.y).toBeCloseTo(point.y, 9);
    }
  });

  it("put one diagram point at each screen's own place: the point travels, not the pixels", () => {
    const anna = svgAt(1, 255, 38);
    const boris = svgAt(2.6, -400, 44);
    const sent = svgClientToDiagram(anna, { x: 420, y: 90 })!;
    expect(sent).toEqual({ x: 165, y: 52 });
    expect(svgDiagramToClient(boris, sent)).toEqual({ x: 165 * 2.6 - 400, y: 52 * 2.6 + 44 });
  });

  it("know nothing before the SVG is laid out", () => {
    const none = { getScreenCTM: () => null };
    expect(svgClientToDiagram(none, { x: 1, y: 1 })).toBeNull();
    expect(svgDiagramToClient(none, { x: 1, y: 1 })).toBeNull();
  });
});

describe("G6 diagram coordinates", () => {
  it("use the graph's own canvas maps", () => {
    const graph = {
      getCanvasByClient: ([x, y]: [number, number]) => [(x - 10) / 2, (y - 20) / 2],
      getClientByCanvas: ([x, y]: [number, number]) => [x * 2 + 10, y * 2 + 20],
    };
    expect(g6ClientToDiagram(graph, { x: 110, y: 220 })).toEqual({ x: 50, y: 100 });
    expect(g6DiagramToClient(graph, { x: 50, y: 100 })).toEqual({ x: 110, y: 220 });
  });
});

describe("the viewport message", () => {
  it("is the centre and size of the visible part of the diagram", () => {
    const svg = svgAt(2, 100, 50);
    const rect = { left: 100, top: 50, right: 500, bottom: 350 } as DOMRectReadOnly;
    expect(viewportOf(rect, (c) => svgClientToDiagram(svg, c))).toEqual({ cx: 100, cy: 75, w: 200, h: 150 });
  });
});

describe("a pointer outside the view", () => {
  it("is an arrow at the edge, pointing towards it", () => {
    expect(place(50, 60, 400, 300)).toEqual({ kind: "inside", x: 50, y: 60 });
    const right = place(900, 150, 400, 300);
    expect(right).toMatchObject({ kind: "edge", x: 380, y: 150, angle: 0 });
    const above = place(200, -500, 400, 300);
    expect(above).toMatchObject({ kind: "edge", x: 200, y: 20, angle: -90 });
  });
});
