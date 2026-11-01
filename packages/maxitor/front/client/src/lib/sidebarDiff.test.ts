// src/lib/sidebarDiff.test.ts
import { describe, expect, it } from "vitest";
import type { NodeRow, SidebarPayload } from "@/model/sidebar";
import { changedDomains, mergeSidebars, narrowToChanges } from "./sidebarDiff";

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

  it("marks a changed lifecycle of both versions, and nothing for the lifecycle's own node", () => {
    const life = (id: string, only?: "a" | "b"): NodeRow => ({ id, parent_id: "d", label: id, type: "lifecycle_state_diagram", only });
    const panelOf = (rows: NodeRow[]) => ({ ...panel([]), level3_diagrams: rows });
    const compared = (nodes: Record<string, "changed">, edges: Record<string, "added"> = {}) => ({ counts: { nodes: { added: 0, removed: 0, changed: 0 }, edges: { added: 0, removed: 0, changed: 0 } }, nodes, edges });
    const rows = (result: ReturnType<typeof compared>) => mergeSidebars(panelOf([life("e:lifecycle:s"), life("e:lifecycle:t")]), panelOf([life("e:lifecycle:s"), life("e:lifecycle:t")]), result).level3_diagrams;
    expect(rows(compared({ "e:lifecycle:s:open": "changed" })).map((row) => row.changed)).toEqual([true, undefined]);
    expect(rows(compared({}, { "e:lifecycle:t:a|lifecycle_transition|e:lifecycle:t:b|a": "added" })).map((row) => row.changed)).toEqual([undefined, true]);
    expect(rows(compared({ "e:lifecycle:s": "changed" })).some((row) => row.changed)).toBe(false);
  });
});

describe("the panel narrowed to what holds a change (spec 044)", () => {
  const row = (id: string, type: string, parent_id: string | null, extra: object = {}) => ({ id, type, parent_id, label: id, ...extra });
  const sidebar = {
    level1_nodes: [],
    level2_diagrams: [row("graph", "graph", "apps")],
    level2_nodes: [row("d.Calm", "domain", "domains"), row("d.Busy", "domain", "domains"), row("d.New", "domain", "domains", { only: "b" }), row("d.Life", "domain", "domains")],
    level3_diagrams: [
      row("erd-calm", "erd_domain", "d.Calm"),
      row("erd-busy", "erd_domain", "d.Busy"),
      row("uc-busy", "use_case_domain", "d.Busy"),
      row("life", "lifecycle_state_diagram", "d.Life", { changed: true }),
      row("life-calm", "lifecycle_state_diagram", "d.Calm"),
    ],
  } as unknown as SidebarPayload;
  const changed = { erd: new Set(["d.Busy"]), useCase: new Set<string>() };

  it("leaves what changed and the domains over it, and a domain one version has", () => {
    const narrow = narrowToChanges(sidebar, changed);
    expect(narrow.level3_diagrams.map((each) => each.id)).toEqual(["erd-busy", "life"]);
    expect(narrow.level2_nodes.map((each) => each.id)).toEqual(["d.Busy", "d.New", "d.Life"]);
  });

  it("keeps the diagrams of all domains", () => {
    expect(narrowToChanges(sidebar, changed).level2_diagrams).toHaveLength(1);
  });

  it("finds a changed domain from a table, a row, a line and a use case", () => {
    const bundle = (entities: object[], relations: object[] = []) => ({ domains: { x: { entities, relations } }, domain_qualifiers: { x: "d.X" } }) as never;
    const noUseCases = { actions: [], roles: [], edges: [] } as never;
    expect(changedDomains(bundle([{ id: "t", diff: "changed" }]), noUseCases).erd.has("d.X")).toBe(true);
    expect(changedDomains(bundle([{ id: "t", fields: [{ name: "f", diff: "added" }] }]), noUseCases).erd.has("d.X")).toBe(true);
    expect(changedDomains(bundle([{ id: "t" }], [{ diff: "removed" }]), noUseCases).erd.has("d.X")).toBe(true);
    expect(changedDomains(bundle([{ id: "t", diff: "unchanged" }]), noUseCases).erd.size).toBe(0);
    expect(changedDomains(bundle([]), { actions: [{ id: "a", domain_id: "d.Y", diff: "added" }], roles: [], edges: [] } as never).useCase.has("d.Y")).toBe(true);
  });
});
