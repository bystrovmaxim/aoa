// src/lib/sidebarDiff.test.ts
import { describe, expect, it } from "vitest";
import type { NodeRow, SidebarPayload } from "@/model/sidebar";
import { mergeSidebars } from "./sidebarDiff";

const domain = (id: string, label = id): NodeRow => ({ id, parent_id: "domains", label, type: "domain" });
const erd = (id: string): NodeRow => ({ id: `${id}:erd`, parent_id: id, label: "Entity domain view", type: "erd_domain" });
const panel = (domains: NodeRow[]): SidebarPayload => ({
  level1_nodes: [{ id: "domains", parent_id: null, label: "Domains", type: "section" }],
  level2_diagrams: [],
  level2_nodes: domains,
  level3_diagrams: domains.map((each) => erd(each.id)),
});

describe("the left panel of two versions", () => {
  it("lists every page of either once, B's in B's order then A's alone, marked by the side it is in", () => {
    const merged = mergeSidebars(panel([domain("orders"), domain("legacy")]), panel([domain("orders"), domain("billing")]));
    expect(merged.level2_nodes.map((row) => [row.id, row.only])).toEqual([
      ["orders", undefined],
      ["billing", "b"],
      ["legacy", "a"],
    ]);
    expect(merged.level3_diagrams.map((row) => [row.id, row.only])).toEqual([
      ["orders:erd", undefined],
      ["billing:erd", "b"],
      ["legacy:erd", "a"],
    ]);
    expect(merged.level1_nodes.map((row) => row.only)).toEqual([undefined]);
  });

  it("knows a page by what it opens, not by its label: two domains of one name stay two pages", () => {
    const merged = mergeSidebars(panel([domain("a.Orders", "Orders")]), panel([domain("b.Orders", "Orders")]));
    expect(merged.level2_nodes.map((row) => [row.id, row.only])).toEqual([
      ["b.Orders", "b"],
      ["a.Orders", "a"],
    ]);
  });

  it("keeps B's fingerprint: the tab reports the version it shows", () => {
    expect(mergeSidebars({ ...panel([]), fingerprint: "A" }, { ...panel([]), fingerprint: "B" }).fingerprint).toBe("B");
  });
});
