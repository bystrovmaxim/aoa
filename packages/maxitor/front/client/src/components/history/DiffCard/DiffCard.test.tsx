// src/components/history/DiffCard/DiffCard.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cardAt } from "@/lib/erdDiffCard";
import type { ErdEntity } from "@/lib/buildDotSource";

const compareElement = vi.fn();
vi.mock("@/api/compare", () => ({ compareElement: (...args: unknown[]) => compareElement(...args) }));

const { DiffCard } = await import("./DiffCard");

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

  it("closes with Escape", () => {
    const onClose = vi.fn();
    render(<DiffCard target={{ ...CHANGED, status: "added" }} newer="0.9.0" at={{ x: 0, y: 0 }} onClose={onClose} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});

describe("what a click opens a card for", () => {
  const entities: ErdEntity[] = [
    { id: "a.Quiet", diff: "unchanged", fields: [{ name: "id", diff: "unchanged" }] },
    { id: "a.Offer", label: "Offer", diff: "changed", fields: [{ name: "id", diff: "unchanged" }, { name: "chosen", diff: "changed" }] },
  ];
  const cell = (id: string) => {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("id", id);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    group.appendChild(text);
    return text;
  };

  it("a marked table's header is its node; a marked row its node and edges; anything unmarked nothing", () => {
    expect(cardAt(cell("a_hn1"), entities)).toEqual({ title: "Offer", status: "changed", elements: [{ kind: "node", id: "a.Offer" }] });
    expect(cardAt(cell("a_ft1_1"), entities)?.elements.map((element) => element.id)).toEqual(["a.Offer:chosen", "a.Offer|entity_field|a.Offer:chosen", "a.Offer|entity_relation|chosen"]);
    expect(cardAt(cell("a_fn1_0"), entities)).toBeNull();
    expect(cardAt(cell("a_hd0"), entities)).toBeNull();
  });
});
