// src/lib/historyKey.test.ts
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { adoptKeyFromLocation, keyFor } from "./historyKey";
import { pushRecent } from "./serviceUrlHistory";
import { roomLink, setUrlHistory, syncUrlToState } from "./urlState";

const NAME = "https://repo-graph-port.aoa.run/api/v1/history/orders";

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

afterEach(() => {
  setUrlHistory(null);
  window.history.replaceState(null, "", "/");
});

describe("a key that arrives in a link", () => {
  it("is kept for the tab and stays in the address bar, so the address is the link to share (FR-010a)", () => {
    window.history.replaceState(null, "", `/?history=${encodeURIComponent(NAME)}&b=abc#key=the-secret-key`);
    adoptKeyFromLocation();
    expect(keyFor(NAME)).toBe("the-secret-key");
    expect(window.location.hash).toBe("#key=the-secret-key");
  });

  it("stays in the address as the version changes", () => {
    window.history.replaceState(null, "", `/?history=${encodeURIComponent(NAME)}&b=abc#key=the-secret-key`);
    adoptKeyFromLocation();
    setUrlHistory({ name: NAME, b: "def" });
    syncUrlToState(null, null);
    expect(window.location.search).toContain("b=def");
    expect(window.location.hash).toBe("#key=the-secret-key");
  });

  it("is found in Recent when the tab holds none", () => {
    pushRecent({ address: `${NAME}#key=from-recent`, kind: "history", name: "orders", versions: 3 });
    expect(keyFor(NAME)).toBe("from-recent");
    expect(keyFor(`${NAME}-other`)).toBe("");
  });

  it("travels in a room's link", () => {
    window.history.replaceState(null, "", `/?history=${encodeURIComponent(NAME)}&b=abc#key=tab-key`);
    adoptKeyFromLocation();
    const link = roomLink(window.location.href, "room-1");
    expect(link).toContain("room=room-1");
    expect(link.endsWith("#key=tab-key")).toBe(true);
  });
});
