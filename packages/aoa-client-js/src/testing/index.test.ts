// packages/aoa-client-js/src/testing/index.test.ts
import { describe, expect, it } from "vitest";

import { buildDynamicGateApi } from "../dynamic-api.ts";
import { AoaEngine, AoaResolveError } from "../engine.ts";
import { buildLayout } from "../path-layout.ts";
import { makeCallablePrimitive, makeGatePrimitive } from "../primitive.ts";
import type { ResolveEngine } from "../types.ts";
import { createMockAoaEngine, denied, resolveError, success } from "./index.ts";

const CANCEL = "POST /actions/cancel-order";

describe("createMockAoaEngine", () => {
  it("answers with whatever the test author's function returns, without any network", async () => {
    const engine = createMockAoaEngine(() => success());

    expect(await engine.resolve([{ operation: CANCEL, params: {} }])).toEqual([{ kind: "AllowedVerdict" }]);
  });

  it("hands the answer function the whole ResolveItem, not just the operation", async () => {
    const seen: unknown[] = [];
    const engine = createMockAoaEngine((item) => {
      seen.push(item);
      return success();
    });

    await engine.resolve([{ operation: CANCEL, params: { order_id: "ORD-1" }, context: { tab: "orders" } }]);

    expect(seen).toEqual([{ operation: CANCEL, params: { order_id: "ORD-1" }, context: { tab: "orders" } }]);
  });

  // The real resolve() is batched; every consumer above reads result N as the
  // answer to question N. A double that reorders or drops would make code that
  // is actually broken look correct.
  it("preserves length and order across a batch, answering each item on its own", async () => {
    const engine = createMockAoaEngine((item) => (item.operation === CANCEL ? success() : denied("not yours")));

    const results = await engine.resolve([
      { operation: "GET /orders", params: {} },
      { operation: CANCEL, params: {} },
      { operation: "GET /orders", params: {} },
      { operation: CANCEL, params: {} },
    ]);

    expect(results).toEqual([
      { kind: "FailSecurityVerdict", reason: "not yours" },
      { kind: "AllowedVerdict" },
      { kind: "FailSecurityVerdict", reason: "not yours" },
      { kind: "AllowedVerdict" },
    ]);
  });

  it("empty batch stays an empty batch and never calls the answer function", async () => {
    let calledTimes = 0;
    const engine = createMockAoaEngine(() => {
      calledTimes += 1;
      return success();
    });

    expect(await engine.resolve([])).toEqual([]);
    expect(calledTimes).toBe(0);
  });

  describe("askedCount", () => {
    it("counts questions across the whole lifetime, not per batch -- this is what makes 'allowed, then denied' expressible", async () => {
      const engine = createMockAoaEngine((_item, askedCount) => (askedCount === 0 ? success() : denied("permission revoked")));

      const first = await engine.resolve([{ operation: CANCEL, params: {} }]);
      const second = await engine.resolve([{ operation: CANCEL, params: {} }]);

      expect(first).toEqual([{ kind: "AllowedVerdict" }]);
      expect(second).toEqual([{ kind: "FailSecurityVerdict", reason: "permission revoked" }]);
    });

    it("is the count of questions ANSWERED BEFORE this one, so it starts at 0 and rises within one batch too", async () => {
      const seen: number[] = [];
      const engine = createMockAoaEngine((_item, askedCount) => {
        seen.push(askedCount);
        return success();
      });

      await engine.resolve([
        { operation: CANCEL, params: {} },
        { operation: CANCEL, params: {} },
      ]);
      await engine.resolve([{ operation: CANCEL, params: {} }]);

      expect(seen).toEqual([0, 1, 2]);
    });
  });

  describe("recorded calls", () => {
    it("records every resolve, oldest first -- so a test can assert the component asked once, not twice", async () => {
      const engine = createMockAoaEngine(() => success());

      await engine.resolve([{ operation: CANCEL, params: { order_id: "ORD-1" } }]);
      await engine.resolve([{ operation: "GET /orders", params: {} }]);

      expect(engine.calls).toHaveLength(2);
      expect(engine.calls[0]?.items).toEqual([{ operation: CANCEL, params: { order_id: "ORD-1" } }]);
      expect(engine.calls[1]?.items).toEqual([{ operation: "GET /orders", params: {} }]);
    });

    it("records opts verbatim, so a test can prove run()'s precheck really asked for a fresh answer", async () => {
      const engine = createMockAoaEngine(() => success());

      const callable = makeCallablePrimitive<{ order_id: string }, { ok: boolean }>(
        engine,
        CANCEL,
        { method: "POST", path: "/actions/cancel-order" },
        async () => ({ ok: true }) as never,
      );
      await callable.run({ order_id: "ORD-1" });

      expect(engine.calls).toHaveLength(1);
      expect(engine.calls[0]?.opts?.skipCache).toBe(true);
    });

    it("leaves opts undefined when the caller passed none", async () => {
      const engine = createMockAoaEngine(() => success());

      await engine.resolve([{ operation: CANCEL, params: {} }]);

      expect(engine.calls[0]?.opts).toBeUndefined();
    });
  });

  describe("async answers", () => {
    it("awaits a promise-returning answer function", async () => {
      const engine = createMockAoaEngine(async () => {
        await Promise.resolve();
        return success();
      });

      expect(await engine.resolve([{ operation: CANCEL, params: {} }])).toEqual([{ kind: "AllowedVerdict" }]);
    });

    // Sequential, not Promise.all: an answer function that counts calls must see
    // them in a deterministic order even when it is async.
    it("answers a batch sequentially, so a counting answer function sees questions in order", async () => {
      const order: string[] = [];
      const engine = createMockAoaEngine(async (item) => {
        order.push(`start:${item.operation}`);
        await Promise.resolve();
        order.push(`end:${item.operation}`);
        return success();
      });

      await engine.resolve([
        { operation: "A", params: {} },
        { operation: "B", params: {} },
      ]);

      expect(order).toEqual(["start:A", "end:A", "start:B", "end:B"]);
    });
  });
});

