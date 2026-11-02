// src/rooms/pageCheck.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  RELOAD_GUARD_MS,
  checkNotice,
  decideCheck,
  lastLayoutReload,
  lastSelfReload,
  pageReport,
  reloadKeepingView,
  takeSavedView,
} from "@/rooms/pageCheck";

const OK = { build: "ok", fingerprint: "ok", layout: "ok" } as const;
const NOW = 1_800_000_000_000;

afterEach(() => sessionStorage.clear());

describe("the page check", () => {
  it("does nothing when the picture is the room's", () => {
    expect(decideCheck(OK, NOW, null)).toEqual({ reload: false, layoutReload: false, reloadHeldBack: false, reread: false, pointersOff: false });
    expect(checkNotice(decideCheck(OK, NOW, null))).toBeNull();
  });

  it("reloads a tab running another build", () => {
    const outcome = decideCheck({ ...OK, build: "reload" }, NOW, null);
    expect(outcome.reload).toBe(true);
    expect(checkNotice(outcome)).toBe("Maxitor was updated — reloading…");
  });

  it("never reloads twice within five minutes", () => {
    const soon = decideCheck({ ...OK, build: "reload" }, NOW, NOW - RELOAD_GUARD_MS + 1);
    expect(soon).toMatchObject({ reload: false, reloadHeldBack: true });
    expect(checkNotice(soon)).toBe("Maxitor was updated. Reload this page to get the new version.");
    expect(decideCheck({ ...OK, build: "reload" }, NOW, NOW - RELOAD_GUARD_MS).reload).toBe(true);
  });

  it("re-reads another graph in place", () => {
    expect(decideCheck({ ...OK, fingerprint: "reread" }, NOW, null)).toMatchObject({ reread: true, reload: false });
  });

  it("reloads once, keeping the view, when the room drew the page another way (spec 038)", () => {
    const outcome = decideCheck({ ...OK, layout: "reload" }, NOW, null, null);
    expect(outcome).toMatchObject({ reload: true, layoutReload: true, pointersOff: false });
    expect(checkNotice(outcome)).toBe("Taking the room's picture of this page — reloading…");
  });

  it("turns pointers off instead when it already reloaded for the layout within five minutes", () => {
    const again = decideCheck({ ...OK, layout: "reload" }, NOW, null, NOW - RELOAD_GUARD_MS + 1);
    expect(again).toMatchObject({ reload: false, layoutReload: false, pointersOff: true });
    expect(checkNotice(again)).toBe("Pointers are off on this page: your diagram is laid out differently from the room's.");
  });

  it("keeps pointers off when the server says the layout differs after both sides reloaded", () => {
    const off = decideCheck({ ...OK, layout: "off" }, NOW, null, null);
    expect(off).toMatchObject({ reload: false, layoutReload: false, pointersOff: true });
    expect(checkNotice(off)).toBe("Pointers are off on this page: your diagram is laid out differently from the room's.");
  });

  it("is not held back by a reload for a new build, nor holds one back", () => {
    expect(decideCheck({ ...OK, layout: "reload" }, NOW, NOW - 1, null).layoutReload).toBe(true);
    expect(decideCheck({ ...OK, build: "reload" }, NOW, null, NOW - 1)).toMatchObject({ reload: true, layoutReload: false });
  });
});

describe("reloading itself", () => {
  it("keeps the view and the time, and gives the view back once", () => {
    const reload = vi.fn();
    reloadKeepingView({ x: 10, y: -4, zoom: 1.5 }, NOW, reload);
    expect(reload).toHaveBeenCalled();
    expect(lastSelfReload()).toBe(NOW);
    expect(takeSavedView()).toEqual({ x: 10, y: -4, zoom: 1.5 });
    expect(takeSavedView()).toBeNull();
  });

  it("keeps the time of a layout reload apart from a build reload's", () => {
    reloadKeepingView(null, NOW, vi.fn(), true);
    expect(lastLayoutReload()).toBe(NOW);
    expect(lastSelfReload()).toBeNull();
  });
});

describe("the page report", () => {
  it("carries the build, the graph and, once drawn, the layout and settings", () => {
    const element = document.createElement("div");
    expect(pageReport("view=domain-erd", "b1", "f1", element)).toEqual({ type: "page", page: "view=domain-erd", build: "b1", fingerprint: "f1" });
    element.setAttribute("data-layout-hash", "h1");
    element.setAttribute("data-layout-input", "d1");
    expect(pageReport("view=domain-erd", "b1", "f1", element)).toMatchObject({ layout_hash: "h1", settings_digest: "d1" });
  });

  it("says the tab reloaded for its layout lately, so the room can reload its own side instead (spec 038)", () => {
    expect(pageReport("view=domain-erd", "b1", "f1", null, NOW)).not.toHaveProperty("layout_reloaded");
    reloadKeepingView(null, NOW, vi.fn(), true);
    expect(pageReport("view=domain-erd", "b1", "f1", null, NOW + 1000)).toMatchObject({ layout_reloaded: true });
    expect(pageReport("view=domain-erd", "b1", "f1", null, NOW + RELOAD_GUARD_MS)).not.toHaveProperty("layout_reloaded");
  });
});

describe("the report of Side by side (spec 044)", () => {
  const element = (hash: string, input: string) => {
    const made = document.createElement("div");
    made.setAttribute("data-layout-hash", hash);
    made.setAttribute("data-layout-input", input);
    return made;
  };

  it("names both pictures and both inputs", () => {
    expect(pageReport("view=domain-erd", "b1", "f1", element("hb", "db"), 0, element("ha", "da"))).toMatchObject({ layout_hash: "ha.hb", settings_digest: "da.db" });
  });
});
