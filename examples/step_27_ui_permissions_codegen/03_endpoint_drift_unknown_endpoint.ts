// examples/step_27_ui_permissions_codegen/03_endpoint_drift_unknown_endpoint.ts
//
// A generated static client is only as fresh as the manifest it was generated
// against. If the server removes or renames a route and nobody regenerates the
// client, the stale Primitive is still callable -- compiling against it proves
// nothing, since tsc only ever checked it against the OLD manifest. This example
// simulates the server no longer recognizing an operation the static client still
// has a Primitive for: verdict() comes back FailErrorVerdict/UNKNOWN_ENDPOINT, and
// can() throws AoaResolveError -- never a silent, wrong `false`, because an
// unanswered question is not the same thing as a denial.
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { AoaEngine, AoaResolveError } from "../../packages/aoa-client-js/src/index.ts";
import { generateClient } from "../../packages/aoa-client-js/src/codegen/generate-client.ts";
import type { ResolveResponse, Verdict } from "../../packages/aoa-client-js/src/types.ts";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "packages", "aoa-client-js");
const MANIFEST_URL = "https://api.example.test/client-manifest.json";

const MANIFEST = {
  manifest_version: "sha256:example",
  version: 1,
  manifest_schema_version: 2,
  endpoints: [
    {
      operation: "POST /actions/cancel-order",
      name: "CancelOrderAction",
      domain: "OrdersDomain",
      description: "Cancel an order",
      route: { method: "POST", path: "/actions/cancel-order" },
      params_schema: { type: "object", properties: { order_id: { type: "integer" } }, required: ["order_id"] },
      result_schema: { type: "object", properties: { status: { type: "string" } }, required: ["status"] },
    },
  ],
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

globalThis.fetch = (async (url: string) => {
  if (url !== MANIFEST_URL) throw new Error(`unexpected fetch: ${url}`);
  return new Response(JSON.stringify(MANIFEST), { status: 200, headers: { "content-type": "application/json" } });
}) as typeof fetch;

// Generate and load a static client -- this is the client a developer committed
// yesterday, before the server changed.
const source = await generateClient(MANIFEST_URL);
const dir = mkdtempSync(path.join(packageRoot, ".codegen-example-"));
const generatedPath = path.join(dir, "generated-client.ts");
writeFileSync(generatedPath, source.replaceAll('"aoa-client-js"', '"../src/index.ts"'));

try {
  const generated = (await import(pathToFileURL(generatedPath).href)) as {
    createGateApi: (engine: AoaEngine) => {
      post: Record<string, { verdict(params: unknown): Promise<Verdict>; can(params: unknown): Promise<boolean> }>;
    };
  };

  // The server today: /actions/cancel-order was removed (renamed, merged into
  // another action, whatever) -- the resolver no longer recognizes this operation.
  globalThis.fetch = (async () => {
    const response: ResolveResponse = { version: 1, results: [{ kind: "FailErrorVerdict", reason: "UNKNOWN_ENDPOINT" }] };
    return new Response(JSON.stringify(response), { status: 200, headers: { "content-type": "application/json" } });
  }) as typeof fetch;

  const engine = new AoaEngine({ transport: { baseUrl: "https://example.test", fetchImpl: fetch, cachePartition: "user:42" } });
  const gate = generated.createGateApi(engine);
  const staleCancelOrder = gate.post["/actions/cancel-order"];

  const verdict = await staleCancelOrder.verdict({ order_id: 7 });
  console.log(`verdict() -> ${JSON.stringify(verdict)}`);

  try {
    await staleCancelOrder.can({ order_id: 7 });
    console.log("this should not print -- can() must not silently resolve for an unknown endpoint");
  } catch (error) {
    console.log(`can() throws instead of returning false: ${(error as AoaResolveError).name} (reason: ${(error as AoaResolveError).reason})`);
    console.log(`instanceof AoaResolveError -> ${error instanceof AoaResolveError}`);
  }
} finally {
  rmSync(dir, { recursive: true, force: true });
}
