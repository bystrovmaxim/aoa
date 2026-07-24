// packages/aoa-client-js/src/dynamic-api.test.ts
import { describe, expect, it } from "vitest";

import { buildDynamicGateApi, type DynamicApiNode } from "./dynamic-api.ts";
import { AoaEngine } from "./engine.ts";
import { buildLayout, type LayoutEndpoint } from "./path-layout.ts";
import type { ResolveResponse } from "./types.ts";

function ep(method: string, path: string): LayoutEndpoint {
  return { operation: `${method} ${path}`, method, path, baseName: "Unused" };
}

function fakeEngine(resultBody: ResolveResponse, captureRequest?: (body: unknown) => void): AoaEngine {
  const fetchImpl = (async (_url: string, init: RequestInit) => {
    captureRequest?.(JSON.parse(init.body as string));
    return new Response(JSON.stringify(resultBody), { status: 200, headers: { "content-type": "application/json" } });
  }) as typeof fetch;
  return new AoaEngine({ transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:1" } });
}

function asPrimitive(node: DynamicApiNode) {
  return node as { verdict: (params: unknown) => Promise<unknown>; can: (params: unknown) => Promise<boolean> };
}

function asNamespace(node: DynamicApiNode): Record<string, DynamicApiNode> {
  return node as Record<string, DynamicApiNode>;
}

describe("buildDynamicGateApi", () => {
  it("builds a real, working Primitive at the bracket key", async () => {
    const engine = fakeEngine({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    const api = buildDynamicGateApi(buildLayout([ep("POST", "/actions/cancel-order")]), engine);
    const primitive = asPrimitive(api.post!["/actions/cancel-order"]!);
    await expect(primitive.can({ order_id: 7 })).resolves.toBe(true);
  });

  it("omits a method bucket entirely when it has zero endpoints", () => {
    const api = buildDynamicGateApi(buildLayout([ep("POST", "/actions/cancel-order")]), fakeEngine({ version: 1, results: [] }));
    expect(api.get).toBeUndefined();
  });

  it("shares the exact same Primitive instance between a single-segment alias and its bracket key", () => {
    const engine = fakeEngine({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    const api = buildDynamicGateApi(buildLayout([ep("GET", "/orders")]), engine);
    expect(api.get!.orders).toBe(api.get!["/orders"]);
  });

  it("shares the exact same Primitive instance across a nested multi-segment alias", () => {
    const engine = fakeEngine({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    const api = buildDynamicGateApi(buildLayout([ep("GET", "/actions/ping")]), engine);
    const actionsNs = asNamespace(api.get!.actions!);
    expect(actionsNs.ping).toBe(api.get!["/actions/ping"]);
  });

  it("gives no alias at all to a hyphenated path, only the bracket key", () => {
    const engine = fakeEngine({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    const api = buildDynamicGateApi(buildLayout([ep("POST", "/actions/cancel-order")]), engine);
    expect(api.post!.actions).toBeUndefined();
    expect(api.post!["/actions/cancel-order"]).toBeDefined();
  });

  it("resolves a branch/leaf collision the same way the static renderer does: bracket key survives, alias leaf is demoted to a pure namespace", () => {
    const engine = fakeEngine({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    const api = buildDynamicGateApi(buildLayout([ep("GET", "/admin"), ep("GET", "/admin/settings")]), engine);
    expect(api.get!["/admin"]).toBeDefined();
    const adminNode = api.get!.admin;
    // "admin" is a pure namespace now (demoted) -- not itself a callable Primitive.
    expect(adminNode).not.toBe(api.get!["/admin"]);
    expect(asNamespace(adminNode!).settings).toBe(api.get!["/admin/settings"]);
  });

  it("each distinct endpoint gets its own real, independently-working Primitive making real resolve() calls with the right operation", async () => {
    let captured: unknown;
    const engine = fakeEngine({ version: 1, results: [{ kind: "AllowedVerdict" }] }, (body) => {
      captured = body;
    });
    const api = buildDynamicGateApi(buildLayout([ep("POST", "/actions/cancel-order"), ep("GET", "/actions/ping")]), engine);
    await asPrimitive(api.get!["/actions/ping"]!).can({});
    expect((captured as { items: Array<{ operation: string }> }).items[0]?.operation).toBe("GET /actions/ping");
  });
});
