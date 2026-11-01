// src/lib/erdCopy.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { bindNameCopy, bareName } from "@/lib/erdCopy";

function mount() {
  document.body.innerHTML =
    '<div id="root"><svg><g id="a_hn0"><a><text>PlayerCoreEntity</text></a></g>' +
    '<g id="a_fn0_1"><a><text>showcase</text></a></g><g id="a_ft0_1"><a><text>ShowcaseCoreEntity</text></a></g></svg></div>';
  const root = document.getElementById("root")!;
  const report = vi.fn();
  bindNameCopy(root, report, new AbortController().signal);
  return { root, report };
}

function press(target: Element, dx = 0) {
  target.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true, clientX: 10, clientY: 10 }));
  target.dispatchEvent(new MouseEvent("pointerup", { bubbles: true, clientX: 10 + dx, clientY: 10 }));
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("bindNameCopy", () => {
  it("copies a table name and a field name on a click, and says so", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    const { root, report } = mount();

    press(root.querySelector("#a_hn0 text")!);
    press(root.querySelector("#a_fn0_1 text")!);
    await flush();

    expect(writeText.mock.calls).toEqual([["PlayerCoreEntity"], ["showcase"]]);
    expect(report.mock.calls).toEqual([["Copied PlayerCoreEntity"], ["Copied showcase"]]);
  });

  it("does not copy when the press moved more than 4 px — that was a pan", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    const { root, report } = mount();

    press(root.querySelector("#a_hn0 text")!, 5);
    await flush();

    expect(writeText).not.toHaveBeenCalled();
    expect(report).not.toHaveBeenCalled();
  });

  it("selects the name and explains when the clipboard is refused", async () => {
    vi.stubGlobal("navigator", { clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) } });
    const { root, report } = mount();

    press(root.querySelector("#a_fn0_1 text")!);
    await flush();

    expect(report).toHaveBeenCalledWith("Selected showcase — press Cmd/Ctrl+C");
    expect(globalThis.getSelection()?.toString()).toBe("showcase");
  });

  it("does nothing on a type cell", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    const { root, report } = mount();

    press(root.querySelector("#a_ft0_1 text")!);
    await flush();

    expect(writeText).not.toHaveBeenCalled();
    expect(report).not.toHaveBeenCalled();
  });
});

describe("a name written with its Diff sign", () => {
  it("is copied bare (spec 038)", () => {
    expect(["+ region", "− is_activated", "~ erid", "region", "  ~ OfferEntity "].map(bareName)).toEqual(["region", "is_activated", "erid", "region", "OfferEntity"]);
  });
});

describe("a touch on a name (spec 043)", () => {
  it("copies nothing: a tap opens the card", () => {
    const root = document.createElement("div");
    root.innerHTML = '<svg><g id="a_fn0_0"><text>name</text></g></svg>';
    const writeText = vi.fn(() => Promise.resolve());
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    bindNameCopy(root, () => undefined, new AbortController().signal);
    const cell = root.querySelector("text")!;
    for (const type of ["pointerdown", "pointerup"]) cell.dispatchEvent(Object.assign(new MouseEvent(type, { bubbles: true }), { pointerType: "touch" }));
    expect(writeText).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
