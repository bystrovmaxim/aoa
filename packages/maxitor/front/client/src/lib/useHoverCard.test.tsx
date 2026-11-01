import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setHoverCardsOn } from "@/lib/hoverCardsOn";
import { CARD_REST_MS, CARD_STAY_MS, useHoverCard } from "@/lib/useHoverCard";
import { putFocus, setFollowTarget } from "@/rooms/focusStore";

const a = { key: "a" };
const b = { key: "b" };

describe("useHoverCard", () => {
  beforeEach(() => void vi.useFakeTimers());
  afterEach(() => void vi.useRealTimers());
  const wait = (ms: number) => act(() => void vi.advanceTimersByTime(ms));

  it("opens only after the pointer has rested", () => {
    const { result } = renderHook(() => useHoverCard<{ key: string }>(false));
    act(() => result.current.want(a));
    wait(CARD_REST_MS - 1);
    expect(result.current.shown).toBeNull();
    wait(1);
    expect(result.current.shown).toBe(a);
  });

  it("opens nothing for an element merely crossed", () => {
    const { result } = renderHook(() => useHoverCard<{ key: string }>(false));
    act(() => result.current.want(a));
    wait(CARD_REST_MS / 2);
    act(() => result.current.want(b));
    wait(CARD_REST_MS / 2);
    act(() => result.current.want(null));
    wait(CARD_REST_MS * 2);
    expect(result.current.shown).toBeNull();
  });

  it("stays while the pointer reaches the card", () => {
    const { result } = renderHook(() => useHoverCard<{ key: string }>(false));
    act(() => result.current.wantNow(a));
    act(() => result.current.want(null));
    wait(CARD_STAY_MS - 1);
    act(() => result.current.hold());
    wait(CARD_STAY_MS * 3);
    expect(result.current.shown).toBe(a);
  });

  it("goes from one card to the next with no gap", () => {
    const { result } = renderHook(() => useHoverCard<{ key: string }>(false));
    act(() => result.current.wantNow(a));
    act(() => result.current.want(null));
    act(() => result.current.want(b));
    wait(CARD_REST_MS - 1);
    expect(result.current.shown).toBe(a);
    wait(1);
    expect(result.current.shown).toBe(b);
  });

  it("keeps the card when the pointer reaches it past another element", () => {
    const { result } = renderHook(() => useHoverCard<{ key: string }>(false));
    act(() => result.current.wantNow(a));
    act(() => result.current.want(b));
    act(() => result.current.hold());
    wait(CARD_REST_MS * 2);
    expect(result.current.shown).toBe(a);
  });

  it("ignores what the diagram reports while the pointer is on the card", () => {
    const { result } = renderHook(() => useHoverCard<{ key: string }>(false));
    act(() => result.current.wantNow(a));
    act(() => result.current.hold());
    act(() => result.current.want(null));
    act(() => result.current.want(b));
    wait(CARD_REST_MS * 2);
    expect(result.current.shown).toBe(a);
    act(() => result.current.release());
    wait(CARD_STAY_MS);
    expect(result.current.shown).toBeNull();
  });

  it("opens nothing with cards switched off, and closes what stands", () => {
    const { result } = renderHook(() => useHoverCard<{ key: string }>(false));
    act(() => result.current.wantNow(a));
    act(() => setHoverCardsOn(false));
    expect(result.current.shown).toBeNull();
    act(() => result.current.want(b));
    act(() => result.current.wantNow(b));
    wait(CARD_REST_MS);
    expect(result.current.shown).toBeNull();
    act(() => setHoverCardsOn(true));
    act(() => result.current.want(b));
    wait(CARD_REST_MS);
    expect(result.current.shown).toBe(b);
  });

  it("shows a followed person's cards with its own switched off", () => {
    putFocus("anna", { page: "p", hover: null, tooltip: null, selection: null, panels: { sidebar: [], filter: null, legend: false, versions: false, track: null, changes: null, why: null } });
    setFollowTarget("anna");
    const { result } = renderHook(() => useHoverCard<{ key: string }>(false));
    act(() => setHoverCardsOn(false));
    act(() => result.current.wantNow(a));
    expect(result.current.shown).toBe(a);
    act(() => setFollowTarget(null));
    act(() => setHoverCardsOn(true));
  });

  it("closes once the pointer has left", () => {
    const { result } = renderHook(() => useHoverCard<{ key: string }>(false));
    act(() => result.current.wantNow(a));
    act(() => result.current.want(null));
    wait(CARD_STAY_MS);
    expect(result.current.shown).toBeNull();
  });

  it("opens nothing while another card stands, and closes its own", () => {
    const { result, rerender } = renderHook(({ paused }) => useHoverCard<{ key: string }>(paused), { initialProps: { paused: false } });
    act(() => result.current.wantNow(a));
    rerender({ paused: true });
    expect(result.current.shown).toBeNull();
    act(() => result.current.want(b));
    wait(CARD_REST_MS);
    expect(result.current.shown).toBeNull();
  });
});
