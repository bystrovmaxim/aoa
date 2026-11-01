// src/rooms/joinWaitsForHistory.test.ts
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const opened: { history?: unknown; ticket?: unknown }[] = [];
vi.mock("@/rooms/connection", async (original) => ({
  ...(await original<typeof import("@/rooms/connection")>()),
  RoomConnection: class {
    constructor(options: { history?: unknown; ticket?: unknown }) {
      opened.push(options);
    }
    open() {}
    close() {}
    send() {}
  },
}));

const { useRoomSession } = await import("@/rooms/useRoomSession");

const HISTORY = { name: "http://h/api/v1/history/erd", version: "live", versionA: null, key: "k" };

afterEach(() => {
  opened.length = 0;
  window.history.replaceState(null, "", "/");
});

describe("joining a room on a private history (spec 038)", () => {
  it("waits for the history to be read, then joins with its key's ticket — never as a room that ended", () => {
    window.history.replaceState(null, "", "/?history=x&room=r1");
    const session = renderHook(({ history }) => useRoomSession({ initialRoom: "r1", source: null, page: "view=domain-erd", onFallbackPage: () => undefined, onGraphChanged: () => undefined, surface: null, fingerprint: null, history }), {
      initialProps: { history: null as typeof HISTORY | null },
    });
    act(() => session.result.current.confirmName("Vera"));
    expect(opened).toHaveLength(0);
    session.rerender({ history: HISTORY });
    expect(opened).toHaveLength(1);
    expect(opened[0].ticket).toBeTypeOf("function");
  });

  it("joins at once on a page with no history", () => {
    window.history.replaceState(null, "", "/?room=r1");
    const session = renderHook(() => useRoomSession({ initialRoom: "r1", source: "http://s", page: "view=domain-erd", onFallbackPage: () => undefined, onGraphChanged: () => undefined, surface: null, fingerprint: null }));
    act(() => session.result.current.confirmName("Vera"));
    expect(opened).toHaveLength(1);
  });
});
