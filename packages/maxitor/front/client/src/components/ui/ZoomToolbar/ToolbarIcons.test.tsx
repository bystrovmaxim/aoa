import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setHoverCardsOn } from "@/lib/hoverCardsOn";
import { CollapseAllButton, HoverCardsButton } from "./ToolbarIcons";

afterEach(() => {
  cleanup();
  setHoverCardsOn(true);
});

describe("the toolbar's icons", () => {
  it("names what the collapse button will do", () => {
    const onClick = vi.fn();
    const { rerender } = render(<CollapseAllButton collapsed={false} onClick={onClick} />);
    fireEvent.click(screen.getByLabelText("Collapse all tables"));
    expect(onClick).toHaveBeenCalledOnce();
    rerender(<CollapseAllButton collapsed onClick={onClick} />);
    expect(screen.getByLabelText("Expand all tables")).toBeTruthy();
  });

  it("switches the cards, on at first", () => {
    render(<HoverCardsButton />);
    const button = screen.getByTestId("hover-cards");
    expect(button.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(button);
    expect(button.getAttribute("aria-pressed")).toBe("false");
    expect(button.getAttribute("aria-label")).toBe("Show cards on hover");
  });
});
