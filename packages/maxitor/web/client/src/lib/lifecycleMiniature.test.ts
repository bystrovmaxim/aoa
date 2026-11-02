import { beforeEach, describe, expect, it, vi } from "vitest";

const loadLifecycle = vi.fn();
vi.mock("@/lib/lifecycleDiff", () => ({ loadLifecycle, loadLifecycleDiff: vi.fn(), lifecycleCounts: vi.fn(), unmarkedLifecycle: vi.fn() }));
vi.mock("@/lib/buildLifecycleFsmDotSource", () => ({ buildLifecycleFsmDotSource: () => "digraph {}" }));
vi.mock("@/components/diagrams/ErdViewer/hooks/useGraphviz", () => ({ loadGraphvizWasm: async () => ({ layout: () => '<svg width="900pt" height="90pt" viewBox="0 0 900 90"><title>x</title></svg>' }) }));

const { fittedSvg, forgetMiniatures, lifecycleMiniature } = await import("@/lib/lifecycleMiniature");

describe("lifecycleMiniature", () => {
  beforeEach(() => {
    forgetMiniatures();
    loadLifecycle.mockReset();
    loadLifecycle.mockResolvedValue({ states: [], transitions: [] });
  });

  it("reads a lifecycle once", async () => {
    await lifecycleMiniature("a");
    await lifecycleMiniature("a");
    expect(loadLifecycle).toHaveBeenCalledTimes(1);
  });

  it("reads each lifecycle on its own", async () => {
    await lifecycleMiniature("a");
    await lifecycleMiniature("b");
    expect(loadLifecycle).toHaveBeenCalledTimes(2);
  });

  it("does not keep a failed read", async () => {
    loadLifecycle.mockRejectedValueOnce(new Error("no"));
    await expect(lifecycleMiniature("a")).rejects.toThrow();
    await expect(lifecycleMiniature("a")).resolves.toContain("<svg");
  });

  it("leaves the size to the viewBox and no native tooltip", () => {
    expect(fittedSvg('<svg width="900pt" height="90pt" viewBox="0 0 900 90"><title>x</title></svg>')).toBe('<svg viewBox="0 0 900 90"></svg>');
  });
});
