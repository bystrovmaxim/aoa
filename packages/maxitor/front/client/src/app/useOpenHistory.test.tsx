// src/app/useOpenHistory.test.tsx
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { HistoryVersion, OpenedHistory } from "@/api/history";
import { readUrlDeepLink, setUrlHistory, syncUrlToState } from "@/lib/urlState";
import { sourceOf, useOpenHistory } from "./useOpenHistory";

function version(n: number, extra: Partial<HistoryVersion> = {}): HistoryVersion {
  return { sha: `${n}`.padEnd(40, "d"), date: "2026-10-01T00:00:00Z", tags: [], nodes: 1, edges: 1, source: `version-${n}`, ...extra };
}
const id = (n: number) => `${n}`.padEnd(12, "d");
const LIVE = "https://live.example/graph-json";

function opened(versions: HistoryVersion[], live: string | null): OpenedHistory {
  return { name: "https://port/api/v1/history/h", title: "h", host: "github", repository: "o/r", live, versions, count: versions.length, room_ticket: "t" };
}

beforeEach(() => window.history.replaceState(null, "", "/"));
afterEach(() => setUrlHistory(null));

describe("the history a tab shows", () => {
  it("opens on Live, on the newest unrefused version, or on nothing in M7, and reads that version's source", () => {
    const { result } = renderHook(() => useOpenHistory(false));
    act(() => result.current.show(opened([version(1), version(2)], LIVE), "k", null));
    expect(result.current.mode).toBe("M4");
    expect(result.current.history?.b).toBe("live");
    expect(sourceOf(result.current.history!)).toBe(LIVE);
    act(() => result.current.show(opened([version(1), version(2, { refused: "bad" })], null), "k", null));
    expect(result.current.history?.b).toBe(id(1));
    expect(sourceOf(result.current.history!)).toBe("version-1");
    act(() => result.current.show(opened([], null), "k", null));
    expect(result.current.mode).toBe("M7");
    expect(result.current.history?.b).toBeNull();
  });

  it("falls back to the default version for a ``b`` the history does not have", () => {
    const { result } = renderHook(() => useOpenHistory(false));
    act(() => result.current.show(opened([version(1), version(2)], null), "k", "ffffffffffff"));
    expect(result.current.history?.b).toBe(id(2));
    act(() => result.current.show(opened([version(1), version(2)], null), "k", "live"));
    expect(result.current.history?.b).toBe(id(2));
  });

  it("reads no source for a refused version, which shows its reason instead", () => {
    const { result } = renderHook(() => useOpenHistory(false));
    act(() => result.current.show(opened([version(1), version(2, { refused: "bad" })], null), "k", id(2)));
    expect(result.current.history?.b).toBe(id(2));
    expect(sourceOf(result.current.history!)).toBeNull();
  });

  it("moves between modes as the list changes, keeping the version when it is still there", () => {
    const { result } = renderHook(() => useOpenHistory(false));
    act(() => result.current.show(opened([], null), "k", null));
    act(() => result.current.takeList([version(1)], null, "e1"));
    expect(result.current.mode).toBe("M3");
    act(() => result.current.takeList([version(1), version(2)], null, "e2"));
    expect(result.current.mode).toBe("M2");
    act(() => result.current.takeList([version(1), version(2)], LIVE, "e3"));
    expect(result.current.mode).toBe("M4");
    expect(result.current.history?.b).toBe(id(1));
    expect(result.current.notice).toBeNull();
  });

  it("moves off Live when Live goes, and off a version that disappears, saying why", () => {
    const { result } = renderHook(() => useOpenHistory(false));
    act(() => result.current.show(opened([version(1), version(2)], LIVE), "k", null));
    act(() => result.current.takeList([version(1), version(2)], null, "e"));
    expect(result.current.history?.b).toBe(id(2));
    expect(result.current.notice).toBe("Live is no longer part of this history");
    act(() => result.current.takeList([version(1)], null, "e2"));
    expect(result.current.history?.b).toBe(id(1));
    expect(result.current.notice).toContain("is no longer in the history");
  });
});

