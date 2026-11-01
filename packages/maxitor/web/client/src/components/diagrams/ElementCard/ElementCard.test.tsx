import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CardSubject } from "./ElementCard";

const fetchElementCard = vi.fn();
const getActiveBase = vi.fn();
vi.mock("@/api/elementCard", () => ({ fetchElementCard }));
vi.mock("@/api/client", () => ({ getActiveBase }));
vi.mock("./LifecycleMiniature", () => ({ LifecycleMiniature: ({ lifecycleId, dimmed, onSettled }: { lifecycleId: string; dimmed?: boolean; onSettled?: (width: number) => void }) => <div data-testid="miniature" data-dimmed={dimmed} onClick={() => onSettled?.(100)}>{lifecycleId}</div> }));
vi.mock("@/components/history/DiffCard", () => ({ DiffBody: () => <div data-testid="diff-body" />, StatusIcon: ({ status }: { status: string }) => <img alt={status} /> }));

const { ElementCard } = await import("./ElementCard");
const { focusToSend } = await import("@/rooms/focusStore");

const subject: CardSubject = { key: "k", ref: { kind: "row", id: "fn0_0" }, title: "price", detail: "int", nodeId: "a:price", change: null, at: { x: 0, y: 0 } };
const show = (over: Partial<CardSubject> = {}) => render(<ElementCard subject={{ ...subject, ...over }} newer="B" onEnter={() => undefined} onLeave={() => undefined} onClose={() => undefined} />);

