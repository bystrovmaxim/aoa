// packages/aoa-client-js/src/index.test.ts
// Nothing else imports from the package's own public barrel (engine.test.ts
// imports directly from ./engine.ts) -- without this, a broken or missing
// export in index.ts would go unnoticed by the whole test suite.
import { describe, expect, it } from "vitest";

import {
  AoaEngine,
  AoaResolveError,
  NetworkUnavailable,
  ProtocolError,
  Unauthorized,
  isRetryableCheckError,
} from "./index.ts";
import type { ResolveResponse } from "./index.ts";

describe("public exports (index.ts)", () => {
  it("re-exports every value export from engine.ts", () => {
    expect(AoaEngine).toBeTypeOf("function");
    expect(AoaResolveError).toBeTypeOf("function");
    expect(NetworkUnavailable).toBeTypeOf("function");
    expect(ProtocolError).toBeTypeOf("function");
    expect(Unauthorized).toBeTypeOf("function");
    expect(isRetryableCheckError).toBeTypeOf("function");
  });

  it("AoaEngine imported from the barrel actually works end-to-end", async () => {
    const fetchImpl: typeof fetch = async () => {
      const body: ResolveResponse = { version: 1, results: [{ kind: "AllowedVerdict" }] };
      return new Response(JSON.stringify(body), { headers: { "content-type": "application/json" } });
    };
    const engine = new AoaEngine({ transport: { baseUrl: "https://x", fetchImpl, cachePartition: "u:1" } });

    const [result] = await engine.resolve([{ operation: "x", params: {} }]);

    expect(result).toEqual({ kind: "AllowedVerdict" });
  });
});
