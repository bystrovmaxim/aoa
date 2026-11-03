// src/lib/topCentre.test.tsx
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { RoomBanner } from "@/rooms/RoomBar/RoomBanner";
import { useReserveTopCentre } from "./topCentre";

afterEach(cleanup);

function Pill({ px }: { px: number }) {
  useReserveTopCentre(px);
  return null;
}

const banner = { kind: "info" as const, text: "#381 was merged", open: false };

describe("the top centre of the canvas", () => {
  it("leaves a banner at its place when nothing stands there", () => {
    render(<RoomBanner banner={banner} onOpenRoom={() => undefined} onDismiss={() => undefined} />);
    expect(getComputedStyle(screen.getByRole("alert")).top).toBe("12px");
  });

  it("puts a banner below what stands there, and back when it goes", () => {
    const { rerender } = render(
      <>
        <Pill px={48} />
        <RoomBanner banner={banner} onOpenRoom={() => undefined} onDismiss={() => undefined} />
      </>,
    );
    expect(getComputedStyle(screen.getByRole("alert")).top).toBe("60px");
    rerender(<RoomBanner banner={banner} onOpenRoom={() => undefined} onDismiss={() => undefined} />);
    expect(getComputedStyle(screen.getByRole("alert")).top).toBe("12px");
  });
});
