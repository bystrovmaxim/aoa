// packages/aoa-client-js/src/engine.test.ts
import { describe, expect, it } from "vitest";

import {
  AoaEngine,
  AoaResolveError,
  NetworkUnavailable,
  ProtocolError,
  Unauthorized,
  isRetryableCheckError,
} from "./engine.ts";
import type { ResolveResponse } from "./types.ts";

function fakeResponse(body: unknown, init?: { status?: number; contentType?: string | null }): Response {
  const headers: Record<string, string> = {};
  if (init?.contentType !== null) {
    headers["content-type"] = init?.contentType ?? "application/json";
  }
  const rawBody = typeof body === "string" ? body : JSON.stringify(body);
  return new Response(rawBody, { status: init?.status ?? 200, headers });
}

function makeEngine(
  fetchImpl: typeof fetch,
  transportOverrides?: Partial<{
    headers: Record<string, string>;
    generateTraceId: () => string;
    clock: () => number;
    cache: { ttlMs?: number };
    cachePartition: string;
  }>,
): AoaEngine {
  return new AoaEngine({
    transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:1", ...transportOverrides },
  });
}

const oneItem = [{ operation: "POST /actions/cancel-order", params: { order_id: 7 } }];

describe("AoaEngine.resolve -- happy path", () => {
  it("posts version+items to the right URL and returns results as-is", async () => {
    let capturedUrl = "";
    let capturedBody: unknown;
    const fetchImpl = (async (url: string, init: RequestInit) => {
      capturedUrl = url;
      capturedBody = JSON.parse(init.body as string);
      const body: ResolveResponse = { version: 1, results: [{ kind: "AllowedVerdict" }] };
      return fakeResponse(body);
    }) as typeof fetch;

    const results = await makeEngine(fetchImpl).resolve(oneItem);

    expect(capturedUrl).toBe("https://example.test/permissions/resolve");
    expect(capturedBody).toEqual({ version: 1, items: oneItem });
    expect(results).toEqual([{ kind: "AllowedVerdict" }]);
    expect(results[0].kind === "AllowedVerdict").toBe(true);
  });

  it("returns a mixed AllowedVerdict/FailErrorVerdict response as-is", async () => {
    const items = [
      { operation: "POST /actions/cancel-order", params: {} },
      { operation: "GET /actions/unknown", params: {} },
    ];
    const fetchImpl = (async () => {
      const body: ResolveResponse = {
        version: 1,
        results: [{ kind: "AllowedVerdict" }, { kind: "FailErrorVerdict", reason: "TIMEOUT" }],
      };
      return fakeResponse(body);
    }) as typeof fetch;

    const results = await makeEngine(fetchImpl).resolve(items);

    expect(results[0]).toEqual({ kind: "AllowedVerdict" });
    expect(results[1]).toEqual({ kind: "FailErrorVerdict", reason: "TIMEOUT" });
  });
});

