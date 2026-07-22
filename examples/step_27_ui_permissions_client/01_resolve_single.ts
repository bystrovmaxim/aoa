// examples/step_27_ui_permissions_client/01_resolve_single.ts
//
// The simplest possible AoaEngine call: one question, one answer. No real
// server needed -- fetchImpl is a fake that returns a canned AllowedVerdict,
// the same shape a real POST /permissions/resolve response would have for a
// successful check.
import { AoaEngine } from "../../packages/aoa-client-js/src/index.ts";
import type { ResolveResponse } from "../../packages/aoa-client-js/src/types.ts";

const fakeFetch: typeof fetch = async (_url, init) => {
  const body = JSON.parse((init as RequestInit).body as string);
  console.log("request body:", JSON.stringify(body));
  const response: ResolveResponse = { version: 1, results: [{ kind: "AllowedVerdict" }] };
  return new Response(JSON.stringify(response), { headers: { "content-type": "application/json" } });
};

const engine = new AoaEngine({
  transport: { baseUrl: "https://example.test", fetchImpl: fakeFetch, cachePartition: "user:42" },
});

const [result] = await engine.resolve([{ operation: "POST /actions/cancel-order", params: { order_id: 7 } }]);

// kind === "AllowedVerdict" is the whole "can" question -- no separate
// allowed field on the wire, and AllowedVerdict carries no reason at all.
if (result.kind === "AllowedVerdict") {
  console.log("Can cancel order 7: yes");
} else {
  console.log(`Can cancel order 7: no (${result.kind}: ${result.reason})`);
}
