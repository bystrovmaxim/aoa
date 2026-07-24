// examples/step_27_ui_permissions_precheck/01_run_precheck_skip_cache.ts
//
// Primitive.run() does its own fresh, non-cached precheck right before invoking
// (chapter 5.5): it always bypasses the cache via `skipCache: true`, so a stale
// "allowed" answer sitting in the cache can never let a revoked action through.
//
// 1. The cache is fresh -- .can() answers from memory, no network call -- but
//    .run() still makes its own separate network call anyway.
// 2. The cache still says "allowed" from a moment ago, but access was revoked in
//    the meantime: run()'s precheck asks fresh, catches it, and never reaches
//    actionInvoker.
import { AoaEngine } from "../../packages/aoa-client-js/src/index.ts";
import { makeCallablePrimitive } from "../../packages/aoa-client-js/src/primitive.ts";
import type { ActionInvoker } from "../../packages/aoa-client-js/src/primitive.ts";
import type { ResolveResponse } from "../../packages/aoa-client-js/src/types.ts";

let networkCallCount = 0;
let serverSaysAllowed = true; // flips to false once access is "revoked" below

const fetchImpl = (async () => {
  networkCallCount += 1;
  const response: ResolveResponse = {
    version: 1,
    results: [serverSaysAllowed ? { kind: "AllowedVerdict" } : { kind: "FailSecurityVerdict", reason: "access revoked" }],
  };
  return new Response(JSON.stringify(response), { status: 200, headers: { "content-type": "application/json" } });
}) as typeof fetch;

const engine = new AoaEngine({ transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:42" } });

const invoker: ActionInvoker = async () => {
  console.log("actionInvoker called -- this is the real HTTP call that cancels the order");
  return { status: "cancelled" };
};
const cancelOrder = makeCallablePrimitive<{ order_id: number }, { status: string }>(
  engine,
  "POST /actions/cancel-order",
  { method: "POST", path: "/actions/cancel-order" },
  invoker,
);

// -- 1. .can() hits the network once, then answers from cache. run() still makes
//       its own separate network call, despite the fresh cache entry.
console.log(`can() #1 -> ${await cancelOrder.can({ order_id: 7 })}`); // network call #1, populates the cache
console.log(`can() #2 (from cache) -> ${await cancelOrder.can({ order_id: 7 })}`); // cache hit, no network call
console.log(`network calls so far: ${networkCallCount} (expected 1)`);

await cancelOrder.run({ order_id: 7 }); // run()'s own precheck -- forces network call #2
console.log(`network calls after run(): ${networkCallCount} (expected 2)`);

// -- 2. Access gets revoked. Nothing has asked again yet, so the cache still says
//       "allowed" -- but run()'s precheck always asks fresh, catches the real
//       answer, and stops before actionInvoker ever runs.
serverSaysAllowed = false;
console.log(`can() #3 (stale cache hit, doesn't know about the revocation yet) -> ${await cancelOrder.can({ order_id: 7 })}`);

try {
  await cancelOrder.run({ order_id: 7 });
  console.log("run() should have thrown -- this line must not print");
} catch (error) {
  console.log(`run() correctly threw instead of trusting the stale cache: ${(error as Error).message}`);
}
