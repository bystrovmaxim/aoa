// packages/aoa-client-js/src/codegen/resolve-contract.test.ts
//
// Contract test: one fixture, read by both Python and TypeScript (chapter 5, "Случай 2").
//
// contracts/fixtures/resolve_response_basic.json is a real ResolveResponse. The Python
// half of this guarantee lives in packages/aoa-fastapi-adapter/tests/test_resolve_contract.py
// -- if AllowedVerdict/FailSecurityVerdict/FailErrorVerdict change shape on one side and
// not the other, one of the two goes red. This is that TS half, as a real vitest test
// picked up automatically by `npm test` (audit finding 5: the standalone example script,
// examples/step_27_ui_permissions_codegen/04_contract_fixture_resolve_response.ts, reads
// the identical fixture but is a plain runnable illustration, not matched by vitest's
// *.test.ts pattern -- it never ran as part of any automated check).
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { afterEach, describe, expect, it, vi } from "vitest";

import { generateClient } from "./generate-client.ts";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const repoRoot = path.resolve(packageRoot, "..", "..");
const FIXTURE_PATH = path.join(repoRoot, "contracts", "fixtures", "resolve_response_basic.json");
const MANIFEST_URL = "https://api.example.test/client-manifest.json";

const MANIFEST = {
  manifest_version: "sha256:example",
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
};

function stubManifestFetch(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url !== MANIFEST_URL) throw new Error(`unexpected fetch: ${url}`);
      return { ok: true, status: 200, statusText: "OK", json: async () => MANIFEST };
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * Writes a real generateClient() output to a temp file inside this package (so its own
 * `import { z } from "zod"` resolves against the real, installed zod via plain node_modules
 * lookup) and dynamically imports the real ResolveResponseSchema export -- not a
 * regex-extracted or `new Function`-evaluated fragment.
 */
async function loadResolveResponseSchema(): Promise<{
  schema: { parse(data: unknown): unknown };
  cleanup: () => void;
}> {
  const source = await generateClient(MANIFEST_URL);
  const dir = mkdtempSync(path.join(packageRoot, ".codegen-example-"));
  const filePath = path.join(dir, "generated-client.ts");
  writeFileSync(filePath, source.replaceAll('"aoa-client-js"', '"../src/index.ts"'), "utf8");
  const generated = (await import(pathToFileURL(filePath).href)) as { ResolveResponseSchema: { parse(data: unknown): unknown } };
  return { schema: generated.ResolveResponseSchema, cleanup: () => rmSync(dir, { recursive: true, force: true }) };
}

describe("resolve_response_basic.json contract fixture (TypeScript half)", () => {
  it("the fixture file exists and is valid JSON", () => {
    const fixture: unknown = JSON.parse(readFileSync(FIXTURE_PATH, "utf8"));
    expect(fixture).toBeTypeOf("object");
  });

  it("the generated ResolveResponseSchema parses the fixture without throwing, matching the Python side's assertions", async () => {
    stubManifestFetch();
    const { schema, cleanup } = await loadResolveResponseSchema();
    try {
      const fixture: unknown = JSON.parse(readFileSync(FIXTURE_PATH, "utf8"));
      const parsed = schema.parse(fixture) as { version: number; results: Array<{ kind: string; reason?: string }> };
      expect(parsed.version).toBe(1);
      expect(parsed.results).toHaveLength(2);
      expect(parsed.results[0]).toEqual({ kind: "AllowedVerdict" });
      expect(parsed.results[1]).toEqual({ kind: "FailSecurityVerdict", reason: "only the order owner can cancel" });
    } finally {
      cleanup();
    }
  });

  it("round-trips all three verdict kinds -- not just the ones in this one fixture", async () => {
    stubManifestFetch();
    const { schema, cleanup } = await loadResolveResponseSchema();
    try {
      const parsed = schema.parse({
        version: 1,
        results: [{ kind: "AllowedVerdict" }, { kind: "FailSecurityVerdict", reason: "no" }, { kind: "FailErrorVerdict", reason: "UNKNOWN_ENDPOINT" }],
      }) as { results: Array<{ kind: string; reason?: string }> };
      expect(parsed.results[0]).toEqual({ kind: "AllowedVerdict" });
      expect(parsed.results[1]).toEqual({ kind: "FailSecurityVerdict", reason: "no" });
      expect(parsed.results[2]).toEqual({ kind: "FailErrorVerdict", reason: "UNKNOWN_ENDPOINT" });
    } finally {
      cleanup();
    }
  });

  it("rejects a FailSecurityVerdict missing its required reason -- mirrors the Python side's hardening test", async () => {
    stubManifestFetch();
    const { schema, cleanup } = await loadResolveResponseSchema();
    try {
      expect(() => schema.parse({ version: 1, results: [{ kind: "FailSecurityVerdict" }] })).toThrow();
    } finally {
      cleanup();
    }
  });

  it("rejects an unrecognized kind rather than silently passing it through", async () => {
    stubManifestFetch();
    const { schema, cleanup } = await loadResolveResponseSchema();
    try {
      expect(() => schema.parse({ version: 1, results: [{ kind: "SomethingElse" }] })).toThrow();
    } finally {
      cleanup();
    }
  });
});
