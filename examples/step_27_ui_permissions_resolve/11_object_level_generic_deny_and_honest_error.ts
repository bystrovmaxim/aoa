// examples/step_27_ui_permissions_resolve/11_object_level_generic_deny_and_honest_error.ts
//
// The same two rules as 10_object_level_generic_deny_and_honest_error.py,
// from the client's side of the wire:
// (1) "no such object" and "belongs to someone else" must look identical --
// foreign and missing print the exact same {kind, reason} below; (2) a crash
// during the check answers as FailErrorVerdict, never a denial. fetchImpl is
// a fake returning canned responses, same technique as 01_resolve_single.ts
// -- no real server needed.
import { AoaEngine } from "../../packages/aoa-client-js/src/index.ts";
import type { ResolveResponse } from "../../packages/aoa-client-js/src/types.ts";

const fakeFetch: typeof fetch = async (_url, init) => {
  const body = JSON.parse((init as RequestInit).body as string);
  const [{ params }] = body.items as Array<{ params: { order_id: string } }>;

  let response: ResolveResponse;
  if (params.order_id.startsWith("CRASH-")) {
    response = { version: 1, results: [{ kind: "FailErrorVerdict", reason: "EVALUATION_FAILED" }] };
  } else if (params.order_id.startsWith("MISSING-") || params.order_id === "ORD-foreign") {
    // Byte-for-byte the same result for "doesn't exist" and "isn't yours" --
    // the server never distinguishes them on the wire either.
    response = { version: 1, results: [{ kind: "FailSecurityVerdict", reason: "FORBIDDEN_OBJECT" }] };
  } else {
    response = { version: 1, results: [{ kind: "AllowedVerdict" }] };
  }
  return new Response(JSON.stringify(response), { headers: { "content-type": "application/json" } });
};

const engine = new AoaEngine({
  transport: { baseUrl: "https://example.test", fetchImpl: fakeFetch, cachePartition: "user:alice" },
});

const cases: Array<[string, string]> = [
  ["own order", "ORD-1"],
  ["foreign order", "ORD-foreign"],
  ["missing order", "MISSING-1"],
  ["crash during check", "CRASH-1"],
];

const results: string[] = [];
for (const [label, order_id] of cases) {
  const [result] = await engine.resolve([{ operation: "POST /actions/cancel-order", params: { order_id } }]);
  const reason = "reason" in result ? result.reason : undefined;
  results.push(`${label.padEnd(20)} -> kind=${result.kind} reason=${reason}`);
}
console.log(results.join("\n"));
