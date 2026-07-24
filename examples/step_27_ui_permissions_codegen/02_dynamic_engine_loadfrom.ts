// examples/step_27_ui_permissions_codegen/02_dynamic_engine_loadfrom.ts
//
// The dynamic codegen path: engine.loadFrom(url) fetches the same manifest already
// at runtime and builds the same api shape in memory -- no file, no build step. Call
// shapes look identical to the static client (see 01_static_codegen_and_primitive.ts),
// but there are no compile-time types: a path that doesn't exist on the live manifest
// isn't a tsc error here, it's a runtime TypeError, because the dynamic api object
// genuinely doesn't have that key.
import { AoaEngine } from "../../packages/aoa-client-js/src/index.ts";
import type { ResolveResponse } from "../../packages/aoa-client-js/src/types.ts";

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
  schemas: {},
};

const fakeFetch: typeof fetch = (async (url: string, init?: RequestInit) => {
  if (url === MANIFEST_URL) {
    return new Response(JSON.stringify(MANIFEST), { status: 200, headers: { "content-type": "application/json" } });
  }
  const body = JSON.parse(init!.body as string) as { items: Array<{ operation: string }> };
  const response: ResolveResponse = { version: 1, results: body.items.map(() => ({ kind: "AllowedVerdict" })) };
  return new Response(JSON.stringify(response), { status: 200, headers: { "content-type": "application/json" } });
}) as typeof fetch;

const engine = new AoaEngine({ transport: { baseUrl: "https://example.test", fetchImpl: fakeFetch, cachePartition: "user:42" } });

// Same manifest, same shapes -- built in memory this time, no file on disk.
const api = await engine.loadFrom(MANIFEST_URL);

const cancelOrder = api.post?.["/actions/cancel-order"] as { can(params: unknown): Promise<boolean> };
console.log(`api.post["/actions/cancel-order"].can(...) -> ${await cancelOrder.can({ order_id: 7 })}`);

const orders = api.get?.orders as { can(params: unknown): Promise<boolean> };
console.log(`api.get.orders === api.get["/orders"] -> ${api.get?.orders === api.get?.["/orders"]}`);
console.log(`api.get.orders.can({}) -> ${await orders.can({})}`);

// No compile-time types: this path was never in the manifest above. TypeScript has
// no way to know that at compile time -- the dynamic api's leaf type is generic,
// not per-endpoint -- so this only fails once the code actually runs.
try {
  const missing = api.get?.["/nonexistent"] as { can(params: unknown): Promise<boolean> };
  await missing.can({});
  console.log("this should not print -- /nonexistent should not exist");
} catch (error) {
  console.log(`accessing a path absent from the live manifest fails at runtime, not at tsc: ${(error as Error).constructor.name}`);
}
