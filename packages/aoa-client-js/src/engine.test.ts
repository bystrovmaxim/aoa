// packages/aoa-client-js/src/engine.test.ts
import { describe, expect, it } from "vitest";

import { AoaEngine, NetworkUnavailable, ProtocolError, Unauthorized, isRetryableCheckError } from "./engine.ts";
import type { ResolveResponse } from "./types.ts";

function fakeResponse(body: unknown, init?: { status?: number; contentType?: string }): Response {
  return new Response(JSON.stringify(body), {
    status: init?.status ?? 200,
    headers: { "content-type": init?.contentType ?? "application/json" },
  });
}

function makeEngine(fetchImpl: typeof fetch): AoaEngine {
  return new AoaEngine({
    transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:1" },
  });
}

describe("AoaEngine.resolve", () => {
  it("posts version+items to the right URL and returns results as-is", async () => {
    let capturedUrl = "";
    let capturedBody: unknown;
    const fetchImpl = (async (url: string, init: RequestInit) => {
      capturedUrl = url;
      capturedBody = JSON.parse(init.body as string);
      const body: ResolveResponse = { version: 1, results: [{ kind: "AllowedVerdict" }] };
      return fakeResponse(body);
    }) as typeof fetch;

    const items = [{ operation: "POST /actions/cancel-order", params: { order_id: 7 } }];
    const results = await makeEngine(fetchImpl).resolve(items);

    expect(capturedUrl).toBe("https://example.test/permissions/resolve");
    expect(capturedBody).toEqual({ version: 1, items });
    expect(results).toEqual([{ kind: "AllowedVerdict" }]);
    expect(results[0].kind === "AllowedVerdict").toBe(true);
  });

  it("turns request-level failures into typed errors, never a verdict", async () => {
    const unauthorized = makeEngine((async () => fakeResponse(null, { status: 401 })) as typeof fetch);
    await expect(unauthorized.resolve([])).rejects.toBeInstanceOf(Unauthorized);

    const down = makeEngine((async () => {
      throw new Error("network down");
    }) as typeof fetch);
    await expect(down.resolve([])).rejects.toBeInstanceOf(NetworkUnavailable);
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
    expect(isRetryableCheckError("TIMEOUT")).toBe(true);
    expect(isRetryableCheckError("UNKNOWN_ENDPOINT")).toBe(false);
  });

  it("rejects a malformed response instead of reading it as a decision", async () => {
    const items = [{ operation: "x", params: {} }];

    const wrongContentType = makeEngine(
      (async () => fakeResponse("<html></html>", { contentType: "text/html" })) as typeof fetch,
    );
    await expect(wrongContentType.resolve(items)).rejects.toBeInstanceOf(ProtocolError);

    const wrongVersion = makeEngine((async () => fakeResponse({ version: 2, results: [] })) as typeof fetch);
    await expect(wrongVersion.resolve(items)).rejects.toBeInstanceOf(ProtocolError);

    const wrongCardinality = makeEngine((async () => fakeResponse({ version: 1, results: [] })) as typeof fetch);
    await expect(wrongCardinality.resolve(items)).rejects.toBeInstanceOf(ProtocolError);
  });

  it("keeps identity read-only -- switching subjects requires a new AoaEngine", () => {
    const engine = makeEngine((async () => fakeResponse({ version: 1, results: [] })) as typeof fetch);

    expect(engine.cachePartition).toBe("user:1");
    expect(() => {
      // @ts-expect-error cachePartition has no setter -- this must throw at runtime too
      engine.cachePartition = "user:2";
    }).toThrow();
  });
});
