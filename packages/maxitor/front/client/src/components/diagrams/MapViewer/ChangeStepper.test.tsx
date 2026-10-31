// src/components/diagrams/MapViewer/ChangeStepper.test.tsx
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setChangeStepping, type ChangeEntry, type ChangeStepping } from "@/lib/changeStepping";
import { clearFocus, focusToSend, putFocus, setFollowTarget, type Panels } from "@/rooms/focusStore";
import { ChangeStepper } from "./ChangeStepper";

const ENTRIES: ChangeEntry[] = [
  { key: "a", title: "Order", detail: "Entity", status: "added", group: "Sales" },
  { key: "b", title: "Invoice", detail: "Entity", status: "changed", group: "Sales" },
  { key: "c", title: "Stock", detail: "Action", status: "removed", group: "Store" },
];

function stepping(more: Partial<ChangeStepping> = {}): ChangeStepping {
  return { entries: ENTRIES, position: null, card: false, go: () => undefined, mirror: () => undefined, ...more };
}

afterEach(() => {
  cleanup();
  act(() => {
    setChangeStepping(null);
    clearFocus();
  });
});

describe("the change stepper", () => {
  it("shows nothing while no diagram steps, or with nothing to step through", () => {
    render(<ChangeStepper />);
    expect(screen.queryByTestId("change-stepper")).toBeNull();
    act(() => setChangeStepping(stepping({ entries: [] })));
    expect(screen.queryByTestId("change-stepper")).toBeNull();
  });

  it("says the total before the first step, and the position after", () => {
    render(<ChangeStepper />);
    act(() => setChangeStepping(stepping()));
    expect(screen.getByTestId("change-position").textContent).toBe("3 changes");
    act(() => setChangeStepping(stepping({ position: 1 })));
    expect(screen.getByTestId("change-position").textContent).toBe("2 of 3");
  });

  it("goes to the next change and wraps around at both ends", () => {
    const go = vi.fn();
    render(<ChangeStepper />);
    act(() => setChangeStepping(stepping({ position: 2, go })));
    fireEvent.click(screen.getByLabelText("Next change"));
    act(() => setChangeStepping(stepping({ position: 0, go })));
    fireEvent.click(screen.getByLabelText("Previous change"));
    expect(go.mock.calls).toEqual([[0], [2]]);
  });

  it("opens the list by group, and a pick goes to that change and closes it", () => {
    const go = vi.fn();
    render(<ChangeStepper />);
    act(() => setChangeStepping(stepping({ go })));
    fireEvent.click(screen.getByLabelText("Changes: 3 changes"));
    expect(screen.getByText("Sales")).toBeTruthy();
    expect(screen.getByText("Store")).toBeTruthy();
    fireEvent.click(screen.getByText("Stock"));
    expect(go).toHaveBeenCalledWith(2);
    expect(screen.queryByText("Sales")).toBeNull();
  });

  it("opens with its rows however far it was scrolled the time before", () => {
    const entries = Array.from({ length: 200 }, (_, index) => ({ ...ENTRIES[0], key: `k${index}`, title: `Change ${index}` }));
    render(<ChangeStepper />);
    act(() => setChangeStepping(stepping({ entries, position: 0 })));
    fireEvent.click(screen.getByLabelText("Changes: 1 of 200"));
    fireEvent.scroll(screen.getByTestId("change-list"), { target: { scrollTop: 4500 } });
    expect(screen.getByText("Change 150")).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Changes: 1 of 200"));
    fireEvent.click(screen.getByLabelText("Changes: 1 of 200"));
    expect(screen.getByText("Change 0")).toBeTruthy();
  });

  it("draws only the rows that can show", () => {
    const entries = Array.from({ length: 2000 }, (_, index) => ({ ...ENTRIES[0], key: `k${index}`, title: `Change ${index}` }));
    render(<ChangeStepper />);
    act(() => setChangeStepping(stepping({ entries })));
    fireEvent.click(screen.getByLabelText("Changes: 2000 changes"));
    expect(screen.getByTestId("change-list").querySelectorAll("button").length).toBeLessThan(40);
  });

  it("reports the list for a follower", () => {
    render(<ChangeStepper />);
    act(() => setChangeStepping(stepping({ position: 1, card: true })));
    fireEvent.click(screen.getByLabelText("Changes: 2 of 3"));
    expect(focusToSend("page").panels.changes).toMatchObject({ open: true, at: "b", card: true });
  });
});

describe("the change stepper of a follower", () => {
  const PANELS: Panels = { sidebar: [], filter: null, legend: false, versions: false, track: null, changes: { open: true, at: "c", card: true, offset: 0 } };

  function following(mirror: ChangeStepping["mirror"], go: ChangeStepping["go"] = () => undefined) {
    render(<ChangeStepper />);
    act(() => {
      setChangeStepping(stepping({ mirror, go }));
      setFollowTarget("anna");
      putFocus("anna", { page: "page", hover: null, tooltip: null, selection: null, panels: PANELS });
    });
  }

  it("shows the followed person's list and stands where they stand", () => {
    const mirror = vi.fn();
    following(mirror);
    expect(screen.getByTestId("change-list")).toBeTruthy();
    expect(mirror).toHaveBeenLastCalledWith(2, true);
  });

  it("does not act on the follower's own clicks", () => {
    const go = vi.fn();
    following(() => undefined, go);
    fireEvent.click(screen.getByText("Stock"));
    fireEvent.click(screen.getByLabelText("Next change"));
    expect(go).not.toHaveBeenCalled();
  });

  it("marks the list and the pill as frames, so a pointer lands on the same row", () => {
    following(() => undefined);
    expect(screen.getByTestId("change-list").getAttribute("data-pointer-frame")).toBe("changes");
    expect(screen.getByTestId("change-stepper").getAttribute("data-pointer-frame")).toBe("change-steps");
  });
});
