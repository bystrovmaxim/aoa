// src/components/diagrams/ErdViewer/hooks/useSvgPanZoom.test.tsx
import { act, cleanup, render } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useSvgPanZoom } from "./useSvgPanZoom";

/** A viewport and its panner, bound the way every Graphviz viewer binds them. */
function Viewer() {
  const { viewportRef, pannerRef, bindInteractions } = useSvgPanZoom();
  useEffect(() => bindInteractions(), [bindInteractions]);
  return (
    <div ref={viewportRef} data-testid="viewport">
      <div ref={pannerRef} data-testid="panner" />
    </div>
  );
}

/** The panner's transform as numbers: scale, tx, ty. */
function transformOf(panner: HTMLElement): { scale: number; tx: number; ty: number } {
  const [scale, , , , tx, ty] = /matrix\(([^)]+)\)/.exec(panner.style.transform)![1]!.split(",").map(Number);
  return { scale: scale!, tx: tx!, ty: ty! };
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("the wheel over a Graphviz diagram (spec 029, FR-053)", () => {
  it("moves the picture on a two-finger swipe and keeps its zoom", () => {
    const { getByTestId } = render(<Viewer />);
    const wheel = new WheelEvent("wheel", { deltaX: 30, deltaY: 50, cancelable: true });
    act(() => {
      getByTestId("viewport").dispatchEvent(wheel);
    });
    expect(transformOf(getByTestId("panner"))).toEqual({ scale: 1, tx: -30, ty: -50 });
    expect(wheel.defaultPrevented).toBe(true);
  });

  it("zooms on a pinch (the browser reports it as a wheel with ctrlKey)", () => {
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "setTimeout"] });
    const { getByTestId } = render(<Viewer />);
    act(() => {
      getByTestId("viewport").dispatchEvent(new WheelEvent("wheel", { deltaY: -40, ctrlKey: true, cancelable: true }));
      vi.advanceTimersByTime(100);
    });
    expect(transformOf(getByTestId("panner")).scale).toBeGreaterThan(1);
  });
});
