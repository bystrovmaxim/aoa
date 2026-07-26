// examples/step_27_ui_permissions_client/07_mock_engine_permission_revoked.ts
//
// "Allowed a moment ago, denied now" -- the scenario a fixed list of canned
// replies cannot express, and the reason the double takes a function instead.
//
// This is not a contrived case. It is exactly what run()'s precheck exists for:
// the button was rendered as available, the user went for coffee, the role was
// revoked, and the click arrives against a permission that no longer holds.
//
// Run: node --experimental-strip-types examples/step_27_ui_permissions_client/07_mock_engine_permission_revoked.ts

import { makeCallablePrimitive, makeGatePrimitive } from "../../packages/aoa-client-js/src/index.ts";
import { createMockAoaEngine, denied, success } from "../../packages/aoa-client-js/src/testing/index.ts";

const CANCEL = "POST /actions/cancel-order";

// askedCount is how many questions this double has answered BEFORE this one,
// across its whole lifetime -- not per batch. The test does not have to keep its
// own counter, and does not have to care how many network calls the code under
// test decided to make.
const engine = createMockAoaEngine((_item, askedCount) =>
  askedCount === 0 ? success() : denied("your manager role was revoked"),
);

const gate = makeGatePrimitive<{ order_id: string }>(engine, CANCEL);

console.log("first ask  (button is rendered):", await gate.can({ order_id: "ORD-1" }));
console.log("second ask (user clicks):       ", await gate.can({ order_id: "ORD-1" }));

// ── The same thing, through the machinery that actually cares ────────────────
//
// A CallablePrimitive's run() asks again -- with skipCache: true -- immediately
// before invoking. Here the first (and only) question this fresh double gets is
// the precheck itself, so it succeeds; the interesting part is what the double
// RECORDED, which is how a test proves the precheck really happened rather than
// trusting a cached answer.
const freshEngine = createMockAoaEngine(() => success());
let invoked = false;
const callable = makeCallablePrimitive<{ order_id: string }, { ok: boolean }>(
  freshEngine,
  CANCEL,
  { method: "POST", path: "/actions/cancel-order" },
  async () => {
    invoked = true;
    return { ok: true } as never;
  },
);

await callable.run({ order_id: "ORD-1" });
console.log("action invoked:          ", invoked);
console.log("precheck asked fresh:    ", freshEngine.calls[0]?.opts?.skipCache === true);

// ── And when the precheck says no ────────────────────────────────────────────
//
// run() refuses to invoke. Note the double is what makes this testable at all:
// producing a real revocation against a real server would mean mutating real
// state mid-test.
const revokingEngine = createMockAoaEngine(() => denied("your manager role was revoked"));
let invokedAfterRevoke = false;
const blocked = makeCallablePrimitive<{ order_id: string }, { ok: boolean }>(
  revokingEngine,
  CANCEL,
  { method: "POST", path: "/actions/cancel-order" },
  async () => {
    invokedAfterRevoke = true;
    return { ok: true } as never;
  },
);

try {
  await blocked.run({ order_id: "ORD-1" });
} catch (error) {
  console.log("run() after revoke:      ", (error as Error).message);
}
console.log("action invoked anyway:   ", invokedAfterRevoke, "(must be false)");
