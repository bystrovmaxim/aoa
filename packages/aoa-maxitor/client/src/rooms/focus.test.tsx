// src/rooms/focus.test.tsx
import { act, renderHook } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useFollow } from "@/rooms/follow";
import {
  clearFocus,
  focusToSend,
  putFocus,
  reportHover,
  reportPanels,
  setFollowTarget,
  useShownPanel,
  type FocusState,
} from "@/rooms/focusStore";
import { elementRefOf, elementsOf, tooltipOf, useGraphvizFocus } from "@/rooms/graphvizFocus";
import type { RoomState } from "@/rooms/roomStore";

const ERD = "view=domain-erd";

const annasFocus: FocusState = {
  page: ERD,
  hover: { kind: "row", id: "fn0_1" },
  tooltip: { kind: "row", id: "fn0_1" },
  selection: null,
  panels: { sidebar: ["domains_root"], filter: "kinds", legend: false },
};

/** A Graphviz-like drawing: one table with a row cell, and a line. */
function drawing(): HTMLDivElement {
  const root = document.createElement("div");
  root.innerHTML = `
    <svg>
      <g class="node"><title>Orders</title>
        <g id="a_fn0_1"><a xlink:title="customer_id: str"><text>customer_id</text></a></g>
      </g>
      <g class="edge" id="re0"><title>Orders&#45;&gt;Customers</title><path d="M0 0"/></g>
    </svg>`;
  document.body.appendChild(root);
  return root;
}

afterEach(() => {
  clearFocus();
  document.body.innerHTML = "";
  vi.useRealTimers();
});

describe("what a tab sends as its focus (spec 029, FR-010)", () => {
  it("is its own hover and panels while it follows nobody", () => {
    reportHover({ kind: "table", id: "Orders" });
    reportPanels({ filter: "domains" });
    expect(focusToSend(ERD)).toMatchObject({ page: ERD, hover: { kind: "table", id: "Orders" }, tooltip: { kind: "table", id: "Orders" }, panels: { filter: "domains" } });
  });

  it("is what it shows — the followed person's — while it follows, so a chain sees the same", () => {
    reportHover({ kind: "table", id: "Mine" });
    putFocus("anna", annasFocus);
    setFollowTarget("anna");
    expect(focusToSend(ERD).hover).toEqual(annasFocus.hover);
  });
});

describe("the focus a tab sends to its followers", () => {
  beforeEach(() => vi.useFakeTimers());

  const room = { youId: "boris", follows: { boris: null }, participants: [] } as unknown as RoomState;

  it("goes out at most ten times a second, only when it changed", () => {
    const send = vi.fn();
    renderHook(() => useFollow({ room, send, surface: null, page: ERD, navigate: vi.fn() }));
    act(() => {
      for (let i = 0; i < 50; i += 1) reportHover({ kind: "table", id: `T${i}` });
    });
    act(() => vi.advanceTimersByTime(1000));
    const focus = send.mock.calls.filter(([message]) => message.type === "focus");
    expect(focus.length).toBeGreaterThan(1);
    expect(focus.length).toBeLessThanOrEqual(11);
    expect(focus.at(-1)?.[0].hover).toEqual({ kind: "table", id: "T49" });
  });
});

describe("a Graphviz drawing's hover", () => {
  it("names a row, a line or a table", () => {
    const root = drawing();
    expect(elementRefOf(root.querySelector("text")!, "table")).toEqual({ kind: "row", id: "fn0_1" });
    expect(elementRefOf(root.querySelector("path")!, "table")).toEqual({ kind: "edge", id: "re0" });
    expect(elementRefOf(root.querySelector("g.node > title")!, "table")).toEqual({ kind: "table", id: "Orders" });
    expect(elementsOf(root, { kind: "row", id: "fn0_1" }).map((e) => e.id || "node")).toEqual(["node", "a_fn0_1"]);
    expect(tooltipOf(root.querySelector("#a_fn0_1")!)).toBe("customer_id: str");
  });

  it("is replayed for a follower — even one whose drawing appears after the focus arrived — and handed back on stop", () => {
    putFocus("anna", annasFocus);
    setFollowTarget("anna");
    const root = drawing();
    const entered: string[] = [];
    root.querySelector("g.node")!.addEventListener("mouseenter", () => entered.push("table"));
    root.querySelector("#a_fn0_1")!.addEventListener("mouseenter", () => entered.push("row"));
    root.querySelector("#a_fn0_1")!.addEventListener("mouseleave", () => entered.push("row left"));
    renderHook(() => useGraphvizFocus(root, "svg-1", ERD, "table"));
    expect(entered).toEqual(["table", "row"]);
    act(() => setFollowTarget(null));
    expect(entered.at(-1)).toBe("row left");
  });

  it("shows the followed person's tooltip text beside the element, inside the window", () => {
    vi.useFakeTimers();
    putFocus("anna", annasFocus);
    setFollowTarget("anna");
    const root = drawing();
    root.querySelector("#a_fn0_1")!.getBoundingClientRect = () => ({ left: window.innerWidth + 50, top: 10, bottom: 20, right: 0, width: 0, height: 10, x: 0, y: 0, toJSON: () => ({}) });
    renderHook(() => useGraphvizFocus(root, "svg-1", ERD, "table"));
    act(() => vi.advanceTimersByTime(600));
    const label = document.querySelector<HTMLElement>("[data-follow-tooltip]")!;
    expect(label.style.display).toBe("block");
    expect(label.textContent).toBe("customer_id: str");
    expect(parseFloat(label.style.left)).toBeLessThanOrEqual(window.innerWidth);
  });

  it("is not replayed from a focus about another page", () => {
    putFocus("anna", { ...annasFocus, page: "view=full-graph" });
    setFollowTarget("anna");
    const root = drawing();
    const entered: string[] = [];
    root.querySelector("g.node")!.addEventListener("mouseenter", () => entered.push("table"));
    renderHook(() => useGraphvizFocus(root, "svg-1", ERD, "table"));
    expect(entered).toEqual([]);
  });
});

describe("a panel while following (spec 029, FR-012)", () => {
  /** A filter panel's state through ``useShownPanel``. */
  function usePanel() {
    const [own, setOwn] = useState<FocusState["panels"]["filter"]>("domains");
    const shown = useShownPanel(own, setOwn, (panels) => panels.filter, (value) => ({ filter: value }));
    return { own, shown };
  }

  it("shows the followed person's panel, and keeps it as its own when following stops", () => {
    const panel = renderHook(usePanel);
    expect(panel.result.current.shown).toBe("domains");
    act(() => {
      putFocus("anna", annasFocus);
      setFollowTarget("anna");
    });
    expect(panel.result.current.shown).toBe("kinds");
    act(() => setFollowTarget(null));
    expect(panel.result.current).toEqual({ own: "kinds", shown: "kinds" });
  });
});
