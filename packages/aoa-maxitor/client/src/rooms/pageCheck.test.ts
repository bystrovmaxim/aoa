// src/rooms/pageCheck.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  RELOAD_GUARD_MS,
  checkNotice,
  decideCheck,
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
    expect(decideCheck(OK, NOW, null)).toEqual({ reload: false, reloadHeldBack: false, reread: false, pointersOff: false });
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

  it("turns pointers off when the layout differs", () => {
    const outcome = decideCheck({ ...OK, layout: "off" }, NOW, null);
    expect(outcome.pointersOff).toBe(true);
    expect(checkNotice(outcome)).toBe("Pointers are off on this page: your diagram is laid out differently from the room's.");
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
});

describe("the page report", () => {
  it("carries the build, the graph and, once drawn, the layout and settings", () => {
    const element = document.createElement("div");
    expect(pageReport("view=domain-erd", "b1", "f1", element)).toEqual({ type: "page", page: "view=domain-erd", build: "b1", fingerprint: "f1" });
    element.setAttribute("data-layout-hash", "h1");
    element.setAttribute("data-layout-input", "d1");
    expect(pageReport("view=domain-erd", "b1", "f1", element)).toMatchObject({ layout_hash: "h1", settings_digest: "d1" });
  });
});
