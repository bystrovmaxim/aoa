// src/lib/useSvgLayoutHash.test.ts
import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { svgLayoutHash } from "@/lib/layoutHash";
import { useSvgLayoutPair } from "@/lib/useSvgLayoutHash";

describe("a picture's layout hash and its input's digest (spec 038)", () => {
  it("come as one pair, the digest of the input the picture was laid out from", async () => {
    const view = renderHook(({ svg, input }) => useSvgLayoutPair(svg, input), { initialProps: { svg: "<svg>A</svg>", input: "dot\nA" } });
    expect(view.result.current).toBeUndefined();
    await waitFor(() => expect(view.result.current).toBeDefined());
    expect(view.result.current).toEqual({ hash: await svgLayoutHash("<svg>A</svg>"), digest: await svgLayoutHash("dot\nA") });
  });

  it("keep the picture's own input while a new input is still being drawn — never the new digest on the old picture", async () => {
    const view = renderHook(({ svg, input }) => useSvgLayoutPair(svg, input), { initialProps: { svg: "<svg>A</svg>", input: "dot\nA" } });
    await waitFor(() => expect(view.result.current).toBeDefined());
    const seen: unknown[] = [];
    // New filters: the input changes at once, the picture only once Graphviz has drawn it.
    view.rerender({ svg: "<svg>A</svg>", input: "dot\nB" });
    // Time for any hashing of that moment to land.
    await act(() => new Promise((resolve) => setTimeout(resolve, 50)));
    seen.push(view.result.current);
    view.rerender({ svg: "", input: "dot\nB" });
    seen.push(view.result.current);
    view.rerender({ svg: "<svg>B</svg>", input: "dot\nB" });
    seen.push(view.result.current);
    await waitFor(async () => expect(view.result.current).toEqual({ hash: await svgLayoutHash("<svg>B</svg>"), digest: await svgLayoutHash("dot\nB") }));
    const [hashA, digestA] = [await svgLayoutHash("<svg>A</svg>"), await svgLayoutHash("dot\nA")];
    expect(seen).toEqual([{ hash: hashA, digest: digestA }, undefined, undefined]);
  });
});
