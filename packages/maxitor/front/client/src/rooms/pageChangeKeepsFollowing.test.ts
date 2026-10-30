// src/rooms/pageChangeKeepsFollowing.test.ts
import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { clearFocus, focusToSend, followedParticipant, mirroredFocus, putFocus, reportHover, setFollowTarget } from "@/rooms/focusStore";

vi.mock("@/rooms/connection", async (original) => ({
  ...(await original<typeof import("@/rooms/connection")>()),
  RoomConnection: class {
    open() {}
    close() {}
    send() {}
  },
}));

const { useRoomSession } = await import("@/rooms/useRoomSession");

afterEach(() => clearFocus());

describe("a page a follower is led to (spec 038)", () => {
  it("keeps whom it follows and what they look at; only its own hover goes", () => {
    const session = renderHook(({ page }) => useRoomSession({ initialRoom: null, source: "http://s", page, onFallbackPage: () => undefined, onGraphChanged: () => undefined, surface: null, fingerprint: null }), {
      initialProps: { page: "view=domain-erd" },
    });
    setFollowTarget("anna");
    putFocus("anna", { page: "view=use-case", hover: null, tooltip: null, selection: null, panels: { sidebar: ["domains"], filter: "changes", legend: false, versions: false, track: null } });
    reportHover({ kind: "table", id: "Orders" });
    session.rerender({ page: "view=use-case" });
    expect(followedParticipant()).toBe("anna");
    expect(mirroredFocus()?.panels.filter).toBe("changes");
    setFollowTarget(null);
    expect(focusToSend("view=use-case").hover).toBeNull();
  });
});
