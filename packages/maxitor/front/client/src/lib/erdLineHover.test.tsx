// src/lib/erdLineHover.test.tsx
import Box from "@mui/material/Box";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ERD_DIFF_COLOUR, ERD_FADED_COLOUR } from "@/lib/buildDotSource";
import { EDGE_HOVER_CLASS, erdLineHoverSx } from "@/lib/erdPostPass";

afterEach(cleanup);

/** One hovered line drawn in ``colour``, as Graphviz writes it, under the canvas's hover style. */
function hoveredLine(colour: string): SVGPathElement {
  const { container } = render(
    <Box sx={erdLineHoverSx}>
      <svg>
        <g className={`edge ${EDGE_HOVER_CLASS}`}>
          <path stroke={colour} d="M0 0" />
        </g>
      </svg>
    </Box>,
  );
  return container.querySelector("path")!;
}

/** ``#rrggbb`` as the browser reports a computed colour. */
function rgb(hex: string): string {
  const [r, g, b] = [1, 3, 5].map((at) => parseInt(hex.slice(at, at + 2), 16));
  return `rgb(${r}, ${g}, ${b})`;
}

describe("a hovered line (spec 038)", () => {
  it.each(Object.entries(ERD_DIFF_COLOUR))("keeps its colour when painted %s in Diff", (_change, colour) => {
    expect(getComputedStyle(hoveredLine(colour)).stroke).toBe(rgb(colour));
  });

  it("turns darker when grey, as it always has", () => {
    expect(getComputedStyle(hoveredLine(ERD_FADED_COLOUR)).stroke).toBe(rgb("#475569"));
  });
});