describe("ElementCard", () => {
  beforeEach(() => {
    localStorage.setItem("maxitor:cardFieldsOpen", "1");
    fetchElementCard.mockReset().mockResolvedValue({ id: "a:price", type: "field", label: "price", description: null, lifecycle_id: null });
    getActiveBase.mockReset().mockReturnValue(null);
  });
  afterEach(cleanup);

  it("in One has no status", async () => {
    show();
    await waitFor(() => expect(fetchElementCard).toHaveBeenCalled());
    expect(screen.queryByAltText("unchanged")).toBeNull();
  });

  it("in a comparison gives an unchanged element the shape of a changed one", () => {
    getActiveBase.mockReturnValue({ source: "a", key: "" });
    show();
    expect(screen.getByAltText("unchanged")).toBeTruthy();
  });

  it("does not call a changed element unchanged", () => {
    getActiveBase.mockReturnValue({ source: "a", key: "" });
    show({ change: { title: "price", status: "added", elements: [] } });
    expect(screen.queryByAltText("unchanged")).toBeNull();
    expect(screen.getByAltText("added")).toBeTruthy();
    expect(screen.getByTestId("diff-body")).toBeTruthy();
  });

  it("shows a description and leaves it out when there is none", async () => {
    fetchElementCard.mockResolvedValue({ id: "t", type: "entity", label: "T", description: "One row", lifecycle_id: null });
    show();
    expect((await screen.findByTestId("card-description")).textContent).toBe("One row");
    cleanup();
    fetchElementCard.mockResolvedValue({ id: "t", type: "entity", label: "T", description: null, lifecycle_id: null });
    show();
    await waitFor(() => expect(fetchElementCard).toHaveBeenCalledTimes(2));
    expect(screen.queryByTestId("card-description")).toBeNull();
  });

  it("keeps a table's list to names, and shows the pointed field's type and description below", () => {
    show({ nodeId: null, fields: [{ name: "id", type: "str", description: "Lot id" }, { name: "plain", type: "int" }] });
    expect(screen.getAllByTestId("card-field").map((each) => each.textContent)).toEqual(["id", "plain"]);
    expect(screen.getByTestId("card-field-hint").textContent).toBe("Hover a field");
    fireEvent.mouseEnter(screen.getAllByTestId("card-field")[0]!);
    expect(screen.getByTestId("card-field-hint").textContent).toBe("strLot id");
    fireEvent.mouseLeave(screen.getByTestId("card-fields"));
    expect(screen.getByTestId("card-field-hint").textContent).toBe("Hover a field");
  });

  it("marks the pointed name by weight and colour", () => {
    show({ nodeId: null, fields: [{ name: "id" }] });
    const name = screen.getByTestId("card-field-name");
    expect(getComputedStyle(name).fontWeight).not.toBe("600");
    fireEvent.mouseEnter(screen.getByTestId("card-field"));
    expect(getComputedStyle(name).fontWeight).toBe("600");
  });

  it("shows a pointed field on a tap too", () => {
    show({ nodeId: null, fields: [{ name: "id", type: "str" }] });
    fireEvent.click(screen.getByTestId("card-field"));
    expect(screen.getByTestId("card-field-hint").textContent).toBe("str");
  });

  it("shows a changed type with what it was in the same place, never in the list", () => {
    show({ nodeId: null, fields: [{ name: "id", type: "int", previousType: "str" }] });
    expect(screen.getByTestId("card-field").textContent).toBe("id");
    fireEvent.mouseEnter(screen.getByTestId("card-field"));
    expect(screen.getByTestId("card-field-hint").textContent).toBe("str → int");
  });

  it("stays unseen until what it reads has come", async () => {
    let answer: (value: unknown) => void = () => undefined;
    fetchElementCard.mockReturnValue(new Promise((resolve) => (answer = resolve)));
    show();
    expect(screen.getByTestId("element-card").style.visibility === "visible" || getComputedStyle(screen.getByTestId("element-card")).visibility).toBe("hidden");
    answer(null);
    await waitFor(() => expect(getComputedStyle(screen.getByTestId("element-card")).visibility).toBe("visible"));
  });

  it("waits for a lifecycle's picture too", async () => {
    show({ nodeId: null, lifecycleIds: ["a:lifecycle:s"] });
    expect(getComputedStyle(screen.getByTestId("element-card")).visibility).toBe("hidden");
    fireEvent.click(screen.getByTestId("miniature"));
    await waitFor(() => expect(getComputedStyle(screen.getByTestId("element-card")).visibility).toBe("visible"));
  });

  it("lights a field's lifecycle and dims the others", () => {
    show({ nodeId: null, lifecycleIds: ["a:lifecycle:s", "a:lifecycle:t"], fields: [{ name: "s", lifecycleId: "a:lifecycle:s" }, { name: "plain" }] });
    const dimmed = () => screen.getAllByTestId("miniature").map((each) => each.dataset.dimmed);
    expect(dimmed()).toEqual(["false", "false"]);
    fireEvent.mouseEnter(screen.getAllByTestId("card-field")[0]!);
    expect(dimmed()).toEqual(["false", "true"]);
    fireEvent.mouseEnter(screen.getAllByTestId("card-field")[1]!);
    expect(dimmed()).toEqual(["false", "false"]);
  });

  it("hides a table's fields at first, and remembers a choice for the next card", () => {
    localStorage.removeItem("maxitor:cardFieldsOpen");
    const fields = [{ name: "id" }, { name: "plain" }];
    show({ nodeId: null, fields });
    expect(screen.queryAllByTestId("card-field")).toEqual([]);
    expect(screen.getByTestId("card-fields-toggle").textContent).toBe("2 fields");
    fireEvent.click(screen.getByTestId("card-fields-toggle"));
    expect(screen.getAllByTestId("card-field")).toHaveLength(2);
    cleanup();
    show({ key: "other", nodeId: null, fields });
    expect(screen.getAllByTestId("card-field")).toHaveLength(2);
    fireEvent.click(screen.getByTestId("card-fields-toggle"));
    cleanup();
    show({ nodeId: null, fields });
    expect(screen.queryAllByTestId("card-field")).toEqual([]);
  });

  it("hides every field with the list hidden, and counts what changed", () => {
    localStorage.setItem("maxitor:cardFieldsOpen", "0");
    show({ nodeId: null, fields: [{ name: "same" }, { name: "new", status: "added" }, { name: "typed", status: "changed", previousType: "str", type: "int" }] });
    expect(screen.queryAllByTestId("card-field")).toEqual([]);
    expect(screen.getAllByTestId("card-fields-count").map((each) => each.textContent)).toEqual(["+1", "~1"]);
  });

  it("reports what happens inside it, for a follower", () => {
    show({ nodeId: null, fields: [{ name: "id" }, { name: "plain" }] });
    fireEvent.mouseEnter(screen.getAllByTestId("card-field")[1]!);
    expect(focusToSend("p").panels.card).toEqual({ ref: subject.ref, fields: true, field: 1, scroll: 0, at: null });
    cleanup();
    expect(focusToSend("p").panels.card).toBeNull();
  });

  it("tells two rows of one name apart", () => {
    show({ nodeId: null, fields: [{ name: "currency", type: "str" }, { name: "currency", type: "Enum" }] });
    fireEvent.mouseEnter(screen.getAllByTestId("card-field")[1]!);
    expect(screen.getByTestId("card-field-hint").textContent).toBe("Enum");
  });

  it("hides the list of a table that came whole", () => {
    localStorage.setItem("maxitor:cardFieldsOpen", "0");
    show({ nodeId: null, fields: [{ name: "id", status: "added" }, { name: "new", status: "added" }] });
    expect(screen.queryAllByTestId("card-field")).toEqual([]);
    expect(screen.queryAllByTestId("card-fields-count")).toEqual([]);
    fireEvent.click(screen.getByTestId("card-fields-toggle"));
    expect(screen.getAllByTestId("card-field")).toHaveLength(2);
  });

  it("draws every lifecycle of a table", () => {
    show({ nodeId: null, lifecycleIds: ["a:lifecycle:s", "a:lifecycle:t"] });
    expect(screen.getAllByTestId("miniature").map((each) => each.textContent)).toEqual(["a:lifecycle:s", "a:lifecycle:t"]);
  });

  it("keeps what it knows when the read fails", async () => {
    fetchElementCard.mockRejectedValue(new Error("no"));
    show();
    expect((await screen.findByTestId("card-unread")).textContent).toContain("could not be read");
    expect(screen.getByTestId("card-detail").textContent).toBe("int");
  });

  it("asks nothing for a line and shows a lifecycle named by the row", () => {
    show({ nodeId: null, lifecycleIds: ["a:lifecycle:s"] });
    expect(fetchElementCard).not.toHaveBeenCalled();
    expect(screen.getByTestId("miniature").textContent).toBe("a:lifecycle:s");
  });
});

describe("drawnWidth", () => {
  it("reads a drawing's width from its viewBox", async () => {
    const { drawnWidth } = await vi.importActual<typeof import("./LifecycleMiniature")>("./LifecycleMiniature");
    expect(drawnWidth('<svg viewBox="0.00 0.00 612.50 90.00">')).toBe(612.5);
    expect(drawnWidth(null)).toBe(0);
  });
});
