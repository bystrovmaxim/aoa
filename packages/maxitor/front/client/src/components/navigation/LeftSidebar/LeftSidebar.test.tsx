// src/components/navigation/LeftSidebar/LeftSidebar.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { NodeRow, SidebarPayload } from "@/model/sidebar";
import { SidebarCollapseProvider } from "@/components/layout/MainLayout/SidebarCollapseContext";
import { LeftSidebar } from "./LeftSidebar";

afterEach(cleanup);

const domain = (id: string, only?: "a" | "b"): NodeRow => ({ id, parent_id: "domains", label: `${id}Domain`, type: "domain", only });
const panel = (domains: NodeRow[]): SidebarPayload => ({
  level1_nodes: [{ id: "domains", parent_id: null, label: "Domains", type: "section" }],
  level2_diagrams: [],
  level2_nodes: domains,
  level3_diagrams: domains.map((each) => ({ id: `${each.id}:erd`, parent_id: each.id, label: "Entity domain view", type: "erd_domain", only: each.only })),
});

function show(sidebar: SidebarPayload) {
  render(
    <SidebarCollapseProvider>
      <LeftSidebar
        diagram={null}
        onSelectDiagram={() => undefined}
        sidebar={sidebar}
        onLoaded={() => undefined}
        onReset={() => undefined}
        source="http://service"
        onReloadFromService={() => undefined}
        reloading={false}
        reloadError={null}
        busy={false}
      />
    </SidebarCollapseProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: /Domains/ }));
}

describe("the left panel in Diff (spec 038, FR-032)", () => {
  it("marks a page only in B with + and one only in A with −", () => {
    show(panel([domain("orders"), domain("billing", "b"), domain("legacy", "a")]));
    expect(screen.getByLabelText("only in B").textContent).toBe("+");
    expect(screen.getByLabelText("only in A").textContent).toBe("−");
    expect(screen.getAllByTestId("only-mark")).toHaveLength(2);
  });

  it("marks nothing in One", () => {
    show(panel([domain("orders"), domain("billing")]));
    expect(screen.queryByTestId("only-mark")).toBeNull();
  });
});

describe("an empty domain (spec 041, FR-027a)", () => {
  it("stays in the panel, dim, and a domain with diagrams is not dim", () => {
    const sidebar = panel([domain("orders"), domain("empty")]);
    show({ ...sidebar, level3_diagrams: sidebar.level3_diagrams.filter((row) => row.parent_id === "orders") });
    expect(screen.getAllByTestId("empty-row").map((row) => row.textContent)).toEqual(["emptyDomain"]);
  });
});
