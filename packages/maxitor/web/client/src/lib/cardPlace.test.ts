import { describe, expect, it } from "vitest";
import { cardBeside, lineBoxes, placeCard } from "@/lib/cardPlace";

const stage = { left: 100, top: 50, right: 1100, bottom: 850 };

describe("cardBeside", () => {
  it("stands on the right of the table, level with the row", () => {
    expect(cardBeside(stage, { left: 200, top: 100, right: 400, bottom: 300 }, { left: 200, top: 180, right: 400, bottom: 200 })).toEqual({ x: 308, y: 130 });
  });

  it("goes left where the right has no room", () => {
    expect(cardBeside(stage, { left: 800, top: 100, right: 1000, bottom: 300 }, { left: 800, top: 180, right: 1000, bottom: 200 }).x).toBe(392);
  });

  it("goes under a table too wide for either side", () => {
    const place = cardBeside(stage, { left: 110, top: 100, right: 1090, bottom: 300 }, { left: 200, top: 180, right: 400, bottom: 200 });
    expect(place).toEqual({ x: 100, y: 158 });
  });

  it("stays on the stage near its bottom", () => {
    expect(cardBeside(stage, { left: 200, top: 700, right: 400, bottom: 840 }, { left: 200, top: 820, right: 400, bottom: 840 }).y).toBe(560);
  });
});

describe("placeCard", () => {
  const size = { width: 300, height: 150 };
  const table = { left: 500, top: 300, right: 700, bottom: 500 };
  const level = { left: 500, top: 340, right: 700, bottom: 360 };
  const onRight = { left: 720, top: 300, right: 900, bottom: 400 };
  const onLeft = { left: 250, top: 300, right: 480, bottom: 400 };
  const under = { left: 500, top: 520, right: 700, bottom: 600 };

  it("stands on the right when nothing is in the way", () => {
    expect(placeCard(stage, size, { beside: table, level, avoid: [] })).toEqual({ x: 608, y: 290 });
  });

  it("goes round a related table on the right", () => {
    expect(placeCard(stage, size, { beside: table, level, avoid: [onRight] })).toEqual({ x: 92, y: 290 });
  });

  it("goes round an active line and its label as round a table", () => {
    const line = { left: 716, top: 330, right: 736, bottom: 350 };
    expect(placeCard(stage, size, { beside: table, level, avoid: [line] }).x).toBe(92);
  });

  it("goes under when both sides hold related tables", () => {
    expect(placeCard(stage, size, { beside: table, level, avoid: [onRight, onLeft] })).toEqual({ x: 400, y: 458 });
  });

  it("goes above when under is taken too", () => {
    expect(placeCard(stage, size, { beside: table, level, avoid: [onRight, onLeft, under] })).toEqual({ x: 400, y: 92 });
  });

  it("takes the side that covers least when none is free", () => {
    const avoid = [{ left: 720, top: 300, right: 1000, bottom: 500 }, { left: 490, top: 100, right: 800, bottom: 290 }, { left: 490, top: 510, right: 800, bottom: 700 }, { left: 470, top: 340, right: 495, bottom: 350 }];
    expect(placeCard(stage, size, { beside: table, level, avoid }).x).toBe(92);
  });

  it("stays whole on the stage when nothing fits", () => {
    const wide = { left: 100, top: 50, right: 1100, bottom: 850 };
    const place = placeCard(stage, { width: 300, height: 700 }, { beside: wide, level: wide, avoid: [] });
    expect(place.x).toBeGreaterThanOrEqual(8);
    expect(place.y).toBeLessThanOrEqual(92);
  });

  it("lifts a card that would run past the foot, keeping it beside the table", () => {
    const low = { left: 500, top: 700, right: 700, bottom: 840 };
    expect(placeCard(stage, size, { beside: low, level: { ...low, top: 820 }, avoid: [] })).toEqual({ x: 608, y: 642 });
  });
});

describe("lineBoxes", () => {
  const box = (left: number, width: number) => ({ left, top: 0, right: left + width, bottom: 10, width, height: 10 });

  it("samples a line on screen, with its shown labels", () => {
    const path = {
      getScreenCTM: () => ({ a: 1 }),
      getTotalLength: () => 72,
      getPointAtLength: (at: number) => ({ matrixTransform: () => ({ x: at, y: 100 }) }),
    };
    const labels = [{ getBoundingClientRect: () => box(5, 20) }, { getBoundingClientRect: () => box(5, 0) }];
    const edge = { querySelector: () => path, querySelectorAll: () => labels } as unknown as Element;
    const boxes = lineBoxes(edge);
    expect(boxes.map((each) => each.left)).toEqual([-10, 26, 62, 5]);
  });
});
