// examples/step_27_ui_permissions_codegen/04_contract_fixture_resolve_response.ts
//
// One fixture, read by both sides of the wire: contracts/fixtures/resolve_response_basic.json
// is a real ResolveResponse. This example parses it with the SAME generated
// ResolveResponseSchema that a real static client would ship (generateClient's real zod
// output, imported like any real app would, not a hand-written schema); the companion
// Python test (packages/aoa-fastapi-adapter/tests/test_resolve_contract.py) parses the
// identical file with the real pydantic ResolveResponse model. If someone changes the
// shape of AllowedVerdict/FailSecurityVerdict/FailErrorVerdict on one side and not the
// other, one of the two tests goes red -- this example demonstrates the TypeScript half
// of that guarantee, not the endpoint-set drift covered in example 3.
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { generateClient } from "../../packages/aoa-client-js/src/codegen/generate-client.ts";

const MANIFEST_URL = "https://api.example.test/client-manifest.json";
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const packageRoot = path.join(repoRoot, "packages", "aoa-client-js");

globalThis.fetch = (async (url: string) => {
  if (url !== MANIFEST_URL) throw new Error(`unexpected fetch: ${url}`);
  const manifest = {
    manifest_version: "sha256:example",
    version: 1,
    manifest_schema_version: 2,
    endpoints: [],
    // The real shape of the manifest's own "schemas.ResolveResponse" entry --
    // BaseVerdict is deliberately abstract here (kind only); see
    // json-schema-to-zod.ts for why AllowedVerdict/FailSecurityVerdict/FailErrorVerdict
    // come from a fixed, hand-maintained zod union instead of this entry directly.
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
  return new Response(JSON.stringify(manifest), { status: 200, headers: { "content-type": "application/json" } });
}) as typeof fetch;

// Generate and import it as a real module -- same "write, then import" shape as
// 01_static_codegen_and_primitive.ts, needed here so the generated file's own
// `import { z } from "zod"` resolves against a real, installed zod.
const source = await generateClient(MANIFEST_URL);
const dir = mkdtempSync(path.join(packageRoot, ".codegen-example-"));
const generatedPath = path.join(dir, "generated-client.ts");
writeFileSync(generatedPath, source.replaceAll('"aoa-client-js"', '"../src/index.ts"'));

try {
  const generated = (await import(pathToFileURL(generatedPath).href)) as {
    ResolveResponseSchema: { parse(data: unknown): { version: number; results: Array<{ kind: string; reason?: string }> } };
  };

  const fixturePath = path.join(repoRoot, "contracts", "fixtures", "resolve_response_basic.json");
  const fixture: unknown = JSON.parse(readFileSync(fixturePath, "utf8"));

  const parsed = generated.ResolveResponseSchema.parse(fixture);
  console.log(`parsed ${parsed.results.length} results from ${fixturePath}`);
  console.log(`results[0].kind -> ${parsed.results[0]!.kind}`);
  console.log(`results[1].kind -> ${parsed.results[1]!.kind}, reason -> ${JSON.stringify(parsed.results[1]!.reason)}`);

  if (parsed.results[0]!.kind !== "AllowedVerdict" || parsed.results[1]!.reason !== "only the order owner can cancel") {
    throw new Error("fixture did not parse as expected -- see packages/aoa-fastapi-adapter/tests/test_resolve_contract.py for the Python side");
  }
  console.log("TypeScript side of the contract test: OK");
} finally {
  rmSync(dir, { recursive: true, force: true });
}