describe("AoaEngine.resolve -- request-level failures", () => {
  it("throws NetworkUnavailable when fetchImpl itself throws", async () => {
    const engine = makeEngine(async () => {
      throw new Error("getaddrinfo ENOTFOUND");
    });
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(NetworkUnavailable);
  });

  it("throws Unauthorized on 401", async () => {
    const engine = makeEngine(async () => fakeResponse(null, { status: 401, contentType: null }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(Unauthorized);
  });

  it.each([500, 403, 418])("throws ProtocolError (not Unauthorized) on a non-401 error status %d", async (status) => {
    const engine = makeEngine(async () => fakeResponse(null, { status, contentType: null }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("ProtocolError on a non-401 status carries the status code in its message", async () => {
    const engine = makeEngine(async () => fakeResponse(null, { status: 500, contentType: null }));
    await expect(engine.resolve(oneItem)).rejects.toThrow("500");
  });
});

describe("AoaEngine.resolve -- content-type validation", () => {
  it("rejects a non-JSON content-type", async () => {
    const engine = makeEngine(async () => fakeResponse("<html></html>", { contentType: "text/html" }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("rejects a missing content-type header", async () => {
    const engine = makeEngine(async () => fakeResponse("{}", { contentType: null }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("accepts application/json with a charset parameter", async () => {
    const body: ResolveResponse = { version: 1, results: [{ kind: "AllowedVerdict" }] };
    const engine = makeEngine(async () => fakeResponse(body, { contentType: "application/json; charset=utf-8" }));
    await expect(engine.resolve(oneItem)).resolves.toEqual([{ kind: "AllowedVerdict" }]);
  });

  it("accepts a differently-cased media type", async () => {
    const body: ResolveResponse = { version: 1, results: [{ kind: "AllowedVerdict" }] };
    const engine = makeEngine(async () => fakeResponse(body, { contentType: "Application/JSON" }));
    await expect(engine.resolve(oneItem)).resolves.toEqual([{ kind: "AllowedVerdict" }]);
  });

  it("rejects a superset media type like application/jsonp", async () => {
    const engine = makeEngine(async () => fakeResponse("callback({})", { contentType: "application/jsonp" }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });
});

describe("AoaEngine.resolve -- malformed body", () => {
  it("rejects syntactically broken JSON with ProtocolError, not a raw SyntaxError", async () => {
    const engine = makeEngine(async () => fakeResponse("not valid json{{{"));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("rejects a body that parses to null with ProtocolError, not a raw TypeError", async () => {
    const engine = makeEngine(async () => fakeResponse("null"));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("rejects a body that parses to a non-object (e.g. a number)", async () => {
    const engine = makeEngine(async () => fakeResponse("42"));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("rejects the wrong wire-language version", async () => {
    const engine = makeEngine(async () => fakeResponse({ version: 2, results: [] }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("rejects a results array shorter than items", async () => {
    const engine = makeEngine(async () => fakeResponse({ version: 1, results: [] }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("rejects results that isn't an array at all", async () => {
    const engine = makeEngine(async () => fakeResponse({ version: 1, results: null }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("rejects results that is an object instead of an array", async () => {
    const engine = makeEngine(async () => fakeResponse({ version: 1, results: { kind: "AllowedVerdict" } }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });
});

describe("AoaEngine.resolve -- per-element verdict validation", () => {
  it("rejects an element with no kind field at all, instead of silently reading as a denial", async () => {
    const engine = makeEngine(async () => fakeResponse({ version: 1, results: [{}] }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("rejects an element whose kind is outside the known set", async () => {
    const engine = makeEngine(async () => fakeResponse({ version: 1, results: [{ kind: "TotallyMadeUp" }] }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("rejects a FailSecurityVerdict element with a missing reason", async () => {
    const engine = makeEngine(async () => fakeResponse({ version: 1, results: [{ kind: "FailSecurityVerdict" }] }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("rejects a FailErrorVerdict element with an empty-string reason", async () => {
    const engine = makeEngine(async () => fakeResponse({ version: 1, results: [{ kind: "FailErrorVerdict", reason: "" }] }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("rejects a non-object element (e.g. a bare string) inside results", async () => {
    const engine = makeEngine(async () => fakeResponse({ version: 1, results: ["AllowedVerdict"] }));
    await expect(engine.resolve(oneItem)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("accepts AllowedVerdict with no reason field", async () => {
    const engine = makeEngine(async () => fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] }));
    await expect(engine.resolve(oneItem)).resolves.toEqual([{ kind: "AllowedVerdict" }]);
  });
});

describe("AoaEngine.resolve -- trace_id", () => {
  it("sends an auto-generated x-trace-id when opts.traceId is not given", async () => {
    let capturedTraceId: string | null = null;
    const fetchImpl = (async (_url: string, init: RequestInit) => {
      capturedTraceId = new Headers(init.headers).get("x-trace-id");
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;

    await makeEngine(fetchImpl).resolve(oneItem);

    expect(capturedTraceId).not.toBeNull();
    expect(capturedTraceId).toMatch(/^[0-9a-f-]{36}$/i);
  });

  it("uses opts.traceId when given, instead of generating a new one", async () => {
    let capturedTraceId: string | null = null;
    const fetchImpl = (async (_url: string, init: RequestInit) => {
      capturedTraceId = new Headers(init.headers).get("x-trace-id");
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;

    await makeEngine(fetchImpl).resolve(oneItem, { traceId: "caller-supplied-trace-id" });

    expect(capturedTraceId).toBe("caller-supplied-trace-id");
  });

  it("sends exactly one x-trace-id for the whole batch, not one per item", async () => {
    const capturedTraceIds: string[] = [];
    const fetchImpl = (async (_url: string, init: RequestInit) => {
      capturedTraceIds.push(new Headers(init.headers).get("x-trace-id") ?? "");
      const items = JSON.parse(init.body as string).items as unknown[];
      return fakeResponse({ version: 1, results: items.map(() => ({ kind: "AllowedVerdict" })) });
    }) as typeof fetch;

    const items = [
      { operation: "a", params: {} },
      { operation: "b", params: {} },
    ];
    await makeEngine(fetchImpl).resolve(items);

    expect(capturedTraceIds).toHaveLength(1);
  });

  it("uses the injected generateTraceId instead of crypto.randomUUID", async () => {
    let capturedTraceId: string | null = null;
    const fetchImpl = (async (_url: string, init: RequestInit) => {
      capturedTraceId = new Headers(init.headers).get("x-trace-id");
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;

    const engine = makeEngine(fetchImpl, { generateTraceId: () => "fixed-trace-id" });
    await engine.resolve(oneItem);

    expect(capturedTraceId).toBe("fixed-trace-id");
  });
});

describe("AoaEngine.resolve -- header merging", () => {
  it("lets transport.headers override the default Content-Type, case-insensitively", async () => {
    let capturedContentType: string | null = null;
    const fetchImpl = (async (_url: string, init: RequestInit) => {
      capturedContentType = new Headers(init.headers).get("content-type");
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;

    const engine = makeEngine(fetchImpl, { headers: { "content-type": "application/json; boundary=x" } });
    await engine.resolve(oneItem);

    expect(capturedContentType).toBe("application/json; boundary=x");
  });

  it("lets transport.headers add an Authorization header without disturbing the trace id", async () => {
    let capturedAuth: string | null = null;
    let capturedTraceId: string | null = null;
    const fetchImpl = (async (_url: string, init: RequestInit) => {
      const h = new Headers(init.headers);
      capturedAuth = h.get("authorization");
      capturedTraceId = h.get("x-trace-id");
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;

    const engine = makeEngine(fetchImpl, { headers: { Authorization: "Bearer token123" } });
    await engine.resolve(oneItem, { traceId: "t-1" });

    expect(capturedAuth).toBe("Bearer token123");
    expect(capturedTraceId).toBe("t-1");
  });
});

describe("AoaEngine.resolve -- cache (chapter 5.5 prerequisite, issue #157)", () => {
  it("a second identical call within the TTL is served from cache -- only one network call happens", async () => {
    let networkCallCount = 0;
    const fetchImpl = (async () => {
      networkCallCount += 1;
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;
    const engine = makeEngine(fetchImpl);

    await expect(engine.resolve(oneItem)).resolves.toEqual([{ kind: "AllowedVerdict" }]);
    await expect(engine.resolve(oneItem)).resolves.toEqual([{ kind: "AllowedVerdict" }]);

    expect(networkCallCount).toBe(1);
  });

  it("skipCache always hits the network, even with a fresh cache entry, and still updates the cache", async () => {
    let networkCallCount = 0;
    const fetchImpl = (async () => {
      networkCallCount += 1;
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;
    const engine = makeEngine(fetchImpl);

    await engine.resolve(oneItem); // network call #1, populates the cache
    await engine.resolve(oneItem); // cache hit, no network call
    await engine.resolve(oneItem, { skipCache: true }); // forced network call #2, despite a fresh entry
    await engine.resolve(oneItem); // cache hit again (skipCache wrote the fresh answer through)

    expect(networkCallCount).toBe(2);
  });

  it("a cache miss for one item in a batch still returns both items, merged in the original order", async () => {
    const cachedItem = { operation: "GET /orders", params: { page: 1 } };
    const freshItem = { operation: "POST /actions/cancel-order", params: { order_id: 7 } };
    let capturedNetworkItems: unknown;
    // Distinct verdicts per operation, not one fixed response -- so the assertion below
    // can only pass if the cached answer and the fresh answer both survive untouched,
    // rather than one accidentally being a copy of the other.
    const fetchImpl = (async (_url: string, init: RequestInit) => {
      const requestItems = JSON.parse(init.body as string).items as Array<{ operation: string }>;
      capturedNetworkItems = requestItems;
      const results = requestItems.map((item) =>
        item.operation === cachedItem.operation
          ? { kind: "AllowedVerdict" as const }
          : { kind: "FailSecurityVerdict" as const, reason: "no access to this order" },
      );
      return fakeResponse({ version: 1, results });
    }) as typeof fetch;
    const engine = makeEngine(fetchImpl);
    await engine.resolve([cachedItem]); // primes the cache with AllowedVerdict for cachedItem only

    const results = await engine.resolve([cachedItem, freshItem]);

    expect(capturedNetworkItems).toEqual([freshItem]); // only the miss went over the wire
    expect(results).toEqual([{ kind: "AllowedVerdict" }, { kind: "FailSecurityVerdict", reason: "no access to this order" }]);
  });

  it("FailErrorVerdict is never cached -- an identical follow-up call goes to the network again", async () => {
    let networkCallCount = 0;
    const fetchImpl = (async () => {
      networkCallCount += 1;
      return fakeResponse({ version: 1, results: [{ kind: "FailErrorVerdict", reason: "UNKNOWN_ENDPOINT" }] });
    }) as typeof fetch;
    const engine = makeEngine(fetchImpl);

    await engine.resolve(oneItem);
    await engine.resolve(oneItem);

    expect(networkCallCount).toBe(2);
  });

  it("an entry past its TTL is refetched instead of served stale", async () => {
    let networkCallCount = 0;
    const fetchImpl = (async () => {
      networkCallCount += 1;
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;
    let now = 0;
    const engine = makeEngine(fetchImpl, { clock: () => now, cache: { ttlMs: 1_000 } });

    await engine.resolve(oneItem);
    now += 1_000; // exactly at the TTL boundary -- staleAt itself must not still count as fresh
    await engine.resolve(oneItem);

    expect(networkCallCount).toBe(2);
  });

  // Audit finding 6: the two TTL-boundary tests above both override cache.ttlMs
  // (1_000, 10_000) -- neither one pins the actual DEFAULT_TTL_MS = 3_000
  // constant itself against a controlled clock. A typo in that constant (an
  // extra zero, say) would pass every "served from cache" test regardless of
  // its real value, and these boundary tests never touch the default at all.
  it("the literal default TTL (DEFAULT_TTL_MS = 3000, no ttlMs override) is honored at its exact boundary", async () => {
    let networkCallCount = 0;
    const fetchImpl = (async () => {
      networkCallCount += 1;
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;
    let now = 0;
    const engine = makeEngine(fetchImpl, { clock: () => now }); // no cache.ttlMs override

    await engine.resolve(oneItem); // fetchedAt=0, staleAt=3000 if the constant is really 3_000
    now = 2_999;
    await engine.resolve(oneItem); // one millisecond inside the default window -- still a cache hit
    expect(networkCallCount).toBe(1);

    now = 3_000;
    await engine.resolve(oneItem); // staleAt itself -- must not still count as fresh
    expect(networkCallCount).toBe(2);
  });

  it("a custom ttlMs from transport.cache is honored, not a hardcoded default", async () => {
    let networkCallCount = 0;
    const fetchImpl = (async () => {
      networkCallCount += 1;
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;
    let now = 0;
    const engine = makeEngine(fetchImpl, { clock: () => now, cache: { ttlMs: 10_000 } });

    await engine.resolve(oneItem);
    now += 5_000; // well past the 3s default, but inside this engine's own 10s ttlMs
    await engine.resolve(oneItem);

    expect(networkCallCount).toBe(1);
  });
});

describe("AoaEngine constructor -- cache.ttlMs validation (audit finding 8)", () => {
  const fetchImpl = (async () => fakeResponse({ version: 1, results: [] })) as typeof fetch;

  it.each([NaN, Infinity, -Infinity, -1])("throws for ttlMs=%s", (ttlMs) => {
    expect(() => makeEngine(fetchImpl, { cache: { ttlMs } })).toThrow(/ttlMs/);
  });

  it("does not throw when ttlMs is omitted (falls back to the default)", () => {
    expect(() => makeEngine(fetchImpl, {})).not.toThrow();
  });

  it("does not throw for a valid, finite, non-negative ttlMs", () => {
    expect(() => makeEngine(fetchImpl, { cache: { ttlMs: 0 } })).not.toThrow();
    expect(() => makeEngine(fetchImpl, { cache: { ttlMs: 10_000 } })).not.toThrow();
  });
});

describe("AoaEngine -- identity", () => {
  it("exposes cachePartition read-only", () => {
    const engine = makeEngine(async () => fakeResponse({ version: 1, results: [] }));
    expect(engine.cachePartition).toBe("user:1");
    expect(() => {
      // @ts-expect-error cachePartition has no setter -- this must throw at runtime too
      engine.cachePartition = "user:2";
    }).toThrow();
  });
});

describe("AoaEngine.loadFrom", () => {
  function fakeManifest(endpoints: Array<{ operation: string; name: string; method: string; path: string }>) {
    return {
      manifest_version: "sha256:x",
      version: 1,
      manifest_schema_version: 2,
      endpoints: endpoints.map((e) => ({
        operation: e.operation,
        name: e.name,
        domain: "TestDomain",
        description: "test",
        route: { method: e.method, path: e.path },
        params_schema: { type: "object", properties: {} },
        result_schema: { type: "object", properties: {} },
      })),
      schemas: {},
    };
  }

  it("builds a real, working dynamic api -- bracket entry and dot alias both call resolve() with the right operation", async () => {
    let captured: unknown;
    const manifest = fakeManifest([
      { operation: "POST /actions/cancel-order", name: "CancelOrderAction", method: "POST", path: "/actions/cancel-order" },
      { operation: "GET /orders", name: "ListOrdersAction", method: "GET", path: "/orders" },
    ]);
    const fetchImpl = (async (url: string, init?: RequestInit) => {
      if (url === "https://x/client-manifest.json") return fakeResponse(manifest);
      captured = JSON.parse(init!.body as string);
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;
    const engine = makeEngine(fetchImpl);

    const api = await engine.loadFrom("https://x/client-manifest.json");
    expect(api.get?.orders).toBe(api.get?.["/orders"]);

    const cancelOrder = api.post?.["/actions/cancel-order"] as { can: (p: unknown) => Promise<boolean> };
    await expect(cancelOrder.can({ order_id: 1 })).resolves.toBe(true);
    expect((captured as { items: Array<{ operation: string }> }).items[0]?.operation).toBe("POST /actions/cancel-order");
  });

  it("throws NetworkUnavailable when the manifest fetch itself fails", async () => {
    const fetchImpl = (async () => {
      throw new Error("network down");
    }) as unknown as typeof fetch;
    await expect(makeEngine(fetchImpl).loadFrom("https://x/client-manifest.json")).rejects.toThrow(NetworkUnavailable);
  });

  it("throws ProtocolError on a non-ok manifest response", async () => {
    const fetchImpl = (async () => fakeResponse({}, { status: 500 })) as typeof fetch;
    await expect(makeEngine(fetchImpl).loadFrom("https://x/client-manifest.json")).rejects.toThrow(ProtocolError);
  });

  it("throws ProtocolError on a manifest body that is not valid JSON", async () => {
    const fetchImpl = (async () => fakeResponse("not json{", { status: 200 })) as typeof fetch;
    await expect(makeEngine(fetchImpl).loadFrom("https://x/client-manifest.json")).rejects.toThrow(ProtocolError);
  });

  it("throws ProtocolError (wrapping the real message) on a manifest that fails shape validation", async () => {
    const fetchImpl = (async () => fakeResponse({ version: 1 })) as typeof fetch;
    const error = await makeEngine(fetchImpl)
      .loadFrom("https://x/client-manifest.json")
      .catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ProtocolError);
    expect((error as ProtocolError).message).toMatch(/manifest_version/);
  });

  // Audit finding 8: assertManifestShape only checked that `endpoints` was an array,
  // never each element's own shape -- loadFrom read endpoint.route.method/.path
  // immediately afterward with no guard of its own, so a malformed element crashed with
  // a raw, uncaught TypeError ("Cannot read properties of undefined/null (reading
  // 'method')") instead of the same ProtocolError every other untrustworthy manifest
  // shape already produces here.
  it.each([
    ["route missing entirely", { operation: "POST /x", name: "X", domain: "D", description: "d", params_schema: {}, result_schema: {} }],
    ["route: null", { operation: "POST /x", name: "X", domain: "D", description: "d", route: null, params_schema: {}, result_schema: {} }],
  ])("throws ProtocolError, not a raw TypeError, when an endpoint has %s", async (_label, brokenEndpoint) => {
    const manifest = { manifest_version: "sha256:x", version: 1, manifest_schema_version: 2, endpoints: [brokenEndpoint], schemas: {} };
    const fetchImpl = (async () => fakeResponse(manifest)) as typeof fetch;
    const error = await makeEngine(fetchImpl)
      .loadFrom("https://x/client-manifest.json")
      .catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ProtocolError);
    expect(error).not.toBeInstanceOf(TypeError);
    expect((error as ProtocolError).message).toMatch(/endpoints\[0\].*route/);
  });

  it("produces the exact same key structure (methods, bracket paths, aliases) as the static renderer for the same manifest", async () => {
    const { renderApiLayout } = await import("./codegen/api-layout-to-ts.ts");
    const { buildLayout } = await import("./path-layout.ts");

    const layoutEndpoints = [
      { operation: "POST /actions/cancel-order", method: "POST", path: "/actions/cancel-order", baseName: "CancelOrder" },
      { operation: "GET /orders", method: "GET", path: "/orders", baseName: "Orders" },
      { operation: "GET /admin", method: "GET", path: "/admin", baseName: "AdminRoot" },
      { operation: "GET /admin/settings", method: "GET", path: "/admin/settings", baseName: "AdminSettings" },
    ];
    const layouts = buildLayout(layoutEndpoints);
    const { typesSource } = renderApiLayout(layouts);

    const manifest = fakeManifest(layoutEndpoints.map((e) => ({ operation: e.operation, name: e.baseName, method: e.method, path: e.path })));
    const fetchImpl = (async () => fakeResponse(manifest)) as typeof fetch;
    const api = await makeEngine(fetchImpl).loadFrom("https://x/client-manifest.json");

    // Every bracket path the static renderer types also exists as a real dynamic key.
    for (const e of layoutEndpoints) {
      expect(typesSource).toContain(`${JSON.stringify(e.path)}: GatePrimitive<`);
      expect(api[e.method.toLowerCase()]?.[e.path]).toBeDefined();
    }
    // "admin" collided (leaf + branch) in both: not a bracket-shaped standalone alias
    // leaf in the static type, and demoted to a pure namespace dynamically too.
    expect(typesSource).not.toMatch(/\n\s*admin: GatePrimitive</);
    expect(api.get?.admin).not.toBe(api.get?.["/admin"]);
    expect((api.get?.admin as Record<string, unknown>)?.settings).toBe(api.get?.["/admin/settings"]);
    // "orders" is a clean single-segment alias in both.
    expect(typesSource).toContain("orders: GatePrimitive<OrdersParams>;");
    expect(api.get?.orders).toBe(api.get?.["/orders"]);
  });
});

describe("error classes", () => {
  it("each request-level error class sets its own .name", () => {
    expect(new Unauthorized("x").name).toBe("Unauthorized");
    expect(new ProtocolError("x").name).toBe("ProtocolError");
    expect(new NetworkUnavailable("x").name).toBe("NetworkUnavailable");
    expect(new AoaResolveError("TIMEOUT").name).toBe("AoaResolveError");
  });

  it("AoaResolveError.message is a sentence, .reason is the raw wire code", () => {
    const err = new AoaResolveError("EVALUATION_FAILED");
    expect(err.reason).toBe("EVALUATION_FAILED");
    expect(err.message).not.toBe("EVALUATION_FAILED");
    expect(err.message).toContain("EVALUATION_FAILED");
  });
});

describe("isRetryableCheckError", () => {
  it("TIMEOUT is retryable", () => {
    expect(isRetryableCheckError("TIMEOUT")).toBe(true);
  });

  it.each(["UNKNOWN_ENDPOINT", "EVALUATION_FAILED", "SomeUnexpectedException"])("%s is not retryable", (reason) => {
    expect(isRetryableCheckError(reason)).toBe(false);
  });
});
