// src/components/history/VersionPicker/VersionPicker.phone.test.tsx
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { TOUCH_STEP } from "@/components/history/VersionTrack/VersionTrack";
import { VersionPicker } from "./VersionPicker";

/** jsdom has no ResizeObserver; the picker only uses it to follow its button. */
class NoResize {
  observe(): void {}
  disconnect(): void {}
}

beforeEach(() => vi.stubGlobal("ResizeObserver", NoResize));
afterEach(() => vi.unstubAllGlobals());


afterEach(cleanup);

function versions(count: number): HistoryVersion[] {
  return Array.from({ length: count }, (_, i) => ({ sha: `${i}`.padStart(4, "0").padEnd(40, "f"), date: "2026-10-01T00:00:00Z", tags: [], nodes: 1, edges: 1, source: `s${i}` }));
}

function picker(count: number, live: string | null, value: string | null) {
  render(
    <VersionPicker anchor={{ current: document.body }} onClose={() => undefined} title="orders" versions={versions(count)} live={live} value={value} onChange={() => undefined} phone>
      <div data-testid="message-slot">message</div>
    </VersionPicker>,
  );
}

describe.each([
  ["M2", 12, null, "0011ffffffff"],
  ["M3", 1, null, "0000ffffffff"],
  ["M5", 1, "https://live", "live"],
  ["M6", 0, "https://live", "live"],
] as const)("the sheet on a phone, %s", (_mode, count, live, value) => {
  it("opens from the bottom with the head, the track and the message", () => {
    picker(count, live, value);
    const sheet = screen.getByRole("dialog", { name: "Pick a version" });
    expect(sheet.closest(".MuiDrawer-root")).not.toBeNull();
    expect(sheet.closest(".MuiPopover-root")).toBeNull();
    expect(screen.getByText("orders")).toBeTruthy();
    expect(screen.getByRole("slider")).toBeTruthy();
    expect(screen.getByTestId("message-slot")).toBeTruthy();
  });

  it("makes every point a touch target of at least 44 px, the points at least 44 px apart", () => {
    picker(count, live, value);
    const targets = screen.queryAllByTestId(/^target-/);
    expect(targets).toHaveLength(count + (live ? 1 : 0));
    for (const target of targets) expect(2 * Number(target.getAttribute("r"))).toBeGreaterThanOrEqual(TOUCH_STEP);
    const xs = screen.queryAllByTestId(/^point-/).map((point) => Number(point.getAttribute("data-x")));
    for (let i = 1; i < xs.length; i += 1) expect(xs[i] - xs[i - 1]).toBeGreaterThanOrEqual(TOUCH_STEP);
  });
});

describe("the picker on a desktop", () => {
  it("is a card under the button, not a sheet, and lets clicks outside it through", () => {
    render(<VersionPicker anchor={{ current: document.body }} onClose={() => undefined} title="orders" versions={versions(3)} live={null} value={null} onChange={() => undefined} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog.closest(".MuiPopper-root")).not.toBeNull();
    expect(dialog.closest(".MuiDrawer-root")).toBeNull();
    expect(document.querySelector(".MuiBackdrop-root")).toBeNull();
  });
});
