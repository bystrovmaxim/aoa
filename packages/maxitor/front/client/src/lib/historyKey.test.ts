// src/lib/historyKey.test.ts
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { adoptKeyFromLocation, keyFor } from "./historyKey";
import { pushRecent } from "./serviceUrlHistory";
import { roomLink } from "./urlState";

const NAME = "https://repo-graph-port.aoa.run/api/v1/history/orders";

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("a key that arrives in a link", () => {
  it("moves to the tab and leaves the address bar without a new history entry", () => {
    window.history.replaceState(null, "", `/?history=${encodeURIComponent(NAME)}&b=abc#key=the-secret-key`);
    const entries = window.history.length;
    adoptKeyFromLocation();
    expect(window.location.href).not.toContain("the-secret-key");
    expect(window.location.hash).toBe("");
    expect(window.location.search).toContain("history=");
    expect(window.history.length).toBe(entries);
    expect(keyFor(NAME)).toBe("the-secret-key");
  });

  it("is found in Recent when the tab holds none", () => {
    pushRecent({ address: `${NAME}#key=from-recent`, kind: "history", name: "orders", versions: 3 });
    expect(keyFor(NAME)).toBe("from-recent");
    expect(keyFor(`${NAME}-other`)).toBe("");
  });

  it("travels in a room's link, whose page address carries none", () => {
    window.history.replaceState(null, "", `/?history=${encodeURIComponent(NAME)}&b=abc#key=tab-key`);
    adoptKeyFromLocation();
    const link = roomLink(window.location.href, "room-1");
    expect(link).toContain("room=room-1");
    expect(link.endsWith("#key=tab-key")).toBe(true);
    expect(window.location.href).not.toContain("tab-key");
  });
});
