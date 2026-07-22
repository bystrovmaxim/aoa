// examples/step_27_ui_permissions_client/02_resolve_batch_of_questions.ts
//
// resolve() takes a LIST of questions from day one -- this is the resolver's
// own wire protocol (chapter 1), not something AoaEngine adds. Sending three
// questions about three different orders is one HTTP request, one response,
// same order in, same order out. Client-side BATCHING of separate .can()
// calls into one network request is a different thing entirely -- that
// comes later (chapter 7); this example only shows what already works today.
import { AoaEngine } from "../../packages/aoa-client-js/src/index.ts";
import type { ResolveResponse, Verdict } from "../../packages/aoa-client-js/src/types.ts";

const fakeFetch: typeof fetch = async (_url, init) => {
  const body = JSON.parse((init as RequestInit).body as string);
  console.log(`request carried ${body.items.length} questions in one call`);

  const results: Verdict[] = [
    { kind: "AllowedVerdict" },
    { kind: "FailSecurityVerdict", reason: "not the order's owner" },
    { kind: "AllowedVerdict" },
  ];
  const response: ResolveResponse = { version: 1, results };
  return new Response(JSON.stringify(response), { headers: { "content-type": "application/json" } });
};

const engine = new AoaEngine({
  transport: { baseUrl: "https://example.test", fetchImpl: fakeFetch, cachePartition: "user:42" },
});

const results = await engine.resolve([
  { operation: "POST /actions/cancel-order", params: { order_id: 7 } },
  { operation: "POST /actions/cancel-order", params: { order_id: 8 } },
  { operation: "POST /actions/cancel-order", params: { order_id: 9 } },
]);

results.forEach((result, i) => {
  const orderId = 7 + i;
  console.log(
    result.kind === "AllowedVerdict" ? `order ${orderId}: can cancel` : `order ${orderId}: ${result.kind} (${result.reason})`,
  );
});
