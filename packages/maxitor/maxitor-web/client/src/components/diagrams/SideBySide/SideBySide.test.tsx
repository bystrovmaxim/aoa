// src/components/diagrams/SideBySide/SideBySide.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SideBySide } from "@/components/diagrams/SideBySide";
import { useHalf, type Half } from "@/lib/half";

const half = (side: "a" | "b"): Half => ({ side, read: { source: side, key: "" }, name: `v-${side}` });

function Shows() {
  const shown = useHalf();
  return <div data-testid="drawn">{`${shown?.side} ${shown?.phone ? "phone" : "desk"}`}</div>;
}

function atWidth(phone: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({ matches: phone && query.includes("max-width"), media: query, addEventListener: () => undefined, removeEventListener: () => undefined, addListener: () => undefined, removeListener: () => undefined }));
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Side by side", () => {
  it("stands A on the left of B on a desk, each told it is a half", () => {
    atWidth(false);
    render(<SideBySide a={half("a")} b={half("b")}><Shows /></SideBySide>);
    expect(screen.getAllByTestId("drawn").map((each) => each.textContent)).toEqual(["a desk", "b desk"]);
  });

  it("opens one diagram on B on a phone, and flips it to A", () => {
    atWidth(true);
    render(<SideBySide a={half("a")} b={half("b")}><Shows /></SideBySide>);
    expect(screen.getAllByTestId("drawn").map((each) => each.textContent)).toEqual(["b phone"]);
    fireEvent.click(screen.getByRole("radio", { name: "A" }));
    expect(screen.getAllByTestId("drawn").map((each) => each.textContent)).toEqual(["a phone"]);
  });
});
