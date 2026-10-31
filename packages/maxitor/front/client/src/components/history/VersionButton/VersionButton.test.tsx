// src/components/history/VersionButton/VersionButton.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { VersionButton } from "./VersionButton";

afterEach(cleanup);

describe("the version button", () => {
  it("names one version alone", () => {
    render(<VersionButton name="0.11.0 · #147" open={false} onClick={() => undefined} />);
    expect(screen.getByRole("button").getAttribute("aria-label")).toBe("Version: 0.11.0 · #147");
    expect(screen.queryByTestId("diff-counts")).toBeNull();
  });

  it("in Diff carries the diagram's counts, each with its sign (spec 038, FR-025)", () => {
    render(<VersionButton name="A 0.8.0 → B 0.9.0" open={false} onClick={() => undefined} counts={{ added: 15, removed: 1, changed: 3 }} />);
    expect(screen.getByTestId("diff-counts").textContent).toBe("+15−1~3");
    expect(screen.getByRole("button").getAttribute("aria-label")).toBe("Versions: A 0.8.0 → B 0.9.0, +15 −1 ~3");
  });

  it("says \"no changes\" when the diagram has none (FR-026)", () => {
    render(<VersionButton name="A 0.8.0 → B 0.9.0" open={false} onClick={() => undefined} counts={{ added: 0, removed: 0, changed: 0 }} />);
    expect(screen.getByTestId("diff-counts").textContent).toBe("no changes");
  });

  it("names the range without counts on a diagram that does not count", () => {
    render(<VersionButton name="A 0.8.0 → B 0.9.0" open={false} onClick={() => undefined} counts={null} />);
    expect(screen.getByText("A 0.8.0 → B 0.9.0")).toBeTruthy();
    expect(screen.queryByTestId("diff-counts")).toBeNull();
  });

  it("on a phone cuts the name, never the counts (spec 038, FR-033)", () => {
    render(<VersionButton name="A #128 → B #129" open={false} onClick={() => undefined} counts={{ added: 15, removed: 1, changed: 3 }} compact />);
    expect(getComputedStyle(screen.getByRole("button")).maxWidth).toBe("100%");
    expect(screen.getByTestId("version-name").style.textOverflow).toBe("ellipsis");
    expect(screen.getByTestId("diff-counts").style.flexShrink).toBe("0");
  });

  it("carries the step arrows in its pill, each stepping one version, greyed out at the end of the track", () => {
    const onStep = vi.fn();
    render(<VersionButton name="A #2 → B #3" open={false} onClick={() => undefined} onStep={onStep} canStep={{ older: true, newer: false }} />);
    fireEvent.click(screen.getByRole("button", { name: "Older version" }));
    expect(onStep).toHaveBeenCalledWith(-1);
    expect((screen.getByRole("button", { name: "Newer version" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("group", { name: "Versions" }).contains(screen.getByRole("button", { name: /^Versions?:/ }))).toBe(true);
  });

  it("tells the keys when one reaches for an arrow", async () => {
    render(<VersionButton name="#2" open={false} onClick={() => undefined} onStep={() => undefined} />);
    fireEvent.mouseOver(screen.getByRole("button", { name: "Older version" }));
    expect((await screen.findByRole("tooltip")).textContent).toBe("Older version⇧←");
  });

  it("gives each arrow a 44 px target on a phone, and no key hint", () => {
    render(<VersionButton name="#2" open={false} onClick={() => undefined} onStep={() => undefined} compact />);
    const arrow = screen.getByRole("button", { name: "Newer version" });
    expect(getComputedStyle(arrow).minWidth).toBe("44px");
    fireEvent.mouseOver(arrow);
    expect(screen.queryByRole("tooltip")).toBeNull();
  });
});
