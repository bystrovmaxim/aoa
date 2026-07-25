// packages/aoa-client-js/src/codegen/resolve-contract.test.ts
//
// Contract test, TypeScript half: every fixture in contracts/fixtures/ (chapter 12, #144).
//
// Each file there is a complete POST /permissions/resolve response body, read by BOTH
// halves of the system: here with the generated zod ResolveResponseSchema, and in
// packages/aoa-fastapi-adapter/tests/test_resolve_contract.py with the real pydantic
// model. If AllowedVerdict/FailSecurityVerdict/FailErrorVerdict change shape on one side
// and not the other, one of the two goes red.
//
// The split is by filename, matching the Python half exactly:
// resolve_response_invalid_*.json must be REJECTED, every other resolve_response_*.json
// must PARSE. A convention both languages can apply is the only thing that keeps the two
// halves testing the same partition of the same directory -- a hand-maintained list on
// each side drifts apart on the first fixture someone forgets to register.
//
// This is a real vitest test picked up by `npm test` (audit finding 5: the standalone
// example script examples/step_27_ui_permissions_codegen/04_contract_fixture_resolve_response.ts
// reads the same directory but is a runnable illustration, not matched by vitest's
// *.test.ts pattern -- it never ran as part of any automated check).
import { mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { generateClient } from "./generate-client.ts";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const repoRoot = path.resolve(packageRoot, "..", "..");
const FIXTURE_DIR = path.join(repoRoot, "contracts", "fixtures");
const MANIFEST_URL = "https://api.example.test/client-manifest.json";

const fixtureNames = readdirSync(FIXTURE_DIR)
  .filter((name) => name.startsWith("resolve_response_") && name.endsWith(".json"))
  .sort();
const VALID_FIXTURES = fixtureNames.filter((name) => !name.includes("_invalid_"));
const INVALID_FIXTURES = fixtureNames.filter((name) => name.includes("_invalid_"));

function readFixture(name: string): unknown {
  return JSON.parse(readFileSync(path.join(FIXTURE_DIR, name), "utf8"));
}

// The manifest's own $defs.BaseVerdict is the ABSTRACT base's schema ({ kind: string }
// only) -- see json-schema-to-zod.ts's WELL_KNOWN_REF_ZOD, which substitutes the real,
// concrete discriminated union for that well-known name. This stub therefore only has to
// be shaped like the real manifest, not carry the real verdict schemas.
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
        additionalProperties: false,
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

/**
 * Writes a real generateClient() output to a temp file inside this package (so its own
 * `import { z } from "zod"` resolves against the real, installed zod via plain node_modules
 * lookup) and dynamically imports the real ResolveResponseSchema export -- not a
 * regex-extracted or `new Function`-evaluated fragment.
 *
 * Built ONCE for the whole file rather than per test: generating and importing a client is
 * the expensive part, and every case below asks the same schema a different question.
 */
let schema: { parse(data: unknown): unknown };
let cleanup: () => void = () => {};

beforeAll(async () => {
  stubManifestFetch();
  try {
    const source = await generateClient(MANIFEST_URL);
    const dir = mkdtempSync(path.join(packageRoot, ".codegen-example-"));
    const filePath = path.join(dir, "generated-client.ts");
    writeFileSync(filePath, source.replaceAll('"aoa-client-js"', '"../src/index.ts"'), "utf8");
    const generated = (await import(pathToFileURL(filePath).href)) as { ResolveResponseSchema: typeof schema };
    schema = generated.ResolveResponseSchema;
    cleanup = () => rmSync(dir, { recursive: true, force: true });
  } finally {
    vi.unstubAllGlobals();
  }
});

afterAll(() => cleanup());
afterEach(() => vi.unstubAllGlobals());

describe("contract fixtures (TypeScript half)", () => {
  // A glob-driven suite that finds zero files passes vacuously -- the one failure mode a
  // data-driven test has and a hand-written one does not. Mirrors the Python half's
  // test_discovery_found_both_groups.
  it("discovery found both groups of fixtures", () => {
    expect(VALID_FIXTURES.length).toBeGreaterThanOrEqual(2);
    expect(INVALID_FIXTURES.length).toBeGreaterThanOrEqual(2);
  });

  it.each(VALID_FIXTURES)("parses %s without loss", (name) => {
    const fixture = readFixture(name);

    // Deep equality against the file, not merely "did not throw": zod's default is to
    // STRIP unknown keys, so a schema that misunderstood the shape would still "parse"
    // successfully while quietly returning less than it was given.
    expect(schema.parse(fixture)).toEqual(fixture);
  });

  it.each(INVALID_FIXTURES)("rejects %s", (name) => {
    expect(() => schema.parse(readFixture(name))).toThrow();
  });
});

describe("what the fixtures mean", () => {
  it("object_forbidden: missing and foreign objects survive parsing as identical verdicts", () => {
    const parsed = schema.parse(readFixture("resolve_response_object_forbidden.json")) as {
      results: Array<Record<string, unknown>>;
    };

    // Oracle safety has to hold AFTER parsing too -- a schema that dropped or defaulted a
    // field differently for the two elements would reintroduce the difference the server
    // took care to remove.
    const [missing, foreign] = parsed.results;
    expect(missing).toEqual(foreign);
    expect(missing).toEqual({ kind: "FailSecurityVerdict", reason: "FORBIDDEN_OBJECT" });
  });

  it("all_kinds_mixed: one response carries every class, in order", () => {
    const parsed = schema.parse(readFixture("resolve_response_all_kinds_mixed.json")) as {
      results: Array<{ kind: string }>;
    };

    expect(parsed.results.map((r) => r.kind)).toEqual([
      "AllowedVerdict",
      "FailSecurityVerdict",
      "FailErrorVerdict",
      "AllowedVerdict",
    ]);
  });

  it.each([
    ["resolve_response_unknown_endpoint.json", "UNKNOWN_ENDPOINT"],
    ["resolve_response_evaluation_failed.json", "EVALUATION_FAILED"],
  ])("%s is a FailErrorVerdict, never a denial", (name, expectedReason) => {
    const parsed = schema.parse(readFixture(name)) as { results: Array<{ kind: string; reason?: string }> };

    const errors = parsed.results.filter((r) => r.kind === "FailErrorVerdict");
    expect(errors.map((r) => r.reason)).toEqual([expectedReason]);
    expect(parsed.results.some((r) => r.kind === "FailSecurityVerdict")).toBe(false);
  });
});

describe("shape guarantees beyond the files", () => {
  it("round-trips all three verdict kinds, not just the ones some fixture happens to contain", () => {
    const payload = {
      version: 1,
      results: [
        { kind: "AllowedVerdict" },
        { kind: "FailSecurityVerdict", reason: "no" },
        { kind: "FailErrorVerdict", reason: "UNKNOWN_ENDPOINT" },
      ],
    };

    expect(schema.parse(payload)).toEqual(payload);
  });

  it.each([
    ["a missing reason", { kind: "FailSecurityVerdict" }],
    ["an empty reason", { kind: "FailSecurityVerdict", reason: "" }],
    ["an unrecognized kind", { kind: "SomethingElse" }],
    ["an undeclared field", { kind: "AllowedVerdict", cachedUntil: 1 }],
    ["a reason on success", { kind: "AllowedVerdict", reason: "you may" }],
  ])("rejects %s", (_label, result) => {
    expect(() => schema.parse({ version: 1, results: [result] })).toThrow();
  });

  // The response envelope is extra="forbid" on the server too, not just its elements.
  it("rejects an undeclared field on the response itself, not only inside a verdict", () => {
    expect(() => schema.parse({ version: 1, results: [], serverTime: 123 })).toThrow();
  });
});
