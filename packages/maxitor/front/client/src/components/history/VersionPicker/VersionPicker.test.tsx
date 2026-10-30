// src/components/history/VersionPicker/VersionPicker.test.tsx
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { VersionMessage } from "@/components/history/VersionMessage";
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

  it("offers Diff from two points, and switches to it (spec 038, FR-015)", () => {
    const onMode = vi.fn();
    render(<VersionPicker anchor={{ current: document.body }} onClose={() => undefined} title="orders" versions={versions} live={null} value={versions[1].sha.slice(0, 12)} onChange={() => undefined} mode="one" onMode={onMode} diffOffered />);
    const diff = screen.getByRole("radio", { name: "Diff" });
    expect(diff.getAttribute("aria-disabled")).toBeNull();
    fireEvent.click(diff);
    expect(onMode).toHaveBeenCalledWith("diff");
    expect(screen.getByRole("radio", { name: "Side by side" }).getAttribute("aria-disabled")).toBe("true");
  });

  it("greys Diff out with \"needs two versions\" where there is one point (M3, M6)", () => {
    const onMode = vi.fn();
    render(<VersionPicker anchor={{ current: document.body }} onClose={() => undefined} title="orders" versions={versions.slice(0, 1)} live={null} value={versions[0].sha.slice(0, 12)} onChange={() => undefined} mode="one" onMode={onMode} diffOffered={false} />);
    const diff = screen.getByRole("radio", { name: "Diff" });
    expect(diff.getAttribute("aria-disabled")).toBe("true");
    fireEvent.click(diff);
    expect(onMode).not.toHaveBeenCalled();
    fireEvent.mouseOver(diff);
    return screen.findByText("needs two versions");
  });

  it("in Diff holds a range on its track and goes back to One", () => {
    const onMode = vi.fn();
    const [a, b] = versions.map((each) => each.sha.slice(0, 12));
    render(<VersionPicker anchor={{ current: document.body }} onClose={() => undefined} title="orders" versions={versions} live={null} value={b} onChange={() => undefined} mode="diff" onMode={onMode} diffOffered range={{ a, b }} onRange={() => undefined} />);
    expect(screen.getByTestId("handle-a")).toBeTruthy();
    expect(screen.getByTestId("handle-b")).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: "One" }));
    expect(onMode).toHaveBeenCalledWith("one");
  });

  it("in Diff puts A's message on the left and B's on the right, Live's closing line on B's side (spec 038, FR-030)", () => {
    const a = versions[0].sha.slice(0, 12);
    render(
      <VersionPicker
        anchor={{ current: document.body }}
        onClose={() => undefined}
        title="orders"
        versions={versions}
        live="https://live"
        value="live"
        onChange={() => undefined}
        mode="diff"
        diffOffered
        range={{ a, b: "live" }}
        onRange={() => undefined}
        older={<VersionMessage version={{ ...versions[0], message: "Older change" }} repository={null} />}
      >
        <VersionMessage version={null} repository={null} liveLine="checked 3 s ago" />
      </VersionPicker>,
    );
    const left = screen.getByTestId("message-a");
    const right = screen.getByTestId("message-b");
    expect(left.compareDocumentPosition(right) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(left.textContent).toBe("Older change");
    expect(within(right).getByTestId("live-line").textContent).toContain("checked 3 s ago");
    expect(within(left).queryByTestId("live-line")).toBeNull();
  });
});