describe("the address of a history", () => {
  it("names the history and its version, never ``source`` or a key, and reads them back", () => {
    setUrlHistory({ name: "https://port/api/v1/history/h", b: id(1) });
    syncUrlToState("version-1", { kind: "interchange_graph" });
    expect(window.location.search).toContain("history=");
    expect(window.location.search).not.toContain("source=");
    expect(window.location.href).not.toContain("key");
    const link = readUrlDeepLink();
    expect([link.history, link.b, link.view]).toEqual(["https://port/api/v1/history/h", id(1), "full-graph"]);
  });

  it("carries no ``b`` in M7", () => {
    setUrlHistory({ name: "https://port/api/v1/history/h", b: null });
    syncUrlToState(null, null);
    expect(new URLSearchParams(window.location.search).has("b")).toBe(false);
  });

  it("shows the newest version as Live while Live runs exactly its graph", () => {
    const { result } = renderHook(() => useOpenHistory(false));
    act(() => result.current.show({ ...opened([version(1), version(2)], LIVE), live_same_as: version(2).sha }, "k", id(2)));
    expect(result.current.history?.b).toBe("live");
    act(() => result.current.pick(id(2)));
    expect(result.current.history?.b).toBe("live");
    act(() => result.current.pick(id(1)));
    expect(result.current.history?.b).toBe(id(1));
  });

  it("offers an open pull request like a version, reading its head's graph", () => {
    const open = { ...version(9, { source: "proposal-9", pr: { number: 158, title: "T", body: "", url: "", state: "open" as const } }) };
    const { result } = renderHook(() => useOpenHistory(false));
    act(() => result.current.show({ ...opened([version(1)], LIVE), proposals: [open] }, "k", id(9)));
    expect(result.current.history?.b).toBe(id(9));
    expect(sourceOf(result.current.history!)).toBe("proposal-9");
  });

  it("opens two versions from a link, a reversed pair swapped and the same version twice as one (spec 038, FR-014)", () => {
    const { result } = renderHook(() => useOpenHistory(false));
    const three = [version(1), version(2), version(3)];
    act(() => result.current.show(opened(three, LIVE), "k", id(1), id(3)));
    expect([result.current.history?.a, result.current.history?.b]).toEqual([id(1), id(3)]);
    act(() => result.current.show(opened(three, LIVE), "k", id(2), "live"));
    expect([result.current.history?.a, result.current.history?.b]).toEqual([id(2), "live"]);
    act(() => result.current.show(opened(three, LIVE), "k", id(2), id(2)));
    expect([result.current.history?.a, result.current.history?.b]).toEqual([null, id(2)]);
  });

  it("keeps the two apart, and moves an end that left the list toward the other", () => {
    const { result } = renderHook(() => useOpenHistory(false));
    act(() => result.current.show(opened([version(1), version(2), version(3)], null), "k", id(3)));
    act(() => result.current.pickRange({ a: id(1), b: id(3) }));
    expect(result.current.history?.a).toBe(id(1));
    act(() => result.current.takeList([version(2), version(3)], null, "e1"));
    expect([result.current.history?.a, result.current.history?.b]).toEqual([id(2), id(3)]);
    expect(result.current.notice).toBe("A version of the comparison is no longer in the history");
    act(() => result.current.takeList([version(3)], null, "e2"));
    expect([result.current.history?.a, result.current.history?.b]).toEqual([null, id(3)]);
    act(() => result.current.pickRange({ a: id(3), b: id(3) }));
    expect(result.current.history?.a).toBeNull();
  });

  it("writes mode, a and b into the address and reads them back", () => {
    setUrlHistory({ name: "https://port/api/v1/history/h", b: id(3), a: id(1) });
    syncUrlToState(null, null);
    const link = readUrlDeepLink();
    expect(window.location.search).toContain("mode=diff");
    expect([link.a, link.b]).toEqual([id(1), id(3)]);
    setUrlHistory({ name: "https://port/api/v1/history/h", b: id(3), a: null });
    syncUrlToState(null, null);
    expect(window.location.search).not.toContain("mode=");
    expect(readUrlDeepLink().a).toBeNull();
  });
});
