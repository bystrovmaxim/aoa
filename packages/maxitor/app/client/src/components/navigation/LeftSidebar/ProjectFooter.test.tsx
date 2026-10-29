// src/components/navigation/LeftSidebar/ProjectFooter.test.tsx
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PROJECT_URL, ProjectFooter } from "./ProjectFooter";

beforeEach(() => {
  // A version no build of Maxitor has had: the footer can only show it by asking the server.
  vi.stubGlobal("fetch", async (input: RequestInfo | URL) =>
    String(input).endsWith("/api/meta/app-info")
      ? ({ ok: true, status: 200, json: async () => ({ version: "9.8.7-test", build: "abc" }) } as Response)
      : ({ ok: false, status: 404, json: async () => ({}) } as Response),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("the left panel's footer", () => {
  it("links to the project and shows the version the server runs", async () => {
    render(<ProjectFooter collapsed={false} />);
    expect(await screen.findByText("9.8.7-test")).toBeTruthy();
    expect(screen.getByText("Maxitor")).toBeTruthy();
    const link = screen.getByRole("link", { name: "Maxitor on GitHub" });
    expect(link.getAttribute("href")).toBe(PROJECT_URL);
    expect(link.getAttribute("target")).toBe("_blank");
  });

  it("keeps only the mark on the collapsed rail", async () => {
    render(<ProjectFooter collapsed />);
    expect(screen.getByRole("link", { name: "Maxitor on GitHub" })).toBeTruthy();
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.queryByText("Maxitor")).toBeNull();
    expect(screen.queryByText("9.8.7-test")).toBeNull();
  });
});
