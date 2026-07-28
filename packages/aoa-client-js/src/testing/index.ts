// packages/aoa-client-js/src/testing/index.ts
//
// A stand-in for the engine, so code built on this library can be tested without a
// server, a database, or a network.
//
// There are two ways to take the network out of a test, and they answer different
// questions:
//
//   * Give a real engine a fake fetch. The engine still builds the request, still checks
//     the answer, still uses its cache. Reach for this when the ENGINE is what you are
//     testing -- does it send the right thing, does it refuse a malformed answer.
//
//   * Replace the engine entirely, which is what this module does. Nothing is sent or
//     parsed and there is no cache. Reach for this when the engine is NOT what you are
//     testing -- a button, a screen, a piece of business logic that only needs a fast,
//     predictable answer.
//
// Testing the library itself: fake the fetch. Testing code that uses it: fake the engine.
//
// This is a plain object rather than a subclass of the real engine. A subclass would
// inherit the real constructor and the real cache, and a cache inside a test double
// produces confusing passes rather than useful ones. So consumers accept the one method
// they actually need instead of the whole class.

import { assertValidVerdict } from "../engine.ts";
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
// `askedCount` is how many questions this double has already answered, over its whole
// life. It is what lets a test say "allowed the first time, denied the second" without
// keeping a counter of its own.
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
      // Snapshot, not the caller's own array. `calls` is meant to be the record of
      // what WAS asked; storing the reference makes it a live view of an array the
      // caller still owns, so any later mutation silently rewrites history. The
      // realistic version is not malice: a component reusing one items buffer
      // across renders would make every recorded call show the newest questions.
      // Shallow is enough -- ResolveItem's own fields are never mutated in place by
      // anything here, and a deep clone would cost on every call to defend against
      // a case that has not occurred.
      calls.push({ items: [...items], opts: opts === undefined ? undefined : { ...opts } });
      const results: Verdict[] = [];
      for (const item of items) {
        const verdict = await answer(item, askedCount);
        assertAnswerable(verdict, item, askedCount);
        results.push(verdict);
        askedCount += 1;
      }
      return results;
    },
  };
}

/**
 * Refuse to hand back anything the real server could not have sent.
 *
 * Without this, the double's central promise was enforced only by the `denied`/
 * `resolveError` helpers -- which nobody is obliged to use. An `answer` returning
 * `{ kind: "FailSecurityVerdict", reason: "" }` by hand produced a clean `false`
 * out of `.can()`, so a test asserting "the button is greyed out" went green
 * against a response `AoaEngine` would have rejected outright with a
 * `ProtocolError`. That is exactly the failure this module exists to prevent,
 * reproduced inside the tool built to prevent it.
 *
 * The rule is not restated here. `assertValidVerdict` is the same function the
 * real engine runs on every element of every network response, imported from
 * engine.ts -- one definition, so the double and the engine cannot drift apart
 * at the one point whose whole purpose is keeping them together.
 *
 * The message, though, is deliberately NOT the engine's. A ProtocolError saying
 * "results[3] is missing a non-empty reason" sends a test author looking at
 * their server. The problem is in their own answer function, and the message
 * says so, quotes what it returned, and names the question it was answering.
 */
function assertAnswerable(verdict: unknown, item: ResolveItem, askedCount: number): asserts verdict is Verdict {
  // Called out separately because it is the overwhelmingly common way to get
  // here: a lookup table plus a typo in an operation string. `table[op]` is
  // `undefined`, `.verdict()` hands that straight back, and `.can()` dies with
  // `Cannot read properties of undefined (reading 'kind')` pointing at
  // primitive.ts -- a stack trace with no trace of the actual mistake.
  if (verdict === undefined || verdict === null) {
    throw new Error(
      `createMockAoaEngine: the answer function returned ${String(verdict)} for question #${askedCount} ` +
        `(${item.operation}). A lookup table with no entry for that operation is the usual cause -- ` +
        `return resolveError("UNKNOWN_ENDPOINT") for questions the double should not know about.`,
    );
  }
  try {
    assertValidVerdict(verdict, askedCount);
  } catch (error) {
    throw new Error(
      `createMockAoaEngine: the answer function returned something the real server could never send, ` +
        `for question #${askedCount} (${item.operation}): ${JSON.stringify(verdict)}. ` +
        `${(error as Error).message}. Use success()/denied(reason)/resolveError(reason) to build valid verdicts.`,
    );
  }
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
