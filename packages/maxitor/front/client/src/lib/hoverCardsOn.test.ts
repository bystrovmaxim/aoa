import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setHoverCardsOn, useHoverCardsOn } from "@/lib/hoverCardsOn";

describe("whether cards open", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    setHoverCardsOn(true);
    localStorage.clear();
  });

  it("is on at first", () => {
    expect(renderHook(() => useHoverCardsOn()).result.current).toBe(true);
  });

  it("follows a choice, and keeps it for the next visit", () => {
    const { result } = renderHook(() => useHoverCardsOn());
    act(() => setHoverCardsOn(false));
    expect(result.current).toBe(false);
    expect(localStorage.getItem("maxitor:hoverCards")).toBe("0");
  });

  it("works where storage is refused", () => {
    vi.stubGlobal("localStorage", {
      setItem: () => {
        throw new Error("refused");
      },
    });
    const { result } = renderHook(() => useHoverCardsOn());
    act(() => setHoverCardsOn(false));
    expect(result.current).toBe(false);
  });
});
