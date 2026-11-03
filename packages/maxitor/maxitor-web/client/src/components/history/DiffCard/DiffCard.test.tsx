// src/components/history/DiffCard/DiffCard.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const compareElement = vi.fn();
vi.mock("@/api/compare", () => ({ compareElement: (...args: unknown[]) => compareElement(...args) }));

const { DiffCard } = await import("./DiffCard");
const { StatusIcon } = await import("./StatusIcon");

afterEach(() => {
  cleanup();
  compareElement.mockReset();
});

const CHANGED = { title: "chosen", status: "changed" as const, elements: [{ kind: "node" as const, id: "a.Offer:chosen" }, { kind: "edge" as const, id: "a.Offer|entity_relation|chosen" }] };

describe("the card of a changed element", () => {
  it("lists every changed property of every element it stands for, with both values (SC-006)", async () => {
    compareElement.mockImplementation(async (kind: string) =>
      kind === "edge"
        ? { status: "changed", differences: [{ path: ["target_id"], change: "changed", before: "a.Core", after: "a.Detail" }] }
        : { status: "changed", differences: [{ path: ["properties", "field_type"], change: "changed", before: "str", after: "str | None" }, { path: ["properties", "note"], change: "added", after: { deep: 1 } }] },
    );
    render(<DiffCard target={CHANGED} newer="0.9.0" at={{ x: 0, y: 0 }} onClose={() => undefined} />);
    const rows = await screen.findAllByTestId("diff-row");
    expect(rows.map((row) => row.textContent)).toEqual(["properties.field_typestr → str | None", 'properties.noteadded: {"deep":1}', "target_ida.Core → a.Detail"]);
    expect(compareElement.mock.calls).toEqual([["node", "a.Offer:chosen"], ["edge", "a.Offer|entity_relation|chosen"]]);
  });

  it("leaves out an element neither version has", async () => {
    compareElement.mockImplementation(async (kind: string) => {
      if (kind === "node") throw new Error("404");
      return { status: "changed", differences: [{ path: ["target_id"], change: "changed", before: "a", after: "b" }] };
    });
    render(<DiffCard target={CHANGED} newer="0.9.0" at={{ x: 0, y: 0 }} onClose={() => undefined} />);
    expect(await screen.findAllByTestId("diff-row")).toHaveLength(1);
  });

  it("says an added or removed element was added or removed in B, and reads nothing", () => {
    render(<DiffCard target={{ ...CHANGED, status: "added" }} newer="0.9.0" at={{ x: 0, y: 0 }} onClose={() => undefined} />);
    expect(screen.getByText("Added in 0.9.0")).toBeTruthy();
    cleanup();
    render(<DiffCard target={{ ...CHANGED, status: "removed" }} newer="0.9.0" at={{ x: 0, y: 0 }} onClose={() => undefined} />);
    expect(screen.getByText("Removed in 0.9.0")).toBeTruthy();
    expect(compareElement).not.toHaveBeenCalled();
  });

  it("shows a value as text, never as markup", async () => {
    compareElement.mockResolvedValue({ status: "changed", differences: [{ path: ["properties", "description"], change: "changed", before: "<script>alert(1)</script>", after: "<b>new</b>" }] });
    render(<DiffCard target={{ ...CHANGED, elements: [CHANGED.elements[0]] }} newer="0.9.0" at={{ x: 0, y: 0 }} onClose={() => undefined} />);
    const row = await screen.findByTestId("diff-row");
    expect(row.textContent).toContain("<script>alert(1)</script>");
    expect(row.querySelector("script, b")).toBeNull();
  });

  it("says an action changed inside is the same and lists its parts by group, with both values", async () => {
    compareElement.mockResolvedValue({ status: "unchanged", differences: [] });
    const parts = [
      { kind: "node" as const, id: "p:key", label: "key", type: "Field", group: "Params", status: "added" as const, differences: [] },
      { kind: "node" as const, id: "r:ref", label: "ref", type: "Field", group: "Result", status: "changed" as const, differences: [{ path: ["properties", "description"], change: "changed" as const, before: "old", after: "new" }] },
    ];
    render(<DiffCard target={{ title: "SettleAction", status: "changed", elements: [{ kind: "node", id: "a" }], parts }} newer="0.9.0" at={{ x: 0, y: 0 }} onClose={() => undefined} />);
    expect((await screen.findByTestId("diff-inside")).textContent).toBe("The action is the same; its parts changed.");
    expect(screen.queryByText("No property differs.")).toBeNull();
    expect(screen.getAllByTestId("diff-part-group").map((group) => group.firstChild?.textContent)).toEqual(["Params", "Result"]);
    expect(screen.getAllByTestId("diff-part")[0].textContent).toBe("+ key");
    expect(screen.getByTestId("diff-row").textContent).toBe("properties.descriptionold → new");
  });

  it("lists an action's own differences above its parts, with no line that it is the same", async () => {
    compareElement.mockResolvedValue({ status: "changed", differences: [{ path: ["label"], change: "changed", before: "A", after: "B" }] });
    const parts = [{ kind: "node" as const, id: "r:ref", label: "ref", type: "Field", group: "Result", status: "added" as const, differences: [] }];
    render(<DiffCard target={{ title: "SettleAction", status: "changed", elements: [{ kind: "node", id: "a" }], parts }} newer="0.9.0" at={{ x: 0, y: 0 }} onClose={() => undefined} />);
    await screen.findByTestId("diff-row");
    expect(screen.queryByTestId("diff-inside")).toBeNull();
    expect(screen.getAllByTestId("diff-part-group")).toHaveLength(1);
  });

  it("stays open on a click on the change stepper, and closes on a click anywhere else", async () => {
    const onClose = vi.fn();
    render(
      <div>
        <div data-testid="change-stepper"><button>Next</button></div>
        <button>Elsewhere</button>
        <DiffCard target={{ ...CHANGED, status: "added" }} newer="0.9.0" at={{ x: 0, y: 0 }} onClose={onClose} />
      </div>,
    );
    // The listener arms itself a tick after the card mounts.
    await new Promise((resolve) => setTimeout(resolve));
    fireEvent.click(screen.getByText("Next"));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Elsewhere"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("closes with Escape", () => {
    const onClose = vi.fn();
    render(<DiffCard target={{ ...CHANGED, status: "added" }} newer="0.9.0" at={{ x: 0, y: 0 }} onClose={onClose} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});

describe("the status icon", () => {
  it("has a sign for every status, unchanged too", () => {
    const signOf = (status: "added" | "removed" | "changed" | "unchanged") => {
      const { container, unmount } = render(<StatusIcon status={status} />);
      const svg = decodeURIComponent(container.querySelector("img")!.getAttribute("src")!);
      unmount();
      return />([^<]+)<\/text>/.exec(svg)?.[1];
    };
    expect([signOf("added"), signOf("removed"), signOf("changed"), signOf("unchanged")]).toEqual(["+", "−", "~", "="]);
  });
});
