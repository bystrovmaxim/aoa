// packages/aoa-client-js/src/primitive.test.ts
import { describe, expect, it } from "vitest";

import { AoaEngine, AoaResolveError, NetworkUnavailable, ProtocolError, Unauthorized } from "./engine.ts";
import { buildInvocation, makeCallablePrimitive, makeGatePrimitive } from "./primitive.ts";
import type { ActionInvoker } from "./primitive.ts";
import type { ResolveResponse } from "./types.ts";

interface CancelOrderParams {
  order_id: number;
}
interface CancelOrderResult {
  status: string;
}

function fakeResponse(body: ResolveResponse): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
}

function makeEngine(resultBody: ResolveResponse, captureRequest?: (body: unknown) => void): AoaEngine {
  const fetchImpl = (async (_url: string, init: RequestInit) => {
    captureRequest?.(JSON.parse(init.body as string));
    return fakeResponse(resultBody);
  }) as typeof fetch;
  return new AoaEngine({ transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:1" } });
}

describe("buildInvocation", () => {
  it("carries method and path from the descriptor and params as body", () => {
    const invocation = buildInvocation({ method: "POST", path: "/actions/cancel-order" }, { order_id: 7 });
    expect(invocation).toEqual({ method: "POST", path: "/actions/cancel-order", body: { order_id: 7 } });
  });
});

describe("makeGatePrimitive", () => {
  it("verdict() sends {operation, params} and returns the raw result element", async () => {
    let captured: unknown;
    const engine = makeEngine({ version: 1, results: [{ kind: "AllowedVerdict" }] }, (body) => {
      captured = body;
    });
    const primitive = makeGatePrimitive<CancelOrderParams>(engine, "POST /actions/cancel-order");
    const verdict = await primitive.verdict({ order_id: 7 });
    expect(verdict).toEqual({ kind: "AllowedVerdict" });
    expect(captured).toEqual({ version: 1, items: [{ operation: "POST /actions/cancel-order", params: { order_id: 7 } }] });
  });

  it("can() returns true for AllowedVerdict", async () => {
    const engine = makeEngine({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    const primitive = makeGatePrimitive<CancelOrderParams>(engine, "POST /actions/cancel-order");
    await expect(primitive.can({ order_id: 7 })).resolves.toBe(true);
  });

  it("can() returns false for FailSecurityVerdict -- a real denial, not an error", async () => {
    const engine = makeEngine({ version: 1, results: [{ kind: "FailSecurityVerdict", reason: "only the owner can cancel" }] });
    const primitive = makeGatePrimitive<CancelOrderParams>(engine, "POST /actions/cancel-order");
    await expect(primitive.can({ order_id: 7 })).resolves.toBe(false);
  });

  it("can() throws AoaResolveError for FailErrorVerdict -- never silently false", async () => {
    const engine = makeEngine({ version: 1, results: [{ kind: "FailErrorVerdict", reason: "UNKNOWN_ENDPOINT" }] });
    const primitive = makeGatePrimitive<CancelOrderParams>(engine, "POST /actions/cancel-order");
    const error = await primitive.can({ order_id: 7 }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(AoaResolveError);
    expect((error as AoaResolveError).reason).toBe("UNKNOWN_ENDPOINT");
  });
});

describe("makeCallablePrimitive", () => {
  const descriptor = { method: "POST", path: "/actions/cancel-order" };

  it("exposes the same verdict/can behavior as makeGatePrimitive", async () => {
    const engine = makeEngine({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    const invoker: ActionInvoker = async () => ({ status: "cancelled" }) as never;
    const primitive = makeCallablePrimitive<CancelOrderParams, CancelOrderResult>(
      engine,
      "POST /actions/cancel-order",
      descriptor,
      invoker,
    );
    await expect(primitive.can({ order_id: 7 })).resolves.toBe(true);
    await expect(primitive.verdict({ order_id: 7 })).resolves.toEqual({ kind: "AllowedVerdict" });
  });

  it("run() builds the invocation from the descriptor + params and delegates to actionInvoker", async () => {
    const engine = makeEngine({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    let capturedInvocation: unknown;
    const invoker: ActionInvoker = async (invocation) => {
      capturedInvocation = invocation;
      return { status: "cancelled" } as never;
    };
    const primitive = makeCallablePrimitive<CancelOrderParams, CancelOrderResult>(
      engine,
      "POST /actions/cancel-order",
      descriptor,
      invoker,
    );
    const result = await primitive.run({ order_id: 7 });
    expect(capturedInvocation).toEqual({ method: "POST", path: "/actions/cancel-order", body: { order_id: 7 } });
    expect(result).toEqual({ status: "cancelled" });
  });

  it("run() returns exactly what actionInvoker resolves with, untouched", async () => {
    const engine = makeEngine({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    const invoker: ActionInvoker = async () => ({ status: "already-cancelled" }) as never;
    const primitive = makeCallablePrimitive<CancelOrderParams, CancelOrderResult>(
      engine,
      "POST /actions/cancel-order",
      descriptor,
      invoker,
    );
    await expect(primitive.run({ order_id: 7 })).resolves.toEqual({ status: "already-cancelled" });
  });
});

// Chapter 5.5 (issue #157): run() does its own fresh, non-cached precheck right before
// invoking. actionInvoker throwing on any call it wasn't supposed to receive turns a
// silent wrong-call bug into a failing test, rather than a passing test with the wrong
// assertion.
describe("makeCallablePrimitive -- run() precheck (chapter 5.5)", () => {
  const descriptor = { method: "POST", path: "/actions/cancel-order" };

  it("run()'s precheck bypasses the cache -- a grant revoked after can() cached 'allowed' is still caught", async () => {
    let networkCallCount = 0;
    const fetchImpl = (async () => {
      networkCallCount += 1;
      const body: ResolveResponse =
        networkCallCount === 1
          ? { version: 1, results: [{ kind: "AllowedVerdict" }] }
          : { version: 1, results: [{ kind: "FailSecurityVerdict", reason: "access revoked" }] };
      return fakeResponse(body);
    }) as typeof fetch;
    const engine = new AoaEngine({ transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:1" } });
    const invoker: ActionInvoker = async () => {
      throw new Error("actionInvoker must not be called once the precheck denies");
    };
    const primitive = makeCallablePrimitive<CancelOrderParams, CancelOrderResult>(
      engine,
      "POST /actions/cancel-order",
      descriptor,
      invoker,
    );

    await expect(primitive.can({ order_id: 7 })).resolves.toBe(true); // caches "allowed"
    await expect(primitive.run({ order_id: 7 })).rejects.toThrow("access revoked"); // precheck re-asks for real

    expect(networkCallCount).toBe(2); // proves run() didn't just read the stale cached "allowed"
  });

  it("run() throws a plain Error carrying the reason for FailSecurityVerdict -- not AoaResolveError, no actionInvoker call", async () => {
    const engine = makeEngine({ version: 1, results: [{ kind: "FailSecurityVerdict", reason: "only the owner can cancel" }] });
    const invoker: ActionInvoker = async () => {
      throw new Error("actionInvoker must not be called");
    };
    const primitive = makeCallablePrimitive<CancelOrderParams, CancelOrderResult>(
      engine,
      "POST /actions/cancel-order",
      descriptor,
      invoker,
    );

    const error = await primitive.run({ order_id: 7 }).catch((e: unknown) => e);
    expect(error).not.toBeInstanceOf(AoaResolveError);
    expect((error as Error).message).toContain("only the owner can cancel");
  });

  // Audit finding 2: run()'s own decision never reads the cache (skipCache is
  // always true for it), so it can't itself be fooled -- but a slower, unrelated
  // .can() answering AFTER run()'s faster precheck could still roll the cache
  // back to a stale "allowed" for the next caller, if set() didn't compare
  // freshness. Reproduced here against the real engine/Primitive with manually
  // controlled response order (not real timers), for a fully deterministic test.
  it("a slower .can() response landing after run()'s faster precheck never rolls the cache back to stale-allowed", async () => {
    let requestCount = 0;
    const resolvers: Record<number, (body: ResolveResponse) => void> = {};
    const fetchImpl = (async () => {
      requestCount += 1;
      const thisRequest = requestCount;
      return new Promise<Response>((resolve) => {
        resolvers[thisRequest] = (body) => resolve(fakeResponse(body));
      });
    }) as typeof fetch;

    let clockValue = 0;
    const engine = new AoaEngine({
      transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:1", clock: () => clockValue++ },
    });
    const invoker: ActionInvoker = async () => {
      throw new Error("actionInvoker must not be called");
    };
    const primitive = makeCallablePrimitive<CancelOrderParams, CancelOrderResult>(
      engine,
      "POST /actions/cancel-order",
      descriptor,
      invoker,
    );

    const canPromise = primitive.can({ order_id: 7 }); // request #1, fetchedAt will be 0
    const runPromise = primitive.run({ order_id: 7 }).catch((e: unknown) => e); // request #2, fetchedAt will be 1, skipCache

    // Resolve out of order: the newer request (run()'s precheck) answers first
    // with the real, current denial; the older request (.can()) answers second
    // with a now-stale "allowed" -- simulating a slow response landing after a
    // faster one that was actually issued later.
    resolvers[2]({ version: 1, results: [{ kind: "FailSecurityVerdict", reason: "access revoked" }] });
    expect(await runPromise).toBeInstanceOf(Error);
    resolvers[1]({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    await canPromise;

    // A fresh cache read must still see run()'s denial, not the older "allowed"
    // -- and it must be a real cache hit (no 3rd network call), or this
    // wouldn't be testing the cache at all.
    await expect(primitive.can({ order_id: 7 })).resolves.toBe(false);
    expect(requestCount).toBe(2);
  });

  // Audit finding 3: every existing run() test fixture returns a valid 200/JSON
  // response -- none exercises a transport-level failure inside the precheck
  // itself. Correct today by construction (the `throw` on `await
  // engine.resolve(...)` makes actionInvoker unreachable without an explicit
  // try/catch), but unguarded by a test: a future refactor (e.g. wrapping the
  // precheck in its own try/catch for logging) could silently break it.
  it.each([
    ["NetworkUnavailable", (async () => { throw new Error("network down"); }) as typeof fetch, NetworkUnavailable],
    ["Unauthorized", (async () => new Response(null, { status: 401 })) as typeof fetch, Unauthorized],
    [
      "ProtocolError",
      (async () => new Response("not valid json{{{", { status: 200, headers: { "content-type": "application/json" } })) as typeof fetch,
      ProtocolError,
    ],
  ])("run()'s precheck propagates a %s from the transport layer untouched, no actionInvoker call", async (_label, fetchImpl, ErrorClass) => {
    const engine = new AoaEngine({ transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:1" } });
    const invoker: ActionInvoker = async () => {
      throw new Error("actionInvoker must not be called");
    };
    const primitive = makeCallablePrimitive<CancelOrderParams, CancelOrderResult>(
      engine,
      "POST /actions/cancel-order",
      descriptor,
      invoker,
    );

    await expect(primitive.run({ order_id: 7 })).rejects.toBeInstanceOf(ErrorClass);
  });

  // Audit finding 5: engine.ts's own comment claims run()'s fresh answer is
  // written through to the cache, but until now this was only ever verified
  // against raw engine.resolve() in isolation (engine.test.ts) -- never through
  // a real Primitive, where run() and can() share a closed-over `operation`.
  it("run()'s fresh denial is written through to the cache -- the next can() on the same Primitive reads it, no second network call", async () => {
    let networkCallCount = 0;
    const fetchImpl = (async () => {
      networkCallCount += 1;
      return fakeResponse({ version: 1, results: [{ kind: "FailSecurityVerdict", reason: "access revoked" }] });
    }) as typeof fetch;
    const engine = new AoaEngine({ transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:1" } });
    const invoker: ActionInvoker = async () => {
      throw new Error("actionInvoker must not be called");
    };
    const primitive = makeCallablePrimitive<CancelOrderParams, CancelOrderResult>(
      engine,
      "POST /actions/cancel-order",
      descriptor,
      invoker,
    );

    await expect(primitive.run({ order_id: 7 })).rejects.toThrow("access revoked"); // network call #1
    await expect(primitive.can({ order_id: 7 })).resolves.toBe(false); // must read run()'s write-through
    expect(networkCallCount).toBe(1);
  });

  // Audit finding 7: every other test here exercises exactly one .can()/run()
  // round. A bug that only shows up on the second or third cycle (e.g. staleAt
  // drifting on repeated cache.set() calls to the same key) would pass every
  // single-round test and go uncaught. Three full rounds with a controlled
  // clock: fresh cache hit, TTL expiry, run()'s own skipCache call every round.
  it("staleness, write-through, and skipCache all keep composing correctly across several .can()/run() rounds in a row", async () => {
    let networkCallCount = 0;
    const fetchImpl = (async () => {
      networkCallCount += 1;
      return fakeResponse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    }) as typeof fetch;
    let now = 0;
    const engine = new AoaEngine({
      transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:1", clock: () => now },
    });
    const invoker: ActionInvoker = async () => ({ status: "cancelled" }) as never;
    const primitive = makeCallablePrimitive<CancelOrderParams, CancelOrderResult>(
      engine,
      "POST /actions/cancel-order",
      descriptor,
      invoker,
    );

    for (let round = 0; round < 3; round++) {
      const callsAtRoundStart = networkCallCount;

      await expect(primitive.can({ order_id: 7 })).resolves.toBe(true); // cache expired since last round -- refetches
      expect(networkCallCount).toBe(callsAtRoundStart + 1);

      await expect(primitive.can({ order_id: 7 })).resolves.toBe(true); // still fresh within this round -- cache hit
      expect(networkCallCount).toBe(callsAtRoundStart + 1);

      await expect(primitive.run({ order_id: 7 })).resolves.toEqual({ status: "cancelled" }); // skipCache -- own network call every round
      expect(networkCallCount).toBe(callsAtRoundStart + 2);

      now += 3_000; // past this round's TTL -- next round's first can() must refetch
    }
  });

  it("run() throws AoaResolveError for FailErrorVerdict, same as can() -- never a synthetic deny, no actionInvoker call", async () => {
    const engine = makeEngine({ version: 1, results: [{ kind: "FailErrorVerdict", reason: "UNKNOWN_ENDPOINT" }] });
    const invoker: ActionInvoker = async () => {
      throw new Error("actionInvoker must not be called");
    };
    const primitive = makeCallablePrimitive<CancelOrderParams, CancelOrderResult>(
      engine,
      "POST /actions/cancel-order",
      descriptor,
      invoker,
    );

    const error = await primitive.run({ order_id: 7 }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(AoaResolveError);
    expect((error as AoaResolveError).reason).toBe("UNKNOWN_ENDPOINT");
  });
});
