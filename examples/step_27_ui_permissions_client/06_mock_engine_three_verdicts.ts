// examples/step_27_ui_permissions_client/06_mock_engine_three_verdicts.ts
//
// The test double, and the distinction it exists to make visible: "no" and
// "could not check" are NOT the same answer, and code that treats them the same
// is the bug this module is built to expose.
//
// Nothing here touches the network. There is no server, no database, no logged-in
// user -- createMockAoaEngine answers from a function you write yourself.
//
// Run: node --experimental-strip-types examples/step_27_ui_permissions_client/06_mock_engine_three_verdicts.ts

import { AoaResolveError, makeGatePrimitive } from "../../packages/aoa-client-js/src/index.ts";
import { createMockAoaEngine, denied, resolveError, success } from "../../packages/aoa-client-js/src/testing/index.ts";

const CANCEL = "POST /actions/cancel-order";

// One function, three different answers depending on which order is asked about.
// This is why the double takes a function rather than a list of canned replies:
// the answer can depend on the question.
const engine = createMockAoaEngine((item) => {
  if (item.operation !== CANCEL) return resolveError("UNKNOWN_ENDPOINT");
  const orderId = (item.params as { order_id?: string }).order_id;
  if (orderId === "ORD-1") return success();
  if (orderId === "CANCELLED-1") return denied("order is already cancelled");
  return resolveError("EVALUATION_FAILED"); // the check itself broke -- NOT a denial
});

const cancelOrder = makeGatePrimitive<{ order_id: string }>(engine, CANCEL);

// ── 1. Allowed ───────────────────────────────────────────────────────────────
console.log("ORD-1        verdict:", JSON.stringify(await cancelOrder.verdict({ order_id: "ORD-1" })));
console.log("ORD-1        can():  ", await cancelOrder.can({ order_id: "ORD-1" }));

// ── 2. Denied, with a reason a human can read ────────────────────────────────
console.log("CANCELLED-1  verdict:", JSON.stringify(await cancelOrder.verdict({ order_id: "CANCELLED-1" })));
console.log("CANCELLED-1  can():  ", await cancelOrder.can({ order_id: "CANCELLED-1" }));

// ── 3. Could not check -- and this is where the three stop looking alike ─────
//
// .verdict() hands back the FailErrorVerdict as data, because some callers want
// to see it. .can() REFUSES to reduce it to a boolean and throws instead: there
// is no honest boolean for "nobody answered". Returning false here would be the
// classic bug -- a database outage silently rendering every button as forbidden,
// and a client caching that "denial" as if a real decision had been made.
console.log("ORD-99       verdict:", JSON.stringify(await cancelOrder.verdict({ order_id: "ORD-99" })));
try {
  await cancelOrder.can({ order_id: "ORD-99" });
  console.log("ORD-99       can():   returned a boolean — WRONG");
} catch (error) {
  const failure = error as AoaResolveError;
  console.log(`ORD-99       can():   threw ${failure.name} (reason: ${failure.reason}) — correct`);
}

// ── What the double recorded ─────────────────────────────────────────────────
//
// Useful for the assertion tests usually forget: not "what was the answer" but
// "was the question asked at all, and how many times".
console.log("questions asked:", engine.calls.length);
