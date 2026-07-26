// packages/aoa-client-js/src/primitive.types.test.ts
//
// Type-level half of the two-facade split (chapter 12, #144).
//
// The claim being tested is not "nobody calls .run on a gate" -- it is that a gate
// PHYSICALLY CANNOT be used to invoke the action, enforced by the compiler before
// anything runs. A runtime-only test could never distinguish the two: `undefined` is
// what you get either way when the method is merely absent from an object.
//
// The mechanism is @ts-expect-error, which is an assertion, not a suppression: tsc
// FAILS on a directive that turns out to be unnecessary. So if .run ever leaks onto
// GatePrimitive, `npm run typecheck` goes red on the unused-directive error -- the test
// does not need to be re-run or even remembered.
//
// The companion checks for the GENERATED GateApi/CallableApi (which are printed by the
// codegen, not written by hand, and so need a real tsc subprocess against generated
// output) live in codegen/generate-client.test.ts.

import { describe, expect, it } from "vitest";

import { makeCallablePrimitive, makeGatePrimitive, type CallablePrimitive, type GatePrimitive } from "./primitive.ts";
import { createMockAoaEngine, success } from "./testing/index.ts";
import type { Verdict } from "./types.ts";

const CANCEL = "POST /actions/cancel-order";
type CancelParams = { order_id: string };

describe("GatePrimitive has no way to invoke the action", () => {
  it("does not expose .run at the type level", () => {
    const gate: GatePrimitive<CancelParams> = makeGatePrimitive<CancelParams>(createMockAoaEngine(() => success()), CANCEL);

    // @ts-expect-error GatePrimitive has verdict()/can() only. If this directive ever
    // becomes unnecessary, .run leaked onto the gate facade and typecheck fails here.
    void gate.run;

    // The runtime half is a much weaker statement, kept only to show the two are
    // consistent: absent at runtime AND unreachable at the type level.
    expect("run" in gate).toBe(false);
  });

  it("still exposes verdict() and can(), with the params type it was created for", async () => {
    const gate = makeGatePrimitive<CancelParams>(createMockAoaEngine(() => success()), CANCEL);

    const verdict: Verdict = await gate.verdict({ order_id: "ORD-1" });
    const allowed: boolean = await gate.can({ order_id: "ORD-1" });

    expect(verdict).toEqual({ kind: "AllowedVerdict" });
    expect(allowed).toBe(true);

    // @ts-expect-error order_id is a string on this primitive -- a number is not merely
    // unusual, it is a different endpoint's shape.
    void gate.can({ order_id: 1 });
    // @ts-expect-error a misspelled key is a compile error, not a silently ignored one.
    void gate.can({ orderId: "ORD-1" });
  });
});

describe("CallablePrimitive is the same gate plus the ability to invoke", () => {
  it("exposes .run, correctly typed in both directions", async () => {
    const invoked: unknown[] = [];
    const callable: CallablePrimitive<CancelParams, { ok: boolean }> = makeCallablePrimitive<CancelParams, { ok: boolean }>(
      createMockAoaEngine(() => success()),
      CANCEL,
      { method: "POST", path: "/actions/cancel-order" },
      async (invocation) => {
        invoked.push(invocation);
        return { ok: true } as never;
      },
    );

    // The result type comes from the primitive's own TResult -- not `any`, not `unknown`.
    const result: { ok: boolean } = await callable.run({ order_id: "ORD-1" });

    expect(result).toEqual({ ok: true });
    expect(invoked).toEqual([{ method: "POST", path: "/actions/cancel-order", body: { order_id: "ORD-1" } }]);

    // @ts-expect-error .run takes the same params as .can() -- the two cannot drift apart.
    void callable.run({ order_id: 1 });
  });

  it("is usable anywhere a GatePrimitive is expected, but not the other way round", () => {
    const callable = makeCallablePrimitive<CancelParams, void>(
      createMockAoaEngine(() => success()),
      CANCEL,
      { method: "POST", path: "/actions/cancel-order" },
      async () => undefined as never,
    );

    // Widening is fine: CallablePrimitive extends GatePrimitive, so code that only needs
    // to ask "can I?" accepts either.
    const asGate: GatePrimitive<CancelParams> = callable;
    expect(typeof asGate.can).toBe("function");

    const gate = makeGatePrimitive<CancelParams>(createMockAoaEngine(() => success()), CANCEL);
    // @ts-expect-error Narrowing is not: a gate handed out to UI code can never be
    // widened back into something that invokes.
    const asCallable: CallablePrimitive<CancelParams, void> = gate;
    void asCallable;
  });
});