// The whole reason ResolveEngine exists. Before it, AoaEngine's private fields
// made its type nominal and none of these calls would compile with a double.
describe("substitutability -- the double goes everywhere the real engine goes", () => {
  it("satisfies ResolveEngine, and so does the real AoaEngine", () => {
    const double: ResolveEngine = createMockAoaEngine(() => success());
    const real: ResolveEngine = new AoaEngine({
      transport: { baseUrl: "https://example.test", fetchImpl: fetch, cachePartition: "user:1" },
    });

    expect(typeof double.resolve).toBe("function");
    expect(typeof real.resolve).toBe("function");
  });

  it("works as the engine behind a GatePrimitive", async () => {
    const engine = createMockAoaEngine((item) => (item.operation === CANCEL ? success() : denied("nope")));
    const cancelOrder = makeGatePrimitive<{ order_id: string }>(engine, CANCEL);

    expect(await cancelOrder.can({ order_id: "ORD-1" })).toBe(true);
    expect(await cancelOrder.verdict({ order_id: "ORD-1" })).toEqual({ kind: "AllowedVerdict" });
  });

  it("a FailErrorVerdict from the double still throws AoaResolveError out of can(), exactly as a real one would", async () => {
    const engine = createMockAoaEngine(() => resolveError("EVALUATION_FAILED"));
    const cancelOrder = makeGatePrimitive<{ order_id: string }>(engine, CANCEL);

    await expect(cancelOrder.can({ order_id: "ORD-1" })).rejects.toBeInstanceOf(AoaResolveError);
  });

  it("works as the engine behind a dynamically built api", async () => {
    const engine = createMockAoaEngine(() => success());
    const api = buildDynamicGateApi(
      buildLayout([{ operation: CANCEL, method: "POST", path: "/actions/cancel-order", baseName: "CancelOrder" }]),
      engine,
    );

    // Method buckets are lower-cased by buildLayout; the bracket entry is keyed by full path.
    const primitive = api.post?.["/actions/cancel-order"] as { can(params: unknown): Promise<boolean> };
    expect(await primitive.can({})).toBe(true);
  });
});

describe("ready-made verdicts", () => {
  it("success() is an AllowedVerdict with no reason field at all", () => {
    expect(success()).toEqual({ kind: "AllowedVerdict" });
    expect("reason" in success()).toBe(false);
  });

  it("denied() and resolveError() are different classes carrying the same reason", () => {
    expect(denied("FORBIDDEN_OBJECT")).toEqual({ kind: "FailSecurityVerdict", reason: "FORBIDDEN_OBJECT" });
    expect(resolveError("FORBIDDEN_OBJECT")).toEqual({ kind: "FailErrorVerdict", reason: "FORBIDDEN_OBJECT" });
  });

  // The real engine rejects an empty reason as a broken response
  // (assertValidVerdict). A double able to build one would let a test pass
  // against a shape the server can never send -- the exact failure this module
  // exists to prevent.
  it.each([
    ["denied", denied],
    ["resolveError", resolveError],
  ])("%s() refuses an empty reason, because the server can never send one", (_name, build) => {
    expect(() => build("")).toThrow(/non-empty reason/);
  });
});
