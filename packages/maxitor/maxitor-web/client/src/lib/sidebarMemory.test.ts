// src/lib/sidebarMemory.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { readSidebarMemory, readSidebarRail, writeSidebarMemory, writeSidebarRail } from "@/lib/sidebarMemory";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("the left panel's memory", () => {
  it("gives back what it was told", () => {
    writeSidebarMemory({ open: ["domains_root", "a.Orders"], changedOnly: true });
    expect(readSidebarMemory()).toEqual({ open: ["domains_root", "a.Orders"], changedOnly: true });
  });

  it("remembers the rail", () => {
    expect(readSidebarRail()).toBe(false);
    writeSidebarRail(true);
    expect(readSidebarRail()).toBe(true);
  });

  it("opens closed on nothing, on what is out of shape, and when the browser refuses", () => {
    expect(readSidebarMemory()).toEqual({ open: [], changedOnly: false });
    localStorage.setItem("maxitor.left-panel", "{not json");
    expect(readSidebarMemory()).toEqual({ open: [], changedOnly: false });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("refused");
    });
    expect(() => writeSidebarMemory({ open: [], changedOnly: false })).not.toThrow();
  });
});
