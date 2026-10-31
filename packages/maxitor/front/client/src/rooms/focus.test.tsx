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
  sameFocus,
  useShownPanel,
  type FocusState,
} from "@/rooms/focusStore";
import { elementRefOf, elementsOf, placeLabel, tooltipOf, useGraphvizFocus } from "@/rooms/graphvizFocus";
import type { RoomState } from "@/rooms/roomStore";

const ERD = "view=domain-erd";

const annasFocus: FocusState = {
  page: ERD,
  hover: { kind: "row", id: "fn0_1" },
  tooltip: { kind: "row", id: "fn0_1" },
  selection: null,
  panels: { sidebar: ["domains_root"], filter: "kinds", legend: false, versions: false, track: null, changes: null },
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

/** A real mouse moving over ``target``: only a trusted event is your own hover. */
function hoverTrusted(target: Element): void {
  // jsdom marks every ``dispatchEvent`` untrusted, so the event goes through the implementation's own dispatch, as
  // the browser's does for a real mouse.
  const implOf = (wrapper: object) => (wrapper as Record<symbol, Record<string, unknown>>)[Object.getOwnPropertySymbols(wrapper).find((key) => key.description === "impl")!];
  const event = implOf(new MouseEvent("mouseover", { bubbles: true }));
  event.isTrusted = true;
  (implOf(target)._dispatch as (event: unknown) => void).call(implOf(target), event);
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

  it("takes the native tooltip off the drawing, keeping its text (spec 038)", () => {
    const root = drawing();
    renderHook(() => useGraphvizFocus(root, "svg-1", ERD, "table"));
    const link = root.querySelector("a")!;
    expect(link.getAttribute("xlink:title")).toBeNull();
    expect(link.getAttribute("data-tooltip")).toBe("customer_id: str");
  });

  it("quiets a node's and a line's <title>, which the browser shows over a frame, yet still reads them", () => {
    const root = drawing();
    renderHook(() => useGraphvizFocus(root, "svg-1", ERD, "table"));
    const titles = [...root.querySelectorAll("title")];
    expect(titles.map((title) => title.textContent)).toEqual(["Orders", "Orders->Customers"]);
    expect(titles.every((title) => title.namespaceURI !== "http://www.w3.org/2000/svg")).toBe(true);
    expect(elementRefOf(root.querySelector("g.node")!, "table")).toEqual({ kind: "table", id: "Orders" });
    expect(elementsOf(root, { kind: "table", id: "Orders" })).toEqual([root.querySelector("g.node")]);
  });

  it("puts the label under the element, inside the window", () => {
    const element = document.createElement("div");
    const label = document.createElement("div");
    element.getBoundingClientRect = () => ({ left: 100, top: 200, right: 220, bottom: 320, width: 120, height: 120, x: 100, y: 200, toJSON: () => null });
    Object.defineProperty(label, "offsetHeight", { value: 24 });
    placeLabel(label, element);
    expect([label.style.left, label.style.top]).toEqual(["100px", "326px"]);
  });

  it("puts it above only when there is no room below", () => {
    const element = document.createElement("div");
    const label = document.createElement("div");
    element.getBoundingClientRect = () => ({ left: 100, top: 300, right: 220, bottom: window.innerHeight - 10, width: 120, height: 0, x: 100, y: 300, toJSON: () => null });
    Object.defineProperty(label, "offsetHeight", { value: 24 });
    placeLabel(label, element);
    expect(label.style.top).toBe("270px");
  });

  it("shows a row's tooltip under its whole table, as a table's own — for you and for a follower alike", () => {
    vi.useFakeTimers();
    const root = drawing();
    const table = root.querySelector("g.node")!;
    table.getBoundingClientRect = () => ({ left: 100, top: 200, right: 220, bottom: 320, width: 120, height: 120, x: 100, y: 200, toJSON: () => null });
    renderHook(() => useGraphvizFocus(root, "svg-1", ERD, "table"));
    hoverTrusted(root.querySelector("#a_fn0_1 text")!);
    act(() => vi.advanceTimersByTime(600));
    expect(document.querySelector<HTMLElement>("[data-own-tooltip]")!.style.top).toBe("326px");
    act(() => {
      putFocus("anna", annasFocus);
      setFollowTarget("anna");
    });
    act(() => vi.advanceTimersByTime(600));
    expect(document.querySelector<HTMLElement>("[data-follow-tooltip]")!.style.top).toBe("326px");
  });

  it("takes it off a drawing placed after the hook ran, as the viewer places its SVG", async () => {
    const root = drawing();
    renderHook(() => useGraphvizFocus(root, "svg-1", ERD, "table"));
    root.innerHTML = '<svg><g class="node"><title>Orders</title><g id="a_ft0_1"><a xlink:title="int"><text>int</text></a></g></g></svg>';
    await Promise.resolve();
    expect(root.querySelector("a")!.getAttribute("xlink:title")).toBeNull();
    expect(root.querySelector("a")!.getAttribute("data-tooltip")).toBe("int");
  });

  it("shows your own hover's tooltip as the app's label, drawn as a follower's is", () => {
    vi.useFakeTimers();
    const root = drawing();
    renderHook(() => useGraphvizFocus(root, "svg-1", ERD, "table"));
    hoverTrusted(root.querySelector("#a_fn0_1 text")!);
    expect(focusToSend(ERD).hover).toEqual({ kind: "row", id: "fn0_1" });
    act(() => vi.advanceTimersByTime(600));
    const own = document.querySelector<HTMLElement>("[data-own-tooltip]")!;
    const follower = document.querySelector<HTMLElement>("[data-follow-tooltip]")!;
    expect(own.style.display).toBe("block");
    expect(own.textContent).toBe("customer_id: str");
    const look = (label: HTMLElement) => [label.style.background, label.style.color, label.style.font, label.style.padding, label.style.borderRadius];
    expect(look(own)).toEqual(look(follower));
  });

  it("shows no label over a cell whose tooltip is blank", () => {
    vi.useFakeTimers();
    const root = drawing();
    root.querySelector("#a_fn0_1 a")!.setAttribute("xlink:title", " ");
    renderHook(() => useGraphvizFocus(root, "svg-1", ERD, "table"));
    hoverTrusted(root.querySelector("#a_fn0_1 text")!);
    act(() => vi.advanceTimersByTime(600));
    expect(document.querySelector<HTMLElement>("[data-own-tooltip]")!.style.display).toBe("none");
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

  it("opens the version picker while the person followed has it open, and reports your own (spec 038)", () => {
    const picker = renderHook(() => {
      const [own, setOwn] = useState(false);
      return { setOwn, shown: useShownPanel(own, setOwn, (panels) => panels.versions, (open) => ({ versions: open })) };
    });
    act(() => picker.result.current.setOwn(true));
    expect(focusToSend(ERD).panels.versions).toBe(true);
    act(() => {
      putFocus("anna", { ...annasFocus, panels: { ...annasFocus.panels, versions: false } });
      setFollowTarget("anna");
    });
    expect(picker.result.current.shown).toBe(false);
    act(() => putFocus("anna", { ...annasFocus, panels: { ...annasFocus.panels, versions: true } }));
    expect(picker.result.current.shown).toBe(true);
  });

  it("sends a change of the picker alone, as any change of what shows", () => {
    const shut = { ...annasFocus, panels: { ...annasFocus.panels, versions: false } };
    expect(sameFocus(shut, { ...shut, panels: { ...shut.panels, versions: true } })).toBe(false);
  });
});
