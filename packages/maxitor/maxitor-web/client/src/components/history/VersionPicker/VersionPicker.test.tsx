// src/components/history/VersionPicker/VersionPicker.test.tsx
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { VersionMessage } from "@/components/history/VersionMessage";
import { setSmallPointsShown } from "@/lib/smallPointsShown";
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
    render(<VersionPicker anchor={{ current: document.body }} onClose={() => undefined} title="orders" path="owner/service/orders" versions={versions} live="https://live" value="live" onChange={() => undefined} />);
    expect(screen.getByText("orders")).toBeTruthy();
    expect(screen.getByText("2 versions and Live")).toBeTruthy();
    expect(screen.getByRole("radio", { name: "One" }).getAttribute("aria-checked")).toBe("true");
    for (const mode of ["Diff", "Side by side"]) expect(screen.getByRole("radio", { name: mode }).getAttribute("aria-disabled")).toBe("true");
  });

  it("stays closed without a button to open under", () => {
    render(<VersionPicker anchor={null} onClose={() => undefined} title="orders" path="owner/service/orders" versions={versions} live={null} value={null} onChange={() => undefined} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("offers Diff from two points, and switches to it (spec 038, FR-015)", () => {
    const onMode = vi.fn();
    render(<VersionPicker anchor={{ current: document.body }} onClose={() => undefined} title="orders" path="owner/service/orders" versions={versions} live={null} value={versions[1].sha.slice(0, 12)} onChange={() => undefined} mode="one" onMode={onMode} diffOffered />);
    const diff = screen.getByRole("radio", { name: "Diff" });
    expect(diff.getAttribute("aria-disabled")).toBeNull();
    fireEvent.click(diff);
    expect(onMode).toHaveBeenCalledWith("diff");
    const split = screen.getByRole("radio", { name: "Side by side" });
    expect(split.getAttribute("aria-disabled")).toBeNull();
    fireEvent.click(split);
    expect(onMode).toHaveBeenCalledWith("split");
  });

  it("greys Diff out with \"needs two versions\" where there is one point (M3, M6)", () => {
    const onMode = vi.fn();
    render(<VersionPicker anchor={{ current: document.body }} onClose={() => undefined} title="orders" path="owner/service/orders" versions={versions.slice(0, 1)} live={null} value={versions[0].sha.slice(0, 12)} onChange={() => undefined} mode="one" onMode={onMode} diffOffered={false} />);
    const diff = screen.getByRole("radio", { name: "Diff" });
    expect(diff.getAttribute("aria-disabled")).toBe("true");
    fireEvent.click(diff);
    fireEvent.click(screen.getByRole("radio", { name: "Side by side" }));
    expect(onMode).not.toHaveBeenCalled();
    fireEvent.mouseOver(diff);
    return screen.findByText("needs two versions");
  });

  it("in Diff holds a range on its track and goes back to One", () => {
    const onMode = vi.fn();
    const [a, b] = versions.map((each) => each.sha.slice(0, 12));
    render(<VersionPicker anchor={{ current: document.body }} onClose={() => undefined} title="orders" path="owner/service/orders" versions={versions} live={null} value={b} onChange={() => undefined} mode="diff" onMode={onMode} diffOffered range={{ a, b }} onRange={() => undefined} />);
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
        title="orders" path="owner/service/orders"
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

describe("a version file in the picker (spec 051)", () => {
  const joined = versions.map((version, at) => ({ ...version, graph_changed: at === 0, version: "1.0.0", version_changed: at === 0 }));
  const base = { anchor: { current: document.body }, onClose: () => undefined, title: "orders", path: "owner/service/orders", live: null, value: "1", onChange: () => undefined };

  beforeEach(() => setSmallPointsShown(true));

  it("offers the icon only where a point did not change the graph, and it hides this viewer's small points", () => {
    const { rerender } = render(<VersionPicker {...base} versions={versions} versionFile />);
    const icon = () => screen.queryByRole("button", { name: "The versions that did not change the graph" });
    expect(icon()).toBeNull();
    rerender(<VersionPicker {...base} versions={joined} />);
    expect(icon()).toBeNull();
    rerender(<VersionPicker {...base} versions={joined} versionFile />);
    expect(icon()?.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(icon()!);
    expect(icon()?.getAttribute("aria-pressed")).toBe("false");
    expect(screen.queryByTestId(`point-${joined[1].sha.slice(0, 12)}`)).toBeNull();
  });

  it("says a version problem in plain words, and says nothing without one", () => {
    const { rerender } = render(<VersionPicker {...base} versions={joined} versionFile versionProblem="The file holds no version." />);
    expect(screen.getByTestId("version-problem").textContent).toBe("The newest version cannot be read. The file holds no version.");
    rerender(<VersionPicker {...base} versions={joined} versionFile />);
    expect(screen.queryByTestId("version-problem")).toBeNull();
  });

  it("says the track shows only graph changes when no version could be read", () => {
    render(<VersionPicker {...base} versions={versions} versionFile versionProblem="The file holds no version." />);
    expect(screen.getByTestId("version-problem").textContent).toContain("shows only the commits that changed the graph");
  });

  it("says two compared points have the same graph", () => {
    const range = { a: versions[0].sha.slice(0, 12), b: versions[1].sha.slice(0, 12) };
    const { rerender } = render(<VersionPicker {...base} versions={joined} versionFile mode="diff" range={range} />);
    expect(screen.getByTestId("same-graph").textContent).toBe("Both versions have the same graph.");
    rerender(<VersionPicker {...base} versions={versions} mode="diff" range={range} />);
    expect(screen.queryByTestId("same-graph")).toBeNull();
  });
});

describe("the history's name", () => {
  // The tests below put their own copy command on the document; the next test starts without it.
  afterEach(() => void Reflect.deleteProperty(document, "execCommand"));

  const picker = () => render(<VersionPicker anchor={{ current: document.body }} onClose={() => undefined} title="maxitor-web" path="bystrovmaxim/aoa/packages/maxitor/maxitor-web" versions={versions} live={null} value={null} onChange={() => undefined} />);

  it("is the only line of the head about the history: its path is not written under it", () => {
    picker();
    expect(screen.getByRole("button", { name: "maxitor-web" })).toBeTruthy();
    expect(screen.queryByText("bystrovmaxim/aoa/packages/maxitor/maxitor-web")).toBeNull();
  });

  it("shows its full path on hover", async () => {
    picker();
    fireEvent.mouseOver(screen.getByRole("button", { name: "maxitor-web" }));
    expect(await screen.findByText("bystrovmaxim/aoa/packages/maxitor/maxitor-web")).toBeTruthy();
  });

  it("copies its full path on a click and says so", async () => {
    const writeText = vi.fn(() => Promise.resolve());
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    picker();
    const name = screen.getByRole("button", { name: "maxitor-web" });
    fireEvent.mouseOver(name);
    fireEvent.click(name);
    expect(writeText).toHaveBeenCalledWith("bystrovmaxim/aoa/packages/maxitor/maxitor-web");
    expect(await screen.findByText("Copied")).toBeTruthy();
  });

  it("copies through a selected text where the page may not write to the clipboard", async () => {
    vi.stubGlobal("navigator", { clipboard: { writeText: () => Promise.reject(new Error("denied")) } });
    const copied: string[] = [];
    document.execCommand = vi.fn(() => {
      copied.push(document.querySelector("textarea")?.value ?? "");
      return true;
    });
    picker();
    const name = screen.getByRole("button", { name: "maxitor-web" });
    fireEvent.mouseOver(name);
    fireEvent.click(name);
    expect(await screen.findByText("Copied")).toBeTruthy();
    expect(copied).toEqual(["bystrovmaxim/aoa/packages/maxitor/maxitor-web"]);
    expect(document.querySelector("textarea")).toBeNull();
  });

  it("says it could not copy when neither way copies", async () => {
    vi.stubGlobal("navigator", { clipboard: { writeText: () => Promise.reject(new Error("denied")) } });
    document.execCommand = vi.fn(() => false);
    picker();
    const name = screen.getByRole("button", { name: "maxitor-web" });
    fireEvent.mouseOver(name);
    fireEvent.click(name);
    expect(await screen.findByText("Not copied")).toBeTruthy();
  });
});
