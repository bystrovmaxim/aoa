// packages/aoa-client-js/src/codegen/index.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { generateClient } from "./index.ts";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("codegen public barrel (aoa-client-js/codegen)", () => {
  it("exposes generateClient as a working function through the actual public entry point", async () => {
    expect(typeof generateClient).toBe("function");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => ({
          manifest_version: "sha256:x",
          version: 1,
          manifest_schema_version: 2,
          endpoints: [],
          schemas: {
            ResolveResponse: {
              mode: "serialization",
              json_schema: {
                $defs: { BaseVerdict: { properties: { kind: { type: "string" } }, type: "object" } },
                properties: { version: { type: "integer" }, results: { items: { $ref: "#/$defs/BaseVerdict" }, type: "array" } },
                required: ["version", "results"],
                type: "object",
              },
            },
          },
        }),
      })),
    );
    const source = await generateClient("https://x/client-manifest.json");
    expect(source).toContain("export const ResolveResponseSchema =");
  });
});
