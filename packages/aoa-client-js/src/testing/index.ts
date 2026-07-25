// packages/aoa-client-js/src/testing/index.ts
//
// The test double half of chapter 12 (issue #144): everything needed to test code
// that sits ON TOP of this library, without a server, a database, or a network.
//
// ─────────────────────────────────────────────────────────────────────────────
// WHICH DOUBLE TO REACH FOR
// ─────────────────────────────────────────────────────────────────────────────
//
// There are two ways to get the network out of a test, and they are not
// interchangeable:
//
//   * Fake `fetchImpl` on a REAL AoaEngine -- see
//     examples/step_27_ui_permissions_client/04_engine_with_fake_fetch_for_tests.ts.
//     The engine stays real: it genuinely builds the request body, genuinely
//     parses and validates the response, genuinely consults its cache. Use this
//     when the ENGINE is what's under test (does it send the right body? does it
//     reject a malformed response? does the cache hit?).
//
//   * createMockAoaEngine (this module). The engine itself is replaced. Nothing
//     is serialized, nothing is parsed, no cache exists. Use this when the engine
//     is NOT what's under test -- a button, a component, a piece of business
//     logic -- and all that code needs is a fast, predictable answer.
//
// Rule of thumb: testing the library -> fake fetchImpl; testing code that USES
// the library -> fake the engine.
//
// ─────────────────────────────────────────────────────────────────────────────
// WHY THIS IS A PLAIN OBJECT AND NOT AN AoaEngine SUBCLASS
// ─────────────────────────────────────────────────────────────────────────────
//
// AoaEngine has private fields, which makes its class type nominal -- a
// hand-written object can never be assignable to it. The fix was to name what
// consumers actually need (`ResolveEngine` in types.ts, exactly one method) and
// have every consumer accept that instead: makeGatePrimitive,
// makeCallablePrimitive, buildDynamicGateApi, and the generated
// createGateApi/createApi. Subclassing AoaEngine was the alternative and was
// rejected: the double would inherit the real constructor (including its ttlMs
// validation) and the real cache, and a cache in a test double is a source of
// confusing false passes, not a feature.

import type { AllowedVerdict, FailErrorVerdict, FailSecurityVerdict, ResolveEngine, ResolveItem, Verdict } from "../types.ts";

// One recorded round-trip. Kept because "did the component ask at all, and how
// many times?" is a real assertion -- without it, a test can only observe the
// answer, never the question. `opts` is recorded verbatim so a test can prove
// that Primitive.run()'s precheck really did pass skipCache: true.
export interface MockResolveCall {
  items: ResolveItem[];
  opts?: { traceId?: string; skipCache?: boolean };
}

// The answer function the test author writes. It is asked ONE question at a
// time even though the real resolve() is batched -- per-item is how tests
// actually read.
//
// `askedCount` is the number of questions this double has answered BEFORE this
// one, across the double's whole lifetime (not reset per batch). It is what
// makes "allowed the first time, denied the second" expressible without the
// test having to close over its own counter.
export type MockAnswer = (item: ResolveItem, askedCount: number) => Verdict | Promise<Verdict>;

export interface MockAoaEngine extends ResolveEngine {
  // Every resolve() this double received, oldest first.
  readonly calls: readonly MockResolveCall[];
}

/**
 * A stand-in for AoaEngine that never touches the network.
 *
 * ```ts
 * const engine = createMockAoaEngine((item) =>
 *   item.operation === "POST /actions/cancel-order" ? success() : resolveError("UNKNOWN_ENDPOINT"),
 * );
 * ```
 *
 * The real resolve() is batched -- a list of questions in, a list of answers
 * out -- so this walks the list, calls `answer` once per question, and returns
 * the results with the SAME LENGTH AND ORDER. That is not a detail: every
 * consumer above (GatePrimitive included) reads result N as the answer to
 * question N. Questions are answered sequentially, so an `answer` that counts
 * calls sees them in a deterministic order even when it is async.
 */
export function createMockAoaEngine(answer: MockAnswer): MockAoaEngine {
  const calls: MockResolveCall[] = [];
  let askedCount = 0;

  return {
    calls,
    async resolve(items: ResolveItem[], opts?: { traceId?: string; skipCache?: boolean }): Promise<Verdict[]> {
      calls.push({ items, opts });
      const results: Verdict[] = [];
      for (const item of items) {
        results.push(await answer(item, askedCount));
        askedCount += 1;
      }
      return results;
    },
  };
}

// ---- Ready-made verdicts ----
//
// A non-empty reason is mandatory on both failure classes -- the real engine's
// own response validation (assertValidVerdict in engine.ts) rejects an empty
// one as a broken response. Building an impossible verdict here would let a
// test pass against a shape the real server can never produce, which is the
// exact failure mode this whole module exists to prevent.

/** "Yes, allowed." Note there is no `reason` field on this class at all. */
export function success(): AllowedVerdict {
  return { kind: "AllowedVerdict" };
}

/** "No, denied, and here is why." A real access-control decision. */
export function denied(reason: string): FailSecurityVerdict {
  assertNonEmptyReason(reason, "denied");
  return { kind: "FailSecurityVerdict", reason };
}

/**
 * "I could not check." NOT a denial -- the absence of a decision. Code that
 * treats this as "no" is the bug this class exists to expose, so tests need a
 * cheap way to produce it. Real reasons today: UNKNOWN_ENDPOINT, EVALUATION_FAILED.
 */
export function resolveError(reason: string): FailErrorVerdict {
  assertNonEmptyReason(reason, "resolveError");
  return { kind: "FailErrorVerdict", reason };
}

function assertNonEmptyReason(reason: string, fn: string): void {
  if (typeof reason !== "string" || reason.length === 0) {
    throw new Error(`${fn}() requires a non-empty reason -- the server can never send an empty one`);
  }
}
