// packages/aoa-client-js/src/path-layout.test.ts
import { describe, expect, it } from "vitest";

import { buildLayout, type LayoutEndpoint } from "./path-layout.ts";

function ep(method: string, path: string, baseName: string): LayoutEndpoint {
  return { operation: `${method} ${path}`, method, path, baseName };
}

describe("buildLayout", () => {
  it("groups endpoints by lowercased HTTP method", () => {
    const layout = buildLayout([ep("POST", "/actions/cancel-order", "CancelOrder"), ep("GET", "/actions/ping", "Ping")]);
    expect(layout.map((l) => l.method)).toEqual(["post", "get"]);
  });

  it("bracketEntries always includes every endpoint for that method, clean or not", () => {
    const layout = buildLayout([ep("POST", "/actions/cancel-order", "CancelOrder"), ep("POST", "/actions/simple", "Simple")]);
    expect(layout[0]?.bracketEntries.map((e) => e.path)).toEqual(["/actions/cancel-order", "/actions/simple"]);
  });

  it("gives a single-segment clean path a one-level alias", () => {
    const layout = buildLayout([ep("GET", "/orders", "Orders")]);
    const root = layout[0]!.aliasRoot;
    expect(root.children.orders?.endpoint?.baseName).toBe("Orders");
    expect(root.children.orders?.children).toEqual({});
  });

  it("gives a multi-segment clean path a nested alias chain", () => {
    const layout = buildLayout([ep("GET", "/actions/ping", "Ping")]);
    const root = layout[0]!.aliasRoot;
    expect(root.children.actions?.endpoint).toBeNull();
    expect(root.children.actions?.children.ping?.endpoint?.baseName).toBe("Ping");
  });

  it("gives no alias at all to a path with a hyphenated segment", () => {
    const layout = buildLayout([ep("POST", "/actions/cancel-order", "CancelOrder")]);
    const root = layout[0]!.aliasRoot;
    expect(root.children.actions).toBeUndefined();
  });

  it("gives no alias at all to a path with a {param} segment", () => {
    const layout = buildLayout([ep("GET", "/orders/{order_id}", "OrderById")]);
    const root = layout[0]!.aliasRoot;
    expect(Object.keys(root.children)).toEqual([]);
  });

  it("gives no alias to a path with a dotted segment", () => {
    const layout = buildLayout([ep("GET", "/client-manifest.json", "Manifest")]);
    expect(Object.keys(layout[0]!.aliasRoot.children)).toEqual([]);
  });

  it("mixes clean and dirty siblings under the same method correctly", () => {
    const layout = buildLayout([ep("POST", "/actions/cancel-order", "CancelOrder"), ep("POST", "/actions/simple", "Simple")]);
    const root = layout[0]!.aliasRoot;
    expect(root.children.actions?.children.simple?.endpoint?.baseName).toBe("Simple");
    // cancel-order contributed nothing -- "actions" has exactly one clean child.
    expect(Object.keys(root.children.actions?.children ?? {})).toEqual(["simple"]);
  });

  it("resolves a branch/leaf collision by demoting only the shorter path, leaving the deeper one intact", () => {
    const layout = buildLayout([ep("GET", "/admin", "AdminRoot"), ep("GET", "/admin/settings", "AdminSettings")]);
    const root = layout[0]!.aliasRoot;
    expect(root.children.admin?.endpoint).toBeNull(); // demoted: would otherwise be both leaf and branch
    expect(root.children.admin?.children.settings?.endpoint?.baseName).toBe("AdminSettings");
  });

  it("does not let a collision in one method bucket affect a same-shaped path in a different method", () => {
    const layout = buildLayout([ep("GET", "/admin", "AdminRootGet"), ep("GET", "/admin/settings", "AdminSettingsGet"), ep("POST", "/admin", "AdminRootPost")]);
    const postLayout = layout.find((l) => l.method === "post")!;
    // POST /admin has no sibling /admin/settings under POST, so it is not a collision there.
    expect(postLayout.aliasRoot.children.admin?.endpoint?.baseName).toBe("AdminRootPost");
  });

  it("treats a bare root path ('/') as having no segments to alias", () => {
    const layout = buildLayout([ep("GET", "/", "Root")]);
    expect(Object.keys(layout[0]!.aliasRoot.children)).toEqual([]);
  });

  it("keeps method bucket order as first-encountered, matching manifest registration order", () => {
    const layout = buildLayout([ep("GET", "/a", "A"), ep("POST", "/b", "B"), ep("GET", "/c", "C"), ep("DELETE", "/d", "D")]);
    expect(layout.map((l) => l.method)).toEqual(["get", "post", "delete"]);
  });
});
