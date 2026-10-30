// src/components/history/VersionPicker/VersionPicker.test.tsx
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { VersionPicker } from "./VersionPicker";

/** jsdom has no ResizeObserver; the picker only uses it to follow its button. */
class NoResize {
  observe(): void {}
  disconnect(): void {}
}

beforeEach(() => vi.stubGlobal("ResizeObserver", NoResize));


afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const versions: HistoryVersion[] = [1, 2].map((n) => ({ sha: `${n}`.padEnd(40, "c"), date: "2026-10-01T00:00:00Z", tags: [], nodes: 1, edges: 1, source: `s${n}` }));

describe("the picker", () => {
  it("names the service, counts its versions and Live, and greys out the modes that come later", () => {
    render(<VersionPicker anchor={{ current: document.body }} onClose={() => undefined} title="orders" versions={versions} live="https://live" value="live" onChange={() => undefined} />);
    expect(screen.getByText("orders")).toBeTruthy();
    expect(screen.getByText("2 versions and Live")).toBeTruthy();
    expect(screen.getByRole("radio", { name: "One" }).getAttribute("aria-checked")).toBe("true");
    for (const mode of ["Diff", "Side by side"]) expect(screen.getByRole("radio", { name: mode }).getAttribute("aria-disabled")).toBe("true");
  });

  it("stays closed without a button to open under", () => {
    render(<VersionPicker anchor={null} onClose={() => undefined} title="orders" versions={versions} live={null} value={null} onChange={() => undefined} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
