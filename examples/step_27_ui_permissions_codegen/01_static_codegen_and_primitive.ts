// examples/step_27_ui_permissions_codegen/01_static_codegen_and_primitive.ts
//
// The static codegen path end to end: generateClient(url) reads a manifest and
// returns TypeScript source; write it to a file, import it, and use the generated
// api. Full-path access always works; the dot alias (api.get.orders) only exists
// for a "clean" path -- /actions/cancel-order has a hyphen, so it gets no alias at
// all, in any form, only the bracket key.
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { AoaEngine } from "../../packages/aoa-client-js/src/index.ts";
import { generateClient } from "../../packages/aoa-client-js/src/codegen/generate-client.ts";
import type { ResolveResponse } from "../../packages/aoa-client-js/src/types.ts";

// The generated file's own `import { z } from "zod"` needs a real node_modules to
// resolve -- writing the temp dir under the OS tmp dir would leave it unable to find
// zod at all. Nesting it inside packages/aoa-client-js/ lets plain node_modules
// resolution walk up and find the real, installed zod there.
const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "packages", "aoa-client-js");

const MANIFEST_URL = "https://api.example.test/client-manifest.json";

// A fake GET /client-manifest.json: one hyphenated path, one clean one.
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
    {
      operation: "GET /orders",
      name: "ListOrdersAction",
      domain: "OrdersDomain",
      description: "List orders",
      route: { method: "GET", path: "/orders" },
      params_schema: { type: "object", properties: {} },
      result_schema: { type: "object", properties: { count: { type: "integer" } }, required: ["count"] },
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

// 1. Static generation -- exactly what `aoa-codegen --url ... --out ...` or a build
// script calling generateClient(url) directly does.
const source = await generateClient(MANIFEST_URL);
console.log(`generated ${source.split("\n").length} lines of TypeScript`);

// 2. Write it and import it as a real module. A real project commits this file and
// imports the installed "aoa-client-js" package unchanged; here it's a throwaway
// temp file, so the self-import is rewritten to this repo's own package source.
const dir = mkdtempSync(path.join(packageRoot, ".codegen-example-"));
const generatedPath = path.join(dir, "generated-client.ts");
writeFileSync(generatedPath, source.replaceAll('"aoa-client-js"', '"../src/index.ts"'));

try {
  const generated = (await import(pathToFileURL(generatedPath).href)) as {
    createGateApi: (engine: AoaEngine) => {
      post: Record<string, { can(params: unknown): Promise<boolean> }>;
      get: Record<string, { can(params: unknown): Promise<boolean> }> & { orders: { can(params: unknown): Promise<boolean> } };
    };
  };

  // Past this point, fetch calls go to the resolver, not the manifest.
  globalThis.fetch = (async (_url: string, init?: RequestInit) => {
    const body = JSON.parse(init!.body as string) as { items: Array<{ operation: string }> };
    const response: ResolveResponse = { version: 1, results: body.items.map(() => ({ kind: "AllowedVerdict" })) };
    return new Response(JSON.stringify(response), { status: 200, headers: { "content-type": "application/json" } });
  }) as typeof fetch;

  const engine = new AoaEngine({ transport: { baseUrl: "https://example.test", fetchImpl: fetch, cachePartition: "user:42" } });
  const gate = generated.createGateApi(engine);

  // Full path always works.
  const canCancel = await gate.post["/actions/cancel-order"].can({ order_id: 7 });
  console.log(`gate.post["/actions/cancel-order"].can(...) -> ${canCancel}`);

  // /orders is a clean path (no {param}, hyphen, or dot) -- it gets a dot alias too,
  // and both forms call the exact same Primitive, not two independent copies.
  console.log(`gate.get.orders === gate.get["/orders"] -> ${gate.get.orders === gate.get["/orders"]}`);
  console.log(`gate.get.orders.can({}) -> ${await gate.get.orders.can({})}`);

  // /actions/cancel-order has a hyphen -- no dot alias exists for it in any form.
  // There is no `gate.post.actions` to even try; the bracket form above is the only way.
} finally {
  rmSync(dir, { recursive: true, force: true });
}
