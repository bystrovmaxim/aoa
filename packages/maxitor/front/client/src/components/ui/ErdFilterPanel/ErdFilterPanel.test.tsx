// src/components/ui/ErdFilterPanel/ErdFilterPanel.test.tsx
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ErdFilterPanel, type ErdFilterRow } from "@/components/ui/ErdFilterPanel";

const narrow = vi.hoisted(() => ({ value: false }));
vi.mock("@mui/material/useMediaQuery", () => ({ default: () => narrow.value }));

const row = (key: string, label = key): ErdFilterRow => ({ key, label, iconSrc: "data:,", on: true });
const domains = [row("Billing"), row("EntityProjectionDemoDomainWithAVeryLongName")];
const kinds = [row("core", "Core"), row("assoc", "Association")];

function renderPanel(kindRows = kinds) {
  const onToggleDomain = vi.fn();
  const onToggleKind = vi.fn();
  render(<ErdFilterPanel domainRows={domains} kindRows={kindRows} onToggleDomain={onToggleDomain} onToggleKind={onToggleKind} />);
  return { onToggleDomain, onToggleKind };
}

const header = (name: string) => screen.getByRole("button", { name, expanded: undefined });

afterEach(() => {
  cleanup();
  narrow.value = false;
});

describe("ErdFilterPanel", () => {
  it("is exactly 148 px wide whatever its labels, and has no panel title on a wide screen", () => {
    renderPanel();
    const panel = screen.getByTestId("erd-filter-panel");

    const style = getComputedStyle(panel);
    expect(style.width).toBe("148px");
    expect(style.minWidth).toBe("148px");
    expect(style.maxWidth).toBe("148px");
    expect(screen.queryByText("Filter")).toBeNull();
  });

  it("opens Domains on mount with Kinds folded, and lets only one section be open", () => {
    renderPanel();
    const domainsHeader = header("Domains");
    const kindsHeader = header("Kinds");
    expect(domainsHeader.getAttribute("aria-expanded")).toBe("true");
    expect(kindsHeader.getAttribute("aria-expanded")).toBe("false");
    // The folded section's rows are not on screen at all.
    expect(screen.getByRole("button", { name: "Billing" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Association" })).toBeNull();

    fireEvent.click(kindsHeader);
    expect(header("Domains").getAttribute("aria-expanded")).toBe("false");
    expect(header("Kinds").getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("button", { name: "Association" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Billing" })).toBeNull();

    fireEvent.click(header("Domains"));
    expect(header("Kinds").getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(header("Domains"));
    expect(header("Domains").getAttribute("aria-expanded")).toBe("false");
    expect(header("Kinds").getAttribute("aria-expanded")).toBe("false");
  });

  it("shows only the chevron and the name in a section header", () => {
    renderPanel();

    expect(header("Domains").textContent).toBe("Domains");
  });

  it("toggles a row through its callback", () => {
    const { onToggleDomain, onToggleKind } = renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "Billing" }));
    fireEvent.click(header("Kinds"));
    fireEvent.click(screen.getByRole("button", { name: "Core" }));

    expect(onToggleDomain).toHaveBeenCalledWith("Billing");
    expect(onToggleKind).toHaveBeenCalledWith("core");
  });

  it("gives a cut label a tooltip and a fitting one none", async () => {
    renderPanel();
    const [fits, cut] = screen.getAllByTestId("erd-filter-label");
    Object.defineProperty(fits, "scrollWidth", { value: 40 });
    Object.defineProperty(fits, "clientWidth", { value: 100 });
    Object.defineProperty(cut, "scrollWidth", { value: 300 });
    Object.defineProperty(cut, "clientWidth", { value: 100 });

    fireEvent.mouseEnter(fits);
    fireEvent.mouseOver(fits);
    expect(screen.queryByRole("tooltip")).toBeNull();

    fireEvent.mouseEnter(cut);
    fireEvent.mouseOver(cut);
    expect(await screen.findByRole("tooltip")).toBeTruthy();
    expect(screen.getByRole("tooltip").textContent).toBe("EntityProjectionDemoDomainWithAVeryLongName");
  });

  it("has no Kinds section when the graph has one kind", () => {
    renderPanel([row("core", "Core")]);

    expect(screen.queryByRole("button", { name: "Kinds" })).toBeNull();
  });

  it("stops above the zoom toolbar and keeps the wheel to itself", () => {
    renderPanel();
    const panel = screen.getByTestId("erd-filter-panel");
    const outside = vi.fn();
    panel.parentElement!.addEventListener("wheel", outside);

    fireEvent.wheel(panel);

    expect(getComputedStyle(panel).maxHeight).toBe("calc(100% - 68px)");
    expect(getComputedStyle(panel).overflowY).toBe("auto");
    expect(outside).not.toHaveBeenCalled();
  });

  it("starts as a Filter pill on a narrow screen and opens without the word Filter inside", () => {
    narrow.value = true;
    renderPanel();

    const pill = screen.getByRole("button", { name: "Show filter" });
    expect(pill.textContent).toBe("Filter");
    fireEvent.click(pill);

    const panel = screen.getByTestId("erd-filter-panel");
    expect(within(panel).queryByText("Filter")).toBeNull();
    expect(within(panel).getByRole("button", { name: "Hide filter" }).parentElement).toBe(header("Domains").parentElement);
  });

  it("dims the name of a row with nothing of it on screen, and leaves it on (spec 038)", () => {
    render(<ErdFilterPanel domainRows={[row("Billing"), { ...row("Gone"), absent: true }]} kindRows={kinds} onToggleDomain={() => undefined} onToggleKind={() => undefined} />);
    const label = (name: string) => within(screen.getByRole("button", { name })).getByTestId("erd-filter-label");
    expect(getComputedStyle(label("Gone")).opacity).toBe("0.4");
    expect(getComputedStyle(label("Billing")).opacity).toBe("1");
    expect(screen.getByRole("button", { name: "Gone" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("lists the kinds of change in a Changes section and toggles them through its callback", () => {
    const onToggleChange = vi.fn();
    render(<ErdFilterPanel domainRows={domains} kindRows={kinds} onToggleDomain={() => undefined} onToggleKind={() => undefined} changeRows={[row("added", "Added"), row("unchanged", "Unchanged")]} onToggleChange={onToggleChange} />);
    fireEvent.click(header("Changes"));
    fireEvent.click(screen.getByRole("button", { name: "Added" }));
    expect(onToggleChange).toHaveBeenCalledWith("added");
  });

  it("puts the gear shift at its foot, one point per section in their order, below the panel's one divider", () => {
    const onPaint = vi.fn();
    render(
      <ErdFilterPanel domainRows={domains} kindRows={kinds} onToggleDomain={() => undefined} onToggleKind={() => undefined} changeRows={[row("added", "Added")]} onToggleChange={() => undefined} paint={{ source: "changes", onPaint }} />,
    );
    const points = screen.getAllByRole("radio");
    expect(points.map((point) => point.getAttribute("aria-label"))).toEqual(["Paint by Domains", "Paint by Kinds", "Paint by Changes"]);
    expect(points[2].getAttribute("aria-checked")).toBe("true");
    fireEvent.click(points[0]);
    expect(onPaint).toHaveBeenCalledWith("domains");
    const panel = screen.getByTestId("erd-filter-panel");
    const divided = [...panel.querySelectorAll("div")].filter((element) => /rgba\(0, ?0, ?0, ?0\.07\)/.test(getComputedStyle(element).borderTop));
    expect(divided).toHaveLength(1);
    expect(divided[0].contains(points[0])).toBe(true);
  });

  it("has no gear shift when there is one section to paint by", () => {
    render(<ErdFilterPanel domainRows={domains} kindRows={kinds.slice(0, 1)} onToggleDomain={() => undefined} onToggleKind={() => undefined} paint={{ source: "domains", onPaint: () => undefined }} />);
    expect(screen.queryByRole("radio")).toBeNull();
  });
});
